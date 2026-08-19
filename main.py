import os
import json
import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

HISTORY_FILE = "history.json"
TARGET_URL = "https://tonamel.com/competitions?game=XrossStars&region=JP&date=1787065200&nt=0&sr=%E5%9F%BC%E7%8E%89%20%E5%8D%83%E8%91%89%20%E6%9D%B1%E4%BA%AC%20%E7%A5%9E%E5%A5%88%E5%B7%9D"
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
    tournaments = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # networkidle から domcontentloaded に変更（タイムアウト回避）
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        
        # JavaScriptによる要素描画を待つため3秒固定待機
        page.wait_for_timeout(3000)
        
        content = page.content()
        browser.close()

    soup = BeautifulSoup(content, "html.parser")
    for a_tag in soup.find_all("a", href=True):
        if "/competition/" in a_tag["href"]:
            url = f"https://tonamel.com{a_tag['href']}" if a_tag['href'].startswith('/') else a_tag['href']
            if url not in [t["url"] for t in tournaments]:
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
