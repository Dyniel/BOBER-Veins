"""
Web Demonstrator server launcher.
Serves the interactive dashboard locally without requiring external heavy server dependencies.
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path


def launch_local_demonstrator(port: int = 8501, open_browser: bool = False) -> None:
    """Launches local web server for BOBER Veins demonstrator."""
    demo_dir = Path(__file__).resolve().parent.parent.parent.parent / "demo"
    if not demo_dir.exists():
        demo_dir = Path("demo").resolve()

    os.chdir(demo_dir)
    handler = http.server.SimpleHTTPRequestHandler

    print(f"================================================================")
    print(f"  BOBER Veins / VascuShift-GPINN Interactive Demonstrator")
    print(f"  Serving at: http://localhost:{port}")
    print(f"  Directory:  {demo_dir}")
    print(f"================================================================")

    if open_browser:
        webbrowser.open(f"http://localhost:{port}")

    with socketserver.TCPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down demonstrator server.")

