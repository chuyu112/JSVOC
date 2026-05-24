from __future__ import annotations

import os
import re
import time

import paramiko


TARGETS = [
    "/etc/nginx/conf.d/jade-circle.conf",
    "/etc/nginx/conf.d/jade_circle.conf",
]


def main() -> int:
    password = os.environ["JSVOC_SERVER_PASS"]
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
        sftp = client.open_sftp()
        try:
            for remote_path in TARGETS:
                try:
                    with sftp.file(remote_path, "r") as remote_file:
                        content = remote_file.read().decode("utf-8")
                except FileNotFoundError:
                    continue

                if "ai.jadehui.com" not in content and "$host =)" not in content:
                    continue

                backup_path = f"{remote_path}.bak-{int(time.time())}"
                sftp.posix_rename(remote_path, backup_path)
                updated = content
                updated = re.sub(
                    r"\n\s*if \(\$host = ai\.jadehui\.com\) \{\s*"
                    r"return 301 https://\$host\$request_uri;\s*"
                    r"\} # managed by Certbot\n",
                    "\n",
                    updated,
                    flags=re.MULTILINE,
                )
                updated = re.sub(
                    r"\n\s*if \(\$host =\) \{\s*"
                    r"return 301 https://\$host\$request_uri;\s*"
                    r"\} # managed by Certbot\n",
                    "\n",
                    updated,
                    flags=re.MULTILINE,
                )
                updated = re.sub(r"\s+ai\.jadehui\.com(?=[\s;])", "", updated)
                updated = re.sub(r"server_name\s+([^;]*?)\s+;", r"server_name \1;", updated)
                updated = re.sub(r"\n{3,}", "\n\n", updated)
                with sftp.file(remote_path, "w") as remote_file:
                    remote_file.write(updated)
                print(f"updated {remote_path}; backup {backup_path}")
        finally:
            sftp.close()

        stdin, stdout, stderr = client.exec_command(
            "nginx -t && systemctl reload nginx && nginx -T 2>/dev/null | grep -n 'ai.jadehui.com' | head -n 20",
            timeout=120,
        )
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
