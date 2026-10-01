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

rm -rf "$WEB_DIR"
mkdir -p "$(dirname "$WEB_DIR")"
cp -r site "$WEB_DIR"
# serve 只认托管根的 404.html，拷一份上去，缺失路径才能落到站点自定义 404 页
cp "$WEB_DIR/404.html" .generated/web/404.html
echo "Deployed to $WEB_DIR — serve it with:"
echo "  npx serve --no-clipboard -l tcp://0.0.0.0:8080 .generated/web"
