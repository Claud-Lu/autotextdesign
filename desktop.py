"""
书法字体制作器 — 桌面版启动入口
使用 pywebview 将 FastAPI 包装为原生桌面窗口
"""
import multiprocessing
import sys
import time

import uvicorn
import webview


def find_free_port() -> int:
    """找到一个可用端口"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port: int) -> None:
    """启动 FastAPI 后端服务"""
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning")


def main() -> None:
    port = find_free_port()

    # 子进程启动 FastAPI
    server = multiprocessing.Process(target=start_server, args=(port,), daemon=True)
    server.start()

    # 等待服务就绪
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.2)

    # 创建原生窗口
    webview.create_window(
        title="书法字体制作器",
        url=url,
        width=1200,
        height=800,
        min_size=(800, 600),
    )

    webview.start(debug="--debug" in sys.argv)
    server.terminate()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
