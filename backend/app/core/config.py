import os

APP_NAME = "Website & API Testing Platform"
APP_VERSION = "0.1.0"
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./app.db")
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "FRONTEND_ORIGIN",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
