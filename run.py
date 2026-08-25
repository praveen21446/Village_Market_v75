import threading, time, webbrowser, subprocess, sys
import uvicorn

PORT = 8000

def open_browser():
    time.sleep(2)
    webbrowser.open(f"http://127.0.0.1:{PORT}/")

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.main:app", host="127.0.0.1", port=PORT, reload=False)
