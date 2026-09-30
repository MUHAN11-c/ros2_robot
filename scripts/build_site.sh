#!/usr/bin/env bash
# 构建文档站：先同步内容并生成 mkdocs.generated.yml，再执行 mkdocs build。
# 本地与 GitHub Actions 共用：bash scripts/build_site.sh
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
  PYTHON_BIN=".venv/Scripts/python.exe"
fi

"$PYTHON_BIN" scripts/sync_docs.py
"$PYTHON_BIN" -m mkdocs build -f mkdocs.generated.yml "$@"

# 根级 404.html 由 override_404_hook（mkdocs.yml hooks）统一覆盖并修正相对路径，
# 此处无需再拷贝（原样 cp 会把 ../ 前缀带回去，导致根级 404 资源引用失效）
