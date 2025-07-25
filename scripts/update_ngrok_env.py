# scripts/update_ngrok_env.py

import os
import time
import requests

ENV_PATH = ".env"
MAX_RETRIES = 30
RETRY_DELAY = 1.5  # seconds

def wait_for_ngrok_tunnel():
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get("http://ngrok:4040/api/tunnels")
            data = response.json()
            tunnels = data.get("tunnels", [])
            for t in tunnels:
                if t["proto"] == "https":
                    return t["public_url"]
        except Exception as e:
            pass  # ignore errors until ngrok is ready

        print(f"🔄 Waiting for ngrok tunnel... (Attempt {attempt + 1}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY)
    raise Exception("❌ Ngrok tunnel not ready after retries.")

def update_env_file(new_url):
    updated = False
    lines = []
    with open(ENV_PATH, "r") as file:
        for line in file:
            if line.startswith("NGROK_BASE_URL="):
                lines.append(f"NGROK_BASE_URL={new_url}\n")
                updated = True
            else:
                lines.append(line)
    if not updated:
        lines.append(f"NGROK_BASE_URL={new_url}\n")
    with open(ENV_PATH, "w") as file:
        file.writelines(lines)
    print(f"✅ Updated NGROK_BASE_URL to {new_url}")

if __name__ == "__main__":
    url = wait_for_ngrok_tunnel()
    update_env_file(url)
