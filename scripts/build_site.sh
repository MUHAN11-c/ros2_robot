#!/usr/bin/env bash
# 构建文档站：先同步内容并生成 mkdocs.generated.yml，再执行 mkdocs build。
# 本地与 GitHub Actions 共用：bash scripts/build_site.sh
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

"$PYTHON_BIN" scripts/sync_docs.py
"$PYTHON_BIN" -m mkdocs build -f mkdocs.generated.yml "$@"
