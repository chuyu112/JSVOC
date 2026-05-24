#!/usr/bin/env bash
set -euo pipefail

cd /opt/JPASP

backup_dir="/tmp/jpasp-deploy-backup-$(date +%Y%m%d%H%M%S)"
mkdir -p "$backup_dir"

for path in \
  "backend/app/services/account_strategy_context_service.py" \
  "backend/app/prompts/script_prompt.py" \
  "frontend-v2/src/lib/api/images.ts"
do
  mkdir -p "$backup_dir/$(dirname "$path")"
  cp "$path" "$backup_dir/$path"
done

echo "BACKUP_DIR=$backup_dir"
