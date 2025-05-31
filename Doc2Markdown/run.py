# run.py
import os
import subprocess

if __name__ == "__main__":
    port = os.environ.get("PORT", "8000")
    cmd = [
        "gunicorn", 
        "-w", "4", 
        "-k", "uvicorn.workers.UvicornWorker",
        "app.app:app",
        "--bind", f"0.0.0.0:{port}",
        "--timeout", "600"
    ]
    subprocess.run(cmd)