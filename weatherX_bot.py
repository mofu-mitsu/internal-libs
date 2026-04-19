# weatherX_bot.py
import os
import random
import time
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# 環境変数の読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

AUTH_TOKEN = os.getenv('AUTH_TOKEN') or exit("❌ AUTH_TOKENがありません")
CT0 = os.getenv('CT0') or exit("❌ CT0がありません")

# ------------------------------
# ★ テンプレ辞書（みりんてゃの挨拶）
# ------------------------------
GREETINGS = [
    "みんな〜！明日の天気調べといたよっ🎀",
    "あしたのお天気予報、みりんてゃがお届けするね♡",
    "ねぇねぇ、明日の準備はできた？お天気教えるね☁️",
    "明日の日本列島、みりんてゃがパトロールしてきたよっ🐾",
    "あしたの天気、気にならない？みりんが教えてあげる♡"
]

LUCKY_ITEMS = [
    "ぬくぬくの毛布", "あまいホットココア", "お気に入りのぬいぐるみ", 
    "いちごのキャンディ", "ふわふわのタオル", "推しのアクスタ",
    "可愛いヘアピン", "おそろいのリップ", "あたたかいお茶"
]

# ------------------------------
# ★ 気象庁APIで全国の【明日】の天気を取得
# ------------------------------
CITIES = {
    "130000": "🗼東京",
    "270000": "🐙大阪",
    "400000": "🍜福岡",
    "016000": "⛄️札幌"
}

def get_nationwide_weather():
    weather_results = []
    
    for code, name in CITIES.items():
        url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # timeSeries[0] が天気。weathers[1] が「明日」の天気
                # ※気象庁APIの仕様上、夕方以降は [1] が明日になる
                weathers = data[0]["timeSeries"][0]["areas"][0]["weathers"]
                
                # 取得するインデックス（基本は1だが、配列が短い場合は0）
                target_idx = 1 if len(weathers) > 1 else 0
                raw_weather = weathers[target_idx]

                # シンプルな絵文字に変換
                if "雷" in raw_weather: icon = "⚡️"
                elif "雪" in raw_weather: icon = "❄️"
                elif "雨" in raw_weather: icon = "☔️"
                elif "晴" in raw_weather: icon = "☀️"
                else: icon = "☁️"
                
                weather_results.append(f"{name}: {icon}")
            else:
                weather_results.append(f"{name}: 🐾")
        except Exception as e:
            print(f"⚠️ {name} の天気取得エラー: {e}")
            weather_results.append(f"{name}: 🐾")
            
        time.sleep(1) # APIに優しくするため1秒待機
        
    return "\n".join(weather_results)

# ------------------------------
# ★ 人間っぽく入力する関数
# ------------------------------
def random_sleep(min_sec=1.0, max_sec=3.0):
    time.sleep(random.uniform(min_sec, max_sec))

def human_like_typing(page, selector, text):
    page.click(selector)
    random_sleep(0.5, 1.0)
    page.fill(selector, text)
    random_sleep(1.0, 2.0)

# ------------------------------
# ★ メイン処理
# ------------------------------
def main():
    print("🚀 全国お天気Bot（X版）起動！")

    # 1. 天気予報のメッセージを組み立てる
    greeting = random.choice(GREETINGS)
    weathers = get_nationwide_weather()
    lucky_item = random.choice(LUCKY_ITEMS)
    
    # ハッシュタグをつける
    message = f"{greeting}\n\n{weathers}\n\n🍀明日のラッキーアイテム🍀\n【{lucky_item}】\n\n#明日の天気 #天気予報 #みりんてゃ"
    
    print(f"💬 投稿内容:\n{message}")

    # ロボット避けのランダム待機（1〜3分）
    wait_time = random.randint(60, 180)
    print(f"⏳ 人間っぽく見せるため {wait_time}秒 待機します...")
    time.sleep(wait_time)

    with sync_playwright() as p:
        # 🎭 最強の偽装設定
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': random.randint(720, 1080)},
            user_agent=random.choice(user_agents),
            locale="ja-JP",
            timezone_id="Asia/Tokyo"
        )
        
        context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])

        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ja-JP', 'ja']});
            window.navigator.chrome = { runtime: {} };
        """)

        try:
            print("🌐 Xの投稿画面にアクセス中...")
            page.goto("https://x.com/compose/post", timeout=60000)
            page.wait_for_timeout(5000)

            print("👀 画面を見渡してるフリをするよ…")
            for _ in range(3):
                page.mouse.move(random.randint(100, 1000), random.randint(100, 600))
                random_sleep(0.5, 1.5)

            textbox_selector = 'div[data-testid="tweetTextarea_0"]'
            page.wait_for_selector(textbox_selector, timeout=15000)

            print("⌨️ テキストを入力中...")
            human_like_typing(page, textbox_selector, message)

            print("🚀 ポストボタン（送信）を強制クリック！")
            post_button = page.locator('button[data-testid="tweetButton"]')
            post_button.hover()
            random_sleep(0.5, 1.0)
            post_button.click(force=True)

            print("⏳ Xのサーバーに届くまで見守るよ...")
            try:
                success_toast = page.locator('div[data-testid="toast"]').filter(has_text=re.compile(r"送信|sent", re.IGNORECASE))
                success_toast.wait_for(state="visible", timeout=30000)
                print("✨ 天気予報の投稿完了！みりんてゃえらいっ！ ✨")
            except Exception:
                print("⚠️ 30秒待っても『送信完了』の通知が出なかったよ！")
                page.screenshot(path="/root/mirin_bot/weather_error.png")
                print("📸 証拠写真（weather_error.png）を撮ったよ！")
                raise Exception("投稿の空振り、またはシャドウバンの可能性あり！")

            page.wait_for_timeout(3000)

        except Exception as e:
            print(f"❌ エラー起きちゃった…ぴえん🥺\n{e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
