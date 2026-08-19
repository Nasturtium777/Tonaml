import os
import json
import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

HISTORY_FILE = "history.json"
# 監視対象のURL（※dateパラメータで該当大会がない場合はパラメータを外すか調整してください）
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
        # PCブラウザのUser-Agentを設定してBot判定による空画面化を防ぐ
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            # 大会リンク要素（/competition/ を含むaタグ）が出現するまで最大20秒待機
            page.wait_for_selector('a[href*="/competition/"]', timeout=20000)
        except Exception as e:
            print(f"[DEBUG] 要素の読み込み待機タイムアウト（または該当大会が0件）: {e}")

        # レンダリング完了を確実にするため2秒固定待機
        page.wait_for_timeout(2000)
        content = page.content()
        browser.close()

    soup = BeautifulSoup(content, "html.parser")
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "/competition/" in href:
            url = href if href.startswith("http") else f"https://tonamel.com{href}"
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
