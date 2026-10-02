#!/usr/bin/env bash
# 本地正式部署：构建站点并同步到本地托管目录，目录结构与 GitHub Pages 一致
# （根下挂 /ros2_robot/ 子路径），站点内绝对路径引用（如根级 404.html）行为不变。
#
# 用法：
#   bash scripts/deploy_local.sh              # 完整构建 + 同步
#   bash scripts/deploy_local.sh --skip-build # site/ 已是最新，只同步
#
# 启动托管服务（Node/npx，Vercel serve）：
#   npx serve --no-clipboard -l tcp://0.0.0.0:8080 .generated/web
#   仅本机预览则把 0.0.0.0 换成 127.0.0.1；局域网设备访问 http://<本机IP>:8080/ros2_robot/
#   （首次绑定 0.0.0.0 时 Windows 防火墙会弹授权，选“允许”）
#
# 以后迁到自建服务器：把 .generated/web/ 原样交给 Nginx（root 或 Docker 挂载）即可。
set -euo pipefail

cd "$(dirname "$0")/.."

WEB_DIR=".generated/web/ros2_robot"

if [ "${1:-}" != "--skip-build" ]; then
  bash scripts/build_site.sh
fi

# 先同步到暂存目录再原子换名,避免 rm -rf 正在服务的目录把 serve 进程
# 打成 ENOENT 崩溃(替换窗口仅毫秒级)
STAGING=".generated/web-staging"
rm -rf "$STAGING"
mkdir -p "$STAGING/ros2_robot"
# 注意 site/. 的写法:目标目录已存在时 cp -r site dir 会拷成 dir/site/
cp -r site/. "$STAGING/ros2_robot/"
# serve 只认托管根的 404.html,拷一份上去,缺失路径才能落到站点自定义 404 页
cp "$STAGING/ros2_robot/404.html" "$STAGING/404.html"
# navigation.instant 只导航 sitemap.xml 里登记的 URL,而 mkdocs 按 site_url
# (github.io)生成——本地以 127.0.0.1 访问时全部不匹配,instant 静默失效。
# 部署期把 sitemap 域名改写为本地托管地址(可用 HOST=... 覆盖)
HOST_URL="${HOST:-http://127.0.0.1:8080}"
SITE_URL_ORIGIN="https://muhuan11-c.github.io"
".venv/Scripts/python.exe" - "$STAGING/ros2_robot/sitemap.xml" "$SITE_URL_ORIGIN" "$HOST_URL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
t = t.replace(sys.argv[2], sys.argv[3])
p.write_text(t, encoding="utf-8")
print(f"sitemap rewritten -> {sys.argv[3]}")
PY
rm -rf .generated/web
mv "$STAGING" .generated/web
echo "Deployed to $WEB_DIR — serve it with:"
echo "  npx serve --no-clipboard -l tcp://0.0.0.0:8080 .generated/web"
