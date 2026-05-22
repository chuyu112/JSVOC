from __future__ import annotations

import os
import sys

import paramiko


def main() -> int:
    command = " ".join(sys.argv[1:])
    if not command:
        print("usage: python scripts/remote_exec.py <command>", file=sys.stderr)
        return 2

    password = os.environ.get("JSVOC_SERVER_PASS")
    if not password:
        print("JSVOC_SERVER_PASS is required", file=sys.stderr)
        return 2

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=os.environ.get("JSVOC_SERVER_HOST", "47.113.178.57"),
        username=os.environ.get("JSVOC_SERVER_USER", "root"),
        password=password,
        timeout=20,
        banner_timeout=20,
        auth_timeout=20,
    )
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=600)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        if out:
            print(out, end="")
        if err:
            print(err, end="")
        return code
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
