import os
import sys

import paramiko


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    host = os.environ["JPASP_DEPLOY_HOST"]
    user = os.environ["JPASP_DEPLOY_USER"]
    password = os.environ["JPASP_DEPLOY_PASS"]
    remote_command = " && ".join(
        [
            "cd /opt/JPASP",
            "git fetch origin",
            "git checkout sp8-engineering",
            "git pull origin sp8-engineering",
            "docker compose --progress plain up -d --build",
            "docker compose ps",
            "curl -sS http://localhost:8000/health",
            "curl -sS http://localhost:5173/health",
            "git log --oneline -1",
        ]
    )

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
    try:
        _stdin, stdout, stderr = client.exec_command(remote_command, get_pty=True, timeout=900)
        for line in iter(stdout.readline, ""):
            print(line, end="")
        error_text = stderr.read().decode("utf-8", "replace")
        if error_text:
            print(error_text, file=sys.stderr)
        return stdout.channel.recv_exit_status()
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
