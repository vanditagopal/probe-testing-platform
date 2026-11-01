import ipaddress
import re
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address
from urllib.parse import urljoin, urlsplit, urlunsplit

IPAddress = IPv4Address | IPv6Address
AddressResolver = Callable[[str, int], Iterable[str]]

MAX_REDIRECTS = 5
_METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("100.100.100.200"),
    ipaddress.ip_address("fd00:ec2::254"),
}
_METADATA_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata",
    "metadata.google.internal",
    "metadata.azure.internal",
    "instance-data.ec2.internal",
}
_NUMERIC_HOST = re.compile(r"(?i)^(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+))*$")
_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class URLSafetyError(ValueError):
    """Raised when a target URL cannot be proven safe for a later connection."""


@dataclass(frozen=True)
class ValidatedTarget:
    url: str
    scheme: str
    hostname: str
    port: int
    addresses: tuple[IPAddress, ...]

    def validate_connection_address(self, address: str | IPAddress) -> IPAddress:
        """Validate and pin the address chosen by the eventual HTTP connection."""
        parsed_address = _parse_ip_address(address)
        _ensure_public_address(parsed_address)
        if parsed_address not in self.addresses:
            raise URLSafetyError(
                "The connection address was not among the validated DNS answers."
            )
        return parsed_address


def validate_target_url(
    url: str,
    *,
    resolver: AddressResolver | None = None,
) -> ValidatedTarget:
    """Validate an absolute HTTP(S) URL and resolve only globally routable targets."""
    if not isinstance(url, str) or not url or url != url.strip():
        raise URLSafetyError("Enter a valid absolute HTTP or HTTPS URL.")
    if any(ord(character) < 32 or ord(character) == 127 for character in url):
        raise URLSafetyError("The target URL must not contain control characters.")
    if "\\" in url:
        raise URLSafetyError("Backslashes are not allowed in target URLs.")

    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        supplied_port = parsed.port
    except ValueError as exception:
        raise URLSafetyError("The target URL is malformed.") from exception

    if scheme not in {"http", "https"}:
        raise URLSafetyError("Only HTTP and HTTPS target URLs are supported.")
    if not parsed.netloc or hostname is None:
        raise URLSafetyError("Enter a valid absolute HTTP or HTTPS URL.")
    if parsed.netloc.endswith(":"):
        raise URLSafetyError("The target URL has an invalid port.")
    if (
        parsed.username is not None
        or parsed.password is not None
        or "@" in parsed.netloc
    ):
        raise URLSafetyError("URL credentials are not allowed.")
    if "%" in parsed.netloc:
        raise URLSafetyError(
            "Percent-encoded hosts and IPv6 zone identifiers are not allowed."
        )
    if "#" in url:
        raise URLSafetyError("URL fragments are not allowed in target URLs.")
    if any(character.isspace() for character in url):
        raise URLSafetyError("Whitespace is not allowed in target URLs.")

    normalized_host, literal_address = _normalize_hostname(hostname)
    if normalized_host in _METADATA_HOSTNAMES or normalized_host.endswith(
        (".localhost", ".localhost.localdomain", ".local", ".internal")
    ):
        raise URLSafetyError("Local and cloud metadata hostnames are not allowed.")

    expected_port = 443 if scheme == "https" else 80
    port = supplied_port if supplied_port is not None else expected_port
    if port != expected_port:
        raise URLSafetyError(
            "Only the standard port for the selected scheme is allowed."
        )

    if literal_address is not None:
        addresses = (literal_address,)
    else:
        address_resolver = resolver if resolver is not None else _resolve_addresses
        try:
            resolved_values = tuple(address_resolver(normalized_host, port))
        except (OSError, socket.gaierror) as exception:
            raise URLSafetyError(
                "The target hostname could not be resolved."
            ) from exception
        if not resolved_values:
            raise URLSafetyError(
                "The target hostname did not resolve to any addresses."
            )
        addresses = tuple(
            sorted(
                {_parse_ip_address(address) for address in resolved_values},
                key=lambda address: (address.version, int(address)),
            )
        )

    for address in addresses:
        _ensure_public_address(address)

    formatted_host = (
        f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    )
    normalized_url = urlunsplit(
        (scheme, formatted_host, parsed.path or "/", parsed.query, "")
    )
    return ValidatedTarget(
        url=normalized_url,
        scheme=scheme,
        hostname=normalized_host,
        port=port,
        addresses=addresses,
    )


