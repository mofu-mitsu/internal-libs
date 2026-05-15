# follow_notifyX_bot.py
import os
import json
import random
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

HANDLE = os.getenv("HANDLE")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
CT0 = os.getenv("CT0")
CLEAN_HANDLE = HANDLE.replace("@", "")

# 👇👇【ここを追加！】さっきコピーしたGASのURL👇👇
GAS_WEBHOOK_URL = os.getenv("https://script.google.com/macros/s/AKfycbyvHS9-ORsduvU2aU6HS6RRKyHmlRANicIbvNxe_Pa2ff5EV8icvO3ADcQxDvKY8qaN/exec")

STATE_FILE = "/root/mirin_bot/follow_state.json"

def send_email_via_gas(subject, body):
    """GAS経由でGmailに通知を送る魔法"""
    if not GAS_WEBHOOK_URL:
        print("❌ GASのURLが設定されてないよ！")
        return
        
    try:
        data = {
            "subject": subject,
            "body": body
        }
        # GASのURLにデータを投げつける！（これならポート制限に引っかからない！）
        response = requests.post(GAS_WEBHOOK_URL, json=data)
        if response.status_code == 200:
            print("📧 GAS経由でメール通知を送ったよ！")
        else:
            print(f"❌ GAS通信エラー: {response.status_code}")
    except Exception as e:
        print(f"❌ ネットワークエラー: {e}")

def get_x_lists(page):
    def scrape_list(url):
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)
        for _ in range(5):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(1000)
        
        handles = page.locator('div[dir="ltr"]').filter(has_text="@").all_inner_texts()
        return set(h.replace("@", "").strip().lower() for h in handles if h.startswith("@"))

    print("👥 リスト取得中...")
    followers = scrape_list(f"https://x.com/{CLEAN_HANDLE}/followers")
    following = scrape_list(f"https://x.com/{CLEAN_HANDLE}/following")
    return followers, following

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])
        page = context.new_page()

        try:
            current_followers, current_following = get_x_lists(page)
            current_state = {
                "followers": list(current_followers),
                "following": list(current_following)
            }

            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r") as f:
                    old_state = json.load(f)
                old_followers = set(old_state.get("followers", []))
                old_following = set(old_state.get("following", []))

                new_fans = current_followers - old_followers
                mutuals_last_time = old_followers & old_following
                rimmed_by_mutuals = mutuals_last_time - current_followers

                report = []
                if new_fans:
                    report.append(f"💖 新しいフォロワーさん（{len(new_fans)}名）:\n" + "\n".join(f"@{h}" for h in new_fans))
                if rimmed_by_mutuals:
                    report.append(f"💔 相互さんにリムられたよ…（{len(rimmed_by_mutuals)}名）:\n" + "\n".join(f"@{h}" for h in rimmed_by_mutuals))

                if report:
                    # GAS経由で送信！
                    send_email_via_gas("🎀 みりんてゃ：フォロー状況の変化をお知らせ！", "\n\n".join(report))
                else:
                    print("✨ 特に変化はなかったよ！平和！")

            with open(STATE_FILE, "w") as f:
                json.dump(current_state, f)

        finally:
            browser.close()

if __name__ == "__main__":
    main()
