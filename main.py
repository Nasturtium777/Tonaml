import os
import json
import requests
from bs4 import BeautifulSoup

HISTORY_FILE = "history.json"
TARGET_URL = "https://tonamel.com/search?q=カードゲーム"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def get_latest():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(TARGET_URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    tournaments = []
    
    for a_tag in soup.find_all("a", href=True):
        if "/competition/" in a_tag["href"]:
            url = f"https://tonamel.com{a_tag['href']}" if a_tag['href'].startswith('/') else a_tag['href']
            tournaments.append({"url": url})
            
    print(f"[DEBUG] 取得できた大会件数: {len(tournaments)}件")
    return tournaments

def main():
    if not DISCORD_WEBHOOK_URL:
        print("[ERROR] DISCORD_WEBHOOK_URL が設定されていません。")
        return

    history = load_history()
    new_items = get_latest()
    
    send_count = 0
    for item in new_items:
        if item["url"] not in history:
            res = requests.post(DISCORD_WEBHOOK_URL, json={"content": f"新着大会: {item['url']}"})
            print(f"[DEBUG] Discord送信レスポンス: {res.status_code}")
            history.append(item["url"])
            send_count += 1
            
    print(f"[DEBUG] 送信完了数: {send_count}件")
    save_history(history[-100:])

if __name__ == "__main__":
    main()
