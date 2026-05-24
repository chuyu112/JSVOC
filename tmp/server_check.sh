#!/usr/bin/env bash
set -e

if [ -d /opt/JSVOC ]; then
  cd /opt/JSVOC
  echo "PWD=$(pwd)"
  echo "BRANCH=$(git branch --show-current 2>/dev/null || true)"
  echo "HEAD=$(git log --oneline -1 2>/dev/null || true)"
  echo "STATUS:"
  git status --short 2>/dev/null || true
  if [ -f .env ]; then
    echo "ENV=exists"
  else
    echo "ENV=missing"
  fi
  echo "COMPOSE:"
  docker compose ps 2>/dev/null || true
else
  echo "NO_PROJECT_DIR"
fi
