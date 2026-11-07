#!/usr/bin/env bash
# 宿主软件信号实验的显式入口；不是Docker镜像构建/运行证据。
# 输入：第1个参数为underlay setup.bash，第2个为原始overlay setup.bash，随后为直接可执行及参数。
# 输出：完成两个环境入口后，exec把同一PID替换成节点；退出码来自该节点。
# 顺序：检查文件→source underlay→source overlay→exec，不后台启动、不开子shell守护节点。
# 边界：source执行的是调用者明确选择的可信环境脚本，不应给本入口不可信脚本。
set -e
if [[ "$#" -lt 3 ]]; then
  printf '%s\n' '需要underlay setup、overlay setup和直接可执行路径' >&2
  exit 2
fi
_deployment_underlay="$1"
_deployment_overlay="$2"
shift 2
[[ -f "$_deployment_underlay" && -f "$_deployment_overlay" ]]
# --限定环境脚本的临时位置参数；返回后本入口的命令参数仍保留。
source "$_deployment_underlay" --
source "$_deployment_overlay" --
exec "$@"
