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

# 自定义 404 页覆盖 Material 默认 404（GitHub Pages 以 /404.html 提供服务）
if [ -f site/404/index.html ]; then
  cp site/404/index.html site/404.html
fi
