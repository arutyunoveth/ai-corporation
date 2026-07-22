from __future__ import annotations

import base64
import os
import signal
import socket
import subprocess
import time
import secrets
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def compose_project_name() -> str:
    """Return a Docker Compose-safe name that cannot select another run's resources."""
    return f"r8acceptance{secrets.token_hex(4)}"


def http(
    method: str,
    url: str,
    *,
    username: str,
    password: str,
    body: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes, dict]:
    import json

    data = json.dumps(body).encode("utf-8") if body is not None else None
    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
    request_headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    }
    request_headers.update(headers or {})
    request = Request(url, data=data, method=method, headers=request_headers)
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, response.read(), dict(response.headers)
    except HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


class Uvicorn:
    def __init__(self, *, root: Path, env: dict[str, str], port: int, log: Path):
        self.root, self.env, self.port, self.log = root, env, port, log
        self.process: subprocess.Popen | None = None
        self._handle = None

    def start(self, marker: str) -> None:
        self._handle = self.log.open("a", encoding="utf-8")
        self._handle.write(f"=== UVICORN START {marker} ===\n")
        self._handle.flush()
        self.process = subprocess.Popen(
            [
                os.sys.executable,
                "-m",
                "uvicorn",
                "src.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ],
            cwd=self.root,
            env=self.env,
            stdout=self._handle,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )

    def wait_ready(self, username: str, password: str) -> None:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if self.process and self.process.poll() is not None:
                raise RuntimeError("uvicorn terminated before readiness")
            try:
                status, _, _ = http(
                    "GET",
                    f"http://127.0.0.1:{self.port}/api/operator/pilot/summary",
                    username=username,
                    password=password,
                )
                if status == 200:
                    return
            except OSError:
                pass
            time.sleep(0.2)
        raise TimeoutError("uvicorn readiness timeout")

    def stop(self, marker: str) -> None:
        if not self.process:
            return
        self._handle.write(f"=== UVICORN STOP {marker} ===\n")
        self._handle.flush()
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        self._handle.close()
        self.process = None
