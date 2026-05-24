from __future__ import annotations

import os
import sys

import paramiko


CONF_PATH = "/etc/nginx/conf.d/jsvoc-jpasp.conf"
OLD_CONF_PATH = "/etc/nginx/conf.d/ai-jpasp.conf"
CERT_NAME = "zhatu.jadehui.com"
DOMAIN = "jsvoc.jadehui.com"

CONF = f"""
server {{
    listen 80;
    listen [::]:80;
    server_name {DOMAIN};

    location /.well-known/acme-challenge/ {{
        root /var/www/jade_circle;
    }}

    location / {{
        return 301 https://$host$request_uri;
    }}
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {DOMAIN};

    ssl_certificate /etc/letsencrypt/live/{CERT_NAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{CERT_NAME}/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    client_max_body_size 120m;

    location / {{
        proxy_pass http://127.0.0.1:5173;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_read_timeout 600s;
    }}
}}
""".lstrip()


def run(client: paramiko.SSHClient, command: str, timeout: int = 300) -> int:
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out, end="")
    if err:
        print(err, end="")
    return code


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
            try:
                sftp.remove(OLD_CONF_PATH)
                print(f"removed {OLD_CONF_PATH}")
            except FileNotFoundError:
                pass
            with sftp.file(CONF_PATH, "w") as remote_file:
                remote_file.write(CONF)
        finally:
            sftp.close()

        precheck = run(client, "nginx -t", timeout=120)
        if precheck != 0:
            return precheck

        cert_cmd = (
            "certbot certonly --nginx --cert-name zhatu.jadehui.com "
            "-d zhatu.jadehui.com -d jadehui.com -d www.jadehui.com "
            "-d static.jadehui.com -d real.jadehui.com -d ai.jadehui.com "
            "-d jsvoc.jadehui.com --non-interactive --agree-tos "
            "-m admin@jadehui.com --expand"
        )
        cert_code = run(client, cert_cmd, timeout=300)
        if cert_code != 0:
            return cert_code

        return run(
            client,
            "nginx -t && systemctl reload nginx && "
            "openssl x509 -in /etc/letsencrypt/live/zhatu.jadehui.com/fullchain.pem -noout -ext subjectAltName | grep -o 'DNS:[^,]*' | grep 'jsvoc.jadehui.com' && "
            "nginx -T 2>/dev/null | grep -n 'ai.jadehui.com\\|jsvoc.jadehui.com' | head -n 40",
            timeout=120,
        )
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
