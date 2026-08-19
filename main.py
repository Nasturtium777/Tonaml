import os
import json
import time
import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

HISTORY_FILE = "history.json"
# ※日付を限定しない場合は URL から `&date=1787065200` を外すか調整してください
TARGET_URL = "https://tonamel.com/competitions?game=XrossStars&region=JP&nt=0&sr=%E5%9F%BC%E7%8E%89%20%E5%8D%83%E8%91%89%20%E6%9D%B1%E4%BA%AC%20%E7%A5%9E%E5%A5%88%E5%B7%9D"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def auto_scroll(page):
    """ページの一番下までスクロールして追加コンテンツ（無限スクロール）を読み込ませる"""
    previous_height = None
    while True:
        current_height = page.evaluate("document.body.scrollHeight")
        if previous_height == current_height:
            break
        previous_height = current_height
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        page.wait_for_timeout(1500)  # スクロール後のデータ読み込み待機

def get_latest():
    tournaments = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector('a[href*="/competition/"]', timeout=20000)
            
            # ページを一番下までスクロールしてすべての大会を読み込む
            auto_scroll(page)
            
        except Exception as e:
            print(f"[DEBUG] 要素の読み込み待機タイムアウト（または該当大会が0件）: {e}")

        content = page.content()
        browser.close()

    soup = BeautifulSoup(content, "html.parser")
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "/competition/" in href:
            url = href if href.startswith("http") else f"https://tonamel.com{href}"
            
            if url not in [t["url"] for t in tournaments]:
                lines = [line.strip() for line in a_tag.get_text(separator="\n").split("\n") if line.strip()]
                
                title = "名称不明の大会"
                date_str = "日時未記載"

                title_elem = a_tag.select_one('[class*="title"], [class*="name"], h2, h3')
                date_elem = a_tag.select_one('[class*="date"], [class*="time"]')

                if title_elem and title_elem.text.strip():
                    title = title_elem.text.strip()
                elif lines:
                    title = max(lines, key=len)

                if date_elem and date_elem.text.strip():
                    date_str = date_elem.text.strip()
                else:
                    for line in lines:
                        if any(char in line for char in ["/", "月", "日", ":"]) and len(line) < 30:
                            date_str = line
                            break

                tournaments.append({
                    "url": url,
                    "title": title,
                    "date": date_str
                })
                
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
            content = (
                f"🏆 **新着大会情報**\n"
                f"**大会名:** {item['title']}\n"
                f"📅 **日時:** {item['date']}\n"
                f"🔗 **URL:** {item['url']}"
            )
            
            res = requests.post(DISCORD_WEBHOOK_URL, json={"content": content})
            print(f"[DEBUG] Discord送信レスポンス: {res.status_code}")
            
            # Discordの連投制限（Rate Limit）を防ぐために1秒待機
            time.sleep(1)
            
            history.append(item["url"])
            send_count += 1
            
    print(f"[DEBUG] 送信完了数: {send_count}件")
    save_history(history[-100:])

if __name__ == "__main__":
    main()
