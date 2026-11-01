import socket
from ipaddress import ip_address

import pytest

from app.services.url_safety import (
    MAX_REDIRECTS,
    URLSafetyError,
    validate_redirect_chain,
    validate_redirect_target,
    validate_target_url,
)


def _public_resolver(hostname: str, port: int) -> tuple[str, ...]:
    assert hostname == "api.example.test"
    assert port in {80, 443}
    return ("93.184.216.34",)


@pytest.mark.parametrize(
    ("url", "expected_host", "expected_port"),
    [
        ("https://api.example.test/v1", "api.example.test", 443),
        ("https://93.184.216.34/", "93.184.216.34", 443),
        ("https://[2606:4700:4700::1111]/v1", "2606:4700:4700::1111", 443),
        ("http://api.example.test/", "api.example.test", 80),
    ],
)
def test_accepts_public_targets_and_normalizes_urls(
    url: str, expected_host: str, expected_port: int
) -> None:
    target = validate_target_url(url, resolver=_public_resolver)

    assert target.hostname == expected_host
    assert target.port == expected_port
    assert target.url == url
    assert target.addresses


@pytest.mark.parametrize(
    "url",
    [
        "ftp://api.example.test/",
        "file:///C:/Windows/win.ini",
        "javascript:alert(1)",
        "//api.example.test/path",
        "https://",
        "https://user:password@api.example.test/",
        "https://user@api.example.test/",
        "https://api.example.test:invalid/",
        "https://api.example.test:/",
        "https://api.example.test:8443/",
        "https://api%2eexample.test/",
        "https://api.example.test\\@127.0.0.1/",
        "https://api.example.test../",
        "https://api.example.test/path#fragment",
    ],
)
def test_rejects_malformed_or_ambiguous_urls(url: str) -> None:
    with pytest.raises(URLSafetyError):
        validate_target_url(url, resolver=_public_resolver)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://localhost.localdomain/",
        "http://internal.example.internal/",
        "http://metadata/",
        "http://metadata.google.internal/",
        "http://metadata.azure.internal/",
        "http://instance-data.ec2.internal/",
        "http://127.0.0.1/",
        "http://0177.0.0.1/",
        "http://127.1/",
        "http://2130706433/",
        "http://0x7f000001/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
    ],
)
def test_rejects_local_metadata_and_alternate_ip_targets(url: str) -> None:
    with pytest.raises(URLSafetyError):
        validate_target_url(url, resolver=_public_resolver)


@pytest.mark.parametrize(
    "address",
    [
        "0.0.0.0",
        "10.0.0.1",
        "100.64.0.1",
        "100.100.100.200",
        "127.0.0.1",
        "169.254.1.1",
        "169.254.169.254",
        "172.16.0.1",
        "192.168.1.1",
        "192.0.2.1",
        "198.18.0.1",
        "224.0.0.1",
        "240.0.0.1",
        "::",
        "::1",
        "::ffff:127.0.0.1",
        "fc00::1",
        "fe80::1",
        "ff02::1",
        "fd00:ec2::254",
    ],
)
def test_rejects_non_public_ip_literals(address: str) -> None:
    formatted_address = f"[{address}]" if ":" in address else address
    with pytest.raises(URLSafetyError):
        validate_target_url(
            f"https://{formatted_address}/",
            resolver=_public_resolver,
        )


def test_rejects_hostname_if_any_dns_answer_is_not_public() -> None:
    unsafe_answers = [
        ("93.184.216.34", "10.0.0.1"),
        ("93.184.216.34", "fd00::1"),
    ]
    for addresses in unsafe_answers:
        with pytest.raises(URLSafetyError, match="blocked non-public"):
            validate_target_url(
                "https://api.example.test/",
                resolver=lambda hostname, port: addresses,
            )


