# weatherX_bot.py
import os
import random
import time
import requests
import re
from pathlib import Path
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# 環境変数読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

AUTH_TOKEN = os.getenv('AUTH_TOKEN') or exit("❌ AUTH_TOKENがありません")
CT0 = os.getenv('CT0') or exit("❌ CT0がありません")

# ------------------------------
# ★ みりんてゃの語彙設定
# ------------------------------
GREETINGS = [
    "ねぇねぇ、明日の準備はできた？お天気教えるね☁️",
    "あしたのお天気、みりんてゃがパトロールしてきたよっ🐾",
    "明日のこと気にならない？みりんが調べてあげたよ♡",
    "みんな〜！明日の気温とか大丈夫そう？教えるねっ🎀"
]

LUCKY_ITEMS = [
    "ぬくぬくの毛布", "あまいホットココア", "お気に入りのぬいぐるみ", 
    "いちごのキャンディ", "ふわふわのタオル", "推しのアクスタ",
    "可愛いヘアピン", "おそろいのリップ", "あたたかいお茶"
]

# ------------------------------
# ★ 全国主要都市のコード
# ------------------------------
CITIES = {
    "130000": "東京",
    "270000": "大阪",
    "400000": "福岡",
    "016000": "札幌"
}

def get_weather_and_temp():
    """全国の天気と気温を文章形式で組み立てる"""
    weather_parts = []
    
    for code, name in CITIES.items():
        url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # 1. 天気アイコン取得
                weathers = data[0]["timeSeries"][0]["areas"][0]["weathers"]
                target_idx = 1 if len(weathers) > 1 else 0
                raw_weather = weathers[target_idx]
                
                if "雷" in raw_weather: icon = "⚡️"
                elif "雪" in raw_weather: icon = "❄️"
                elif "雨" in raw_weather: icon = "☔️"
                elif "晴" in raw_weather: icon = "☀️"
                else: icon = "☁️"
                
                # 2. 気温取得 (timeSeries[2]にある)
                # 多くの地点では index 0 が今日、index 1 が明日
                temp_area = data[0]["timeSeries"][2]["areas"][0]
                temps = temp_area.get("temps", [])
                
                if len(temps) >= 4: # 夕方以降のデータ取得時
                    t_min = temps[2]
                    t_max = temps[3]
                elif len(temps) >= 2:
                    t_min = temps[0]
                    t_max = temps[1]
                else:
                    t_min, t_max = "？", "？"
                
                weather_parts.append(f"{name}は{icon}({t_max}℃/{t_min}℃)")
            else:
                weather_parts.append(f"{name}は🐾")
        except:
            weather_parts.append(f"{name}は🐾")
        
        time.sleep(1) # API負荷軽減

    return "、".join(weather_parts) + "だよっ🎀"

def main():
    print("🚀 全国お天気Bot（X版：完全版）起動！")

    # 1. メッセージ組み立て
    greeting = random.choice(GREETINGS)
    weather_info = get_weather_and_temp()
    lucky_item = random.choice(LUCKY_ITEMS)
    
    # リスト形式を避け、あえて読点（、）で繋いだ自然な独り言にする
    message = f"{greeting}\n\n{weather_info}\n\nあしたのラッキーアイテムは【{lucky_item}】なのっ♡\n\n#みりんてゃ #お天気"
    
    print(f"💬 投稿内容:\n{message}")

    # ロボット避けのランダム待機（1〜3分）
    wait_time = random.randint(60, 180)
    print(f"⏳ 人間っぽく見せるため {wait_time}秒 待機します...")
    time.sleep(wait_time)

    with sync_playwright() as p:
        # 🎭 最強の偽装設定（UA回転）
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=random.choice(user_agents),
            locale="ja-JP",
            timezone_id="Asia/Tokyo"
        )
        
        context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])

        page = context.new_page()
        # ステルス魔法
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = { runtime: {} };
        """)

        try:
            print("🌐 Xの投稿画面にアクセス中...")
            page.goto("https://x.com/compose/post", timeout=60000)
            page.wait_for_timeout(7000)

            # 🖱️ 画面をウロウロする（人間偽装）
            for _ in range(2):
                page.mouse.move(random.randint(100, 1000), random.randint(100, 600))
                time.sleep(1)

            textbox_selector = 'div[data-testid="tweetTextarea_0"]'
            page.wait_for_selector(textbox_selector, timeout=15000)

            print("⌨️ テキストを入力中...")
            page.fill(textbox_selector, message)
            page.wait_for_timeout(2000)

            # 👇👇【最強の送信ロジック：クリックをやめてショートカットキー！】👇👇
            print("🎯 入力欄をもう一度クリックして確実にフォーカス...")
            page.click(textbox_selector)
            page.wait_for_timeout(1000)

            print("🚀 ショートカットキーでポスト送信！")
            page.keyboard.press("Control+Enter")

            # 投稿完了までじっくり待つ（空振り防止）
            print("⏳ Xのサーバーに届くまで見守るよ...")
            page.wait_for_timeout(10000) 
            
            # 念のため証拠写真を撮る
            page.screenshot(path="/root/mirin_bot/weather_result.png")
            print("✨ 天気予報の投稿完了！ ✨")

        except Exception as e:
            print(f"❌ エラー起きちゃった…ぴえん🥺\n{e}")
            page.screenshot(path="/root/mirin_bot/weather_error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
