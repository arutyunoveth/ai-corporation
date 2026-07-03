from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.shared.config.settings import Settings


def install_optional_site_mount(app: FastAPI, settings: Settings) -> None:
    site_public_root = settings.site_public_root_path()
    if site_public_root is None:
        return
    if not site_public_root.is_dir():
        raise RuntimeError(f"Configured site_public_root does not exist or is not a directory: {site_public_root}")
    app.mount("/", StaticFiles(directory=site_public_root, html=True), name="site")
