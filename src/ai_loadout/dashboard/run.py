"""Launch the dashboard with uvicorn on the default Loadout port (8421).

Kept separate from :mod:`server` so importing the app (e.g. in tests) never starts a
server, and so the missing-extra message is friendly when the web stack isn't installed.
"""

from __future__ import annotations

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8421


def serve(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    open_browser: bool = True,
) -> int:
    try:
        import uvicorn
    except ImportError:
        print(
            "The dashboard needs the web extra. Install it with:\n"
            "    pip install ai-loadout[dashboard]"
        )
        return 1

    from .server import create_app

    app = create_app()
    url = f"http://{host}:{port}"
    print(f"Loadout dashboard -> {url}   (Ctrl+C to stop)")

    if open_browser:
        import threading
        import webbrowser

        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0
