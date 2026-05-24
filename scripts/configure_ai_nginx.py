from __future__ import annotations

import os
import sys

import paramiko


CONF_PATH = "/etc/nginx/conf.d/ai-jpasp.conf"
CONF = r"""
server {
    listen 80;
    listen [::]:80;
    server_name ai.jadehui.com;

    location /.well-known/acme-challenge/ {
        root /var/www/jade_circle;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ai.jadehui.com;

    ssl_certificate /etc/letsencrypt/live/zhatu.jadehui.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/zhatu.jadehui.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    client_max_body_size 120m;

    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_read_timeout 600s;
    }
}
""".lstrip()


def main() -> int:
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
        sftp = client.open_sftp()
        try:
            with sftp.file(CONF_PATH, "w") as remote_file:
                remote_file.write(CONF)
        finally:
            sftp.close()

        command = "nginx -t && systemctl reload nginx && nginx -T 2>/dev/null | grep -n 'server_name ai.jadehui.com' | head"
        stdin, stdout, stderr = client.exec_command(command, timeout=120)
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
