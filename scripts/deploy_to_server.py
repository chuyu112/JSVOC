from __future__ import annotations

import os
import posixpath
import socket
import stat
import sys
import time
from pathlib import Path

import paramiko


ROOT = Path(__file__).resolve().parents[1]
REMOTE_DIR = "/opt/JPASP"

EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "dist-ssr",
    "generated_images",
    "JPASP",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
}
EXCLUDED_FILES = {
    "dev-frontend.log",
    "dev-frontend.err.log",
    "project_check_report.txt",
}


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = set(rel.parts)
    if parts & EXCLUDED_DIRS:
        return True
    if path.name in EXCLUDED_FILES:
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    return False


def connect() -> paramiko.SSHClient:
    host = os.environ.get("JSVOC_SERVER_HOST", "47.113.178.57")
    user = os.environ.get("JSVOC_SERVER_USER", "root")
    password = os.environ.get("JSVOC_SERVER_PASS")
    if not password:
        raise RuntimeError("JSVOC_SERVER_PASS is required")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        username=user,
        password=password,
        timeout=20,
        banner_timeout=20,
        auth_timeout=20,
    )
    return client


def run(client: paramiko.SSHClient, command: str, timeout: int = 300) -> str:
    print(f"\n$ {command}", flush=True)
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out, end="", flush=True)
    if err:
        print(err, end="", flush=True)
    if code != 0:
        raise RuntimeError(f"remote command failed with exit code {code}: {command}")
    return out


def mkdir_p(sftp: paramiko.SFTPClient, remote_path: str) -> None:
    parts = [part for part in remote_path.split("/") if part]
    current = ""
    for part in parts:
        current += "/" + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def upload_tree(client: paramiko.SSHClient) -> tuple[int, int]:
    sftp = client.open_sftp()
    try:
        mkdir_p(sftp, REMOTE_DIR)
        uploaded = 0
        skipped = 0
        for local_path in ROOT.rglob("*"):
            if should_skip(local_path):
                skipped += 1
                continue
            rel = local_path.relative_to(ROOT).as_posix()
            remote_path = posixpath.join(REMOTE_DIR, rel)
            if local_path.is_dir():
                mkdir_p(sftp, remote_path)
                continue
            mkdir_p(sftp, posixpath.dirname(remote_path))
            sftp.put(str(local_path), remote_path)
            uploaded += 1
        return uploaded, skipped
    finally:
        sftp.close()


def main() -> int:
    started = time.perf_counter()
    client = connect()
    try:
        run(client, "hostname; docker compose version; docker --version; df -h /opt", timeout=60)
        run(
            client,
            "mkdir -p /opt/JPASP && find /opt/JPASP -mindepth 1 "
            "! -path '/opt/JPASP/.env' "
            "! -path '/opt/JPASP/.env.*' "
            "-exec rm -rf {} +",
            timeout=120,
        )
        uploaded, skipped = upload_tree(client)
        print(f"\nUploaded files: {uploaded}; skipped paths: {skipped}", flush=True)
        run(client, "cd /opt/JPASP && docker compose config >/tmp/jpasp-compose-config.txt && tail -n 40 /tmp/jpasp-compose-config.txt", timeout=120)
        run(client, "cd /opt/JPASP && docker compose up -d --build", timeout=900)
        run(client, "cd /opt/JPASP && docker compose ps", timeout=120)
        run(
            client,
            "cd /opt/JPASP && "
            "docker compose exec -T backend python -c "
            "'import json, urllib.request; print(json.load(urllib.request.urlopen(\"http://127.0.0.1:8000/health\", timeout=5)))' "
            "&& curl -fsS http://127.0.0.1:5173/health && echo",
            timeout=120,
        )
        print(f"\nDeploy completed in {int((time.perf_counter() - started) * 1000)} ms", flush=True)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, socket.error) as exc:
        print(f"deploy failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