def validate_redirect_target(
    current: ValidatedTarget,
    location: str,
    *,
    resolver: AddressResolver | None = None,
) -> ValidatedTarget:
    """Resolve and validate a redirect destination before following it."""
    if not location or location != location.strip():
        raise URLSafetyError("The redirect destination is malformed.")
    try:
        destination = urljoin(current.url, location)
    except ValueError as exception:
        raise URLSafetyError("The redirect destination is malformed.") from exception
    if urlsplit(destination).scheme.lower() == "http" and current.scheme == "https":
        raise URLSafetyError("HTTPS redirects must not downgrade to HTTP.")
    target = validate_target_url(destination, resolver=resolver)
    return target


def validate_redirect_chain(
    initial_url: str,
    redirect_locations: Iterable[str],
    *,
    resolver: AddressResolver | None = None,
    max_redirects: int = MAX_REDIRECTS,
) -> ValidatedTarget:
    """Validate every destination in a bounded redirect chain."""
    if max_redirects < 0:
        raise ValueError("max_redirects must be non-negative.")
    current = validate_target_url(initial_url, resolver=resolver)
    visited_urls = {current.url}

    for redirect_count, location in enumerate(redirect_locations, start=1):
        if redirect_count > max_redirects:
            raise URLSafetyError("The redirect limit was exceeded.")
        current = validate_redirect_target(current, location, resolver=resolver)
        if current.url in visited_urls:
            raise URLSafetyError("A redirect loop was detected.")
        visited_urls.add(current.url)

    return current


def _normalize_hostname(hostname: str) -> tuple[str, IPAddress | None]:
    if not hostname or "%" in hostname:
        raise URLSafetyError("The target hostname is malformed.")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None

    if address is not None:
        return str(address), address

    if hostname.endswith("."):
        hostname = hostname[:-1]
    if not hostname or _NUMERIC_HOST.fullmatch(hostname):
        raise URLSafetyError("Non-standard numeric IP address formats are not allowed.")
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exception:
        raise URLSafetyError("The target hostname is malformed.") from exception
    if len(ascii_hostname) > 253:
        raise URLSafetyError("The target hostname is too long.")
    labels = ascii_hostname.split(".")
    if len(labels) < 2 or any(not _DNS_LABEL.fullmatch(label) for label in labels):
        raise URLSafetyError("Enter a fully qualified, valid DNS hostname.")
    return ascii_hostname, None


def _parse_ip_address(address: str | IPAddress) -> IPAddress:
    if isinstance(address, str) and "%" in address:
        raise URLSafetyError("Scoped IP addresses are not allowed.")
    try:
        return ipaddress.ip_address(address)
    except ValueError as exception:
        raise URLSafetyError(
            "The target resolved to an invalid IP address."
        ) from exception


def _ensure_public_address(address: IPAddress) -> None:
    mapped_address = address.ipv4_mapped if isinstance(address, IPv6Address) else None
    checked_address = mapped_address or address
    if (
        checked_address in _METADATA_IPS
        or not checked_address.is_global
        or checked_address.is_private
        or checked_address.is_loopback
        or checked_address.is_link_local
        or checked_address.is_multicast
        or checked_address.is_reserved
        or checked_address.is_unspecified
    ):
        raise URLSafetyError("The target resolves to a blocked non-public IP address.")


def _resolve_addresses(hostname: str, port: int) -> tuple[str, ...]:
    results = socket.getaddrinfo(
        hostname,
        port,
        family=socket.AF_UNSPEC,
        type=socket.SOCK_STREAM,
    )
    return tuple(result[4][0] for result in results)
