import os
import json
import requests
from bs4 import BeautifulSoup

HISTORY_FILE = "history.json"
TARGET_URL = "https://tonamel.com/competitions?game=XrossStars&region=JP&date=1787065200&nt=0&sr=%E5%9F%BC%E7%8E%89%20%E5%8D%83%E8%91%89%20%E6%9D%B1%E4%BA%AC%20%E7%A5%9E%E5%A5%88%E5%B7%9D"
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def get_latest():
    # 実際のTonamelのHTML構造に応じてここを調整してください
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(TARGET_URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    tournaments = []
    for a_tag in soup.find_all("a", href=True):
        if "/competition/" in a_tag["href"]:
            url = f"https://tonamel.com{a_tag['href']}" if a_tag['href'].startswith('/') else a_tag['href']
            tournaments.append({"url": url})
    return tournaments

def main():
    history = load_history()
    new_items = get_latest()
    for item in new_items:
        if item["url"] not in history:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"新着大会: {item['url']}"})
            history.append(item["url"])
    save_history(history[-100:])

if __name__ == "__main__":
    main()
