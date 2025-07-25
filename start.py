import subprocess
import webbrowser
import os
import sys
import time
import socket

def wait_for_server(host, port, timeout=30):
    """Wait until the server is accepting connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False

def run():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    manage_py = os.path.join(base_dir, 'manage.py')

    # Start the Django server in a new subprocess
    subprocess.Popen([sys.executable, manage_py, 'runserver'], cwd=base_dir)

    # Wait until the server is ready
    if wait_for_server("127.0.0.1", 8000):
        webbrowser.open("http://127.0.0.1:8000")
    else:
        print("⚠️ Server did not start in time.")

if __name__ == "__main__":
    run()