def test_rejects_empty_dns_answers_and_reports_resolution_failure_safely() -> None:
    with pytest.raises(URLSafetyError, match="did not resolve"):
        validate_target_url(
            "https://api.example.test/",
            resolver=lambda hostname, port: (),
        )

    def failed_resolver(hostname: str, port: int) -> tuple[str, ...]:
        raise socket.gaierror("private resolver detail")

    with pytest.raises(URLSafetyError, match="could not be resolved") as error:
        validate_target_url("https://api.example.test/", resolver=failed_resolver)
    assert "private resolver detail" not in str(error.value)


def test_normalizes_idn_before_resolving() -> None:
    resolved_hosts: list[str] = []

    def resolver(hostname: str, port: int) -> tuple[str, ...]:
        resolved_hosts.append(hostname)
        return ("93.184.216.34",)

    target = validate_target_url("https://bücher.example/", resolver=resolver)

    assert resolved_hosts == ["xn--bcher-kva.example"]
    assert target.hostname == "xn--bcher-kva.example"
    assert target.url == "https://xn--bcher-kva.example/"


def test_preserves_query_and_normalizes_trailing_dns_dot() -> None:
    target = validate_target_url(
        "https://api.example.test./v1?version=1",
        resolver=_public_resolver,
    )

    assert target.hostname == "api.example.test"
    assert target.url == "https://api.example.test/v1?version=1"


def test_normalizes_explicit_standard_port() -> None:
    target = validate_target_url(
        "https://api.example.test:443/v1",
        resolver=_public_resolver,
    )

    assert target.port == 443
    assert target.url == "https://api.example.test/v1"


def test_connection_address_must_be_one_of_validated_dns_answers() -> None:
    target = validate_target_url("https://api.example.test/", resolver=_public_resolver)

    assert target.validate_connection_address("93.184.216.34") == ip_address(
        "93.184.216.34"
    )
    with pytest.raises(URLSafetyError, match="not among the validated"):
        target.validate_connection_address("1.1.1.1")
    with pytest.raises(URLSafetyError, match="blocked non-public"):
        target.validate_connection_address("127.0.0.1")
    with pytest.raises(URLSafetyError, match="Scoped IP"):
        target.validate_connection_address("2606:4700:4700::1111%12")


def test_redirect_target_is_resolved_and_validated_before_following() -> None:
    initial = validate_target_url(
        "https://api.example.test/v1", resolver=_public_resolver
    )

    with pytest.raises(URLSafetyError, match="blocked non-public"):
        validate_redirect_target(initial, "https://169.254.169.254/latest/meta-data/")

    with pytest.raises(URLSafetyError, match="must not downgrade"):
        validate_redirect_target(
            initial,
            "http://api.example.test/v2",
            resolver=_public_resolver,
        )


def test_redirect_chain_checks_each_destination_and_limits_redirects() -> None:
    resolved_hosts: list[str] = []

    def safe_resolver(hostname: str, port: int) -> tuple[str, ...]:
        resolved_hosts.append(hostname)
        return ("93.184.216.34",)

    target = validate_redirect_chain(
        "https://api.example.test/start",
        ["/next", "https://other.example.test/final"],
        resolver=safe_resolver,
    )
    assert target.url == "https://other.example.test/final"
    assert resolved_hosts == [
        "api.example.test",
        "api.example.test",
        "other.example.test",
    ]

    with pytest.raises(URLSafetyError, match="redirect limit"):
        validate_redirect_chain(
            "https://api.example.test/start",
            ["/1", "/2"],
            resolver=safe_resolver,
            max_redirects=1,
        )
    with pytest.raises(URLSafetyError, match="redirect loop"):
        validate_redirect_chain(
            "https://api.example.test/start",
            ["/start"],
            resolver=safe_resolver,
        )
    assert MAX_REDIRECTS == 5


def test_rejects_invalid_max_redirect_count() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        validate_redirect_chain(
            "https://api.example.test/",
            [],
            resolver=_public_resolver,
            max_redirects=-1,
        )
