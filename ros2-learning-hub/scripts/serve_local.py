#!/usr/bin/env python3
"""本机只读阅读服务：教材静态文件与独立保存的原始资料。

输入：工作区现有文件；--port 单位为 TCP 端口号，默认 8766。
输出：仅绑定 127.0.0.1 的 HTTP 页面和文本读取接口；不执行所读取的源码。
执行顺序：校验请求路径 → 检查允许目录 → 读取文件 → 返回转义所需的 JSON 文本。
边界：拒绝越界和凭据目录；仅白名单 API 提供目录索引，单次站内文本读取上限 3 MiB。
网站和原始资料分开保存，避免将第三方许可证混同或把大仓库复制进教材包。
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from local_editions import save_edition, safe_path


HUB = Path(__file__).resolve().parents[1]
WORKSPACE = HUB.parent
DIST = HUB / "dist"
ALLOWED = [WORKSPACE / name for name in (
    "ros2_tutorial", "ROS2_Tuition", "Robotics_Tutorial", "ros2_control", "ros2_controllers",
    "ros2_control_demos", "AgroSenseBot", "bunker_ros2", "ugv_sdk", "linorobot2", "linorobot2_hardware")]
ALLOWED += [HUB / "references" / "sources", HUB / "references" / "archives",
            HUB / "examples", HUB / "foundation-examples", HUB / "deliverables"]
TEXT_SUFFIXES = {".md", ".rst", ".mdx", ".txt", ".py", ".cpp", ".hpp", ".h", ".c", ".cc",
                 ".cmake", ".xml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".sh", ".bash",
                 ".msg", ".srv", ".action", ".urdf", ".xacro", ".sdf", ".repos", ".csv", ".html"}
SECRET_PARTS = {".git", ".aws", ".codex", ".agents", ".openai", ".env", "__pycache__"}


def workspace_file(relative: str, allow_directory: bool = False) -> Path:
    """解析后再次检查目录归属，软链接不能用来绕过白名单。"""
    candidate = (WORKSPACE / relative).resolve(strict=True)
    if Path(relative).is_absolute() or any(part in SECRET_PARTS or part.startswith(".env.") for part in candidate.parts):
        raise PermissionError("请求不在可阅读的资料范围")
    if (not any(candidate.is_relative_to(root.resolve()) for root in ALLOWED)
            or not (candidate.is_file() or (allow_directory and candidate.is_dir()))):
        raise PermissionError("请求不在可阅读的资料范围")
    return candidate


class ReaderHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def end_headers(self):
        # 页面只使用本地资源。原始 HTML 中的远程脚本也不会自动运行。
        policy="default-src 'self' data: blob:; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'self'"
        # 原始文件使用独立沙箱：即使主动打开 HTML，也不执行其中的脚本。
        if urlsplit(self.path).path.startswith('/local/'):
            policy="sandbox; default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src data:; object-src 'none'"
        self.send_header("Content-Security-Policy",policy)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(403, "Directory listing is disabled")
        return None

    def translate_path(self, path):
        parsed = unquote(urlsplit(path).path)
        hub = getattr(self.server, "hub", HUB)
        if parsed.startswith("/design-review/"):
            relative = "design-review/" + parsed.removeprefix("/design-review/")
        elif parsed.startswith("/dist/"):
            relative = "dist/" + parsed.removeprefix("/dist/")
        else:
            relative = "dist/" + parsed.lstrip("/")
        try:
            return str(safe_path(hub, relative))
        except ValueError:
            return str(hub / "__not_public__")

    def send_json(self, value, status=200):
        payload = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        # 只有显式 --editable 才接受同源写入；不信任任意网页提交的路径或命令。
        port = self.server.server_port
        origin = f"http://127.0.0.1:{port}"
        if (not getattr(self.server, "editable", False)
                or urlsplit(self.path).path != "/api/textbook/save"):
            self.send_json({"error": "当前服务只读，请用 --editable 启动编辑服务"}, 405)
            return
        if (self.headers.get("Host") != f"127.0.0.1:{port}"
                or self.headers.get("Origin") != origin
                or not secrets.compare_digest(self.headers.get("X-Textbook-Token", ""), self.server.editor_token)):
            self.send_json({"error": "保存请求不是来自当前本机编辑页面"}, 403)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 8 * 1024**2:
                self.send_json({"error": "保存数据无效或超过 8 MiB"}, 413)
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.send_json({"error": "只接受 JSON 章节数据"}, 415)
                return
            payload = json.loads(self.rfile.read(size))
            self.send_json(save_edition(self.server.hub, payload))
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.send_json({"error": str(error)}, 409)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/design-review/service-config.js":
            config = {"enabled": True, "token": self.server.editor_token} if getattr(self.server, "editable", False) else None
            payload = ("window.NarukamiEditorService = " + json.dumps(config) + ";\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if parsed.path == "/api/source":
            try:
                relative = parse_qs(parsed.query).get("path", [""])[0]
                file = workspace_file(relative, allow_directory=True)
                if file.is_dir():
                    entries=[]
                    for child in sorted(file.iterdir(), key=lambda item:(not item.is_dir(),item.name.lower())):
                        if child.name.startswith('.'):
                            continue
                        child_path=child.relative_to(WORKSPACE).as_posix()
                        try:
                            checked=workspace_file(child_path, allow_directory=True)
                        except (OSError, ValueError):
                            continue
                        entries.append({'name':child.name,'path':child_path,'directory':checked.is_dir()})
                    try:
                        parent=workspace_file(file.parent.relative_to(WORKSPACE).as_posix(),allow_directory=True).relative_to(WORKSPACE).as_posix()
                    except (OSError, ValueError):
                        parent=None
                    value={'kind':'directory','path':relative,'entries':entries,'parent':parent}
                elif file.stat().st_size > 3 * 1024**2:
                    self.send_error(413, "File exceeds the 3 MiB inline reading limit")
                    return
                elif file.suffix.lower() not in TEXT_SUFFIXES and not file.name.startswith(("README", "LICENSE", "NOTICE", "CMakeLists", "COPYING")):
                    self.send_error(415, "Use the original file link for this format")
                    return
                else:
                    parent=file.parent.relative_to(WORKSPACE).as_posix()
                    value = {"kind":"file","path": relative,"parent":parent,"bytes": file.stat().st_size,
                             "text": file.read_text(encoding="utf-8", errors="replace")}
                payload = json.dumps(value, ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (OSError, ValueError):
                self.send_error(404, "The requested local source is unavailable")
            return
        if parsed.path.startswith("/local/"):
            try:
                file = workspace_file(unquote(parsed.path.removeprefix("/local/")))
                self.send_response(200)
                mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                if file.suffix.lower() in TEXT_SUFFIXES and file.suffix.lower() != ".html":
                    mime = "text/plain; charset=utf-8"
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(file.stat().st_size))
                self.end_headers()
                with file.open("rb") as source:
                    self.copyfile(source, self.wfile)
            except (OSError, ValueError):
                self.send_error(404, "The requested local file is unavailable")
            return
        if parsed.path == "/api/status":
            payload = json.dumps({"workspace": True, "readOnly": not getattr(self.server, "editable", False)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--editable", action="store_true", help="允许当前本机页面备份并保存教材修订")
    parser.add_argument("--root", type=Path, default=HUB, help="教材根目录；用于独立副本或验收")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口号须在 1–65535 之间")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ReaderHandler)
    server.hub = args.root.resolve()
    server.editable = args.editable
    server.editor_token = secrets.token_urlsafe(32)
    print(f"Local: http://127.0.0.1:{args.port}/", flush=True)
    if args.editable:
        print(f"编辑入口：http://127.0.0.1:{args.port}/design-review/", flush=True)
    print("本机教材编辑已启用，保存前自动备份。" if args.editable else "仅提供本机只读阅读。", flush=True)
    print("按 Ctrl+C 结束。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
