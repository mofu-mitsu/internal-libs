# postX_emotion.py
import os
import random
import time
import re
import requests
from pathlib import Path
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv
from groq import Groq
from playwright.sync_api import sync_playwright

# 1. 環境変数の読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

AUTH_TOKEN = os.getenv('AUTH_TOKEN')
CT0 = os.getenv('CT0')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# ------------------------------
# ★ クリーニング・NGワード処理
# ------------------------------
def clean_poem(poem):
    # 文っぽい区切りを正規表現でカウント
    sentences = re.split(r'[。！？♡♪]+', poem)
    if len(sentences) >= 4:
        cleaned_parts = ["。".join(sentences[:3]) + "…"]
        poem = cleaned_parts[0]
    
    poem = re.sub(r'[。、！？♡♪]{2,}', lambda m: m.group(0)[0], poem)
    poem = re.sub(r'\n{2,}', '\n', poem)
    return poem.strip()

# ------------------------------
# ★ 天気取得 (気象庁API)
# ------------------------------
def get_weather():
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            areas = data[0]["timeSeries"][0]["areas"]
            selected_area = next((area for area in areas if area["area"]["code"] == "130010"), None)
            pop = data[0]["timeSeries"][1]["areas"][0]["pops"][1]
            temp_data = data[0]["timeSeries"][2]["areas"][0]
            temp_min = temp_data["temps"][0] if "temps" in temp_data else "？"
            temp_max = temp_data["temps"][1] if "temps" in temp_data else "？"
            weather_text = selected_area["weathers"][0]
            
            # 天気アイコン判定
            weather = "くもり"
            if "晴" in weather_text: weather = "晴れ"
            if "雨" in weather_text: weather = "雨"
            if "雪" in weather_text: weather = "雪"
            if "雷" in weather_text: weather = "雷"
            
            return weather, pop, temp_min, temp_max
    except:
        pass
    return "くもり", "？", "？", "？"

# ------------------------------
# ★ ポエム生成 (Groq)
# ------------------------------
def generate_poem(weather, day_of_week, temp_min, temp_max, pop):
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        prompt = f"{weather}の{day_of_week}、降水確率{pop}%、気温{temp_min}-{temp_max}℃。みりんてゃが空を見上げて浮かんだ詩を作って。"
        
        system_prompt = (
            "あなたは「みりんてゃ」、地雷系ENFPのあざと可愛い女の子！\n"
            "口調：タメ口で『〜なのっ♡』『〜よぉ？♪』『えへへ〜♡』が特徴！\n"
            "役割：天気と曜日を元に、短くやさしい詩を1つだけ作って。50文字以内。"
        )

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.7
        )
        return clean_poem(response.choices[0].message.content.strip())
    except:
        return "えへへ〜♡ 空を見てたら、きみに会いたくなっちゃったのっ♪"

def main():
    if not AUTH_TOKEN or not GROQ_API_KEY:
        print("❌ 設定が足りないよ！")
        return

    # データ準備
    now = datetime.now(timezone('Asia/Tokyo'))
    days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    day_of_week = days[now.weekday()]
    weather, pop, t_min, t_max = get_weather()
    poem = generate_poem(weather, day_of_week, t_min, t_max, pop)
    
    # スポット選択
    spot = random.choice(["渋谷", "新宿", "池袋", "原宿", "秋葉原", "歌舞伎町", "大宮", "川越"])
    full_message = f"{spot}の{weather}の{day_of_week}。{poem}"
    
    print(f"🚀 朝のポエム投稿Bot起動！\n💬 内容: {full_message}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            page.goto("https://x.com/compose/post")
            page.wait_for_timeout(7000)
            page.fill('div[data-testid="tweetTextarea_0"]', full_message)
            page.wait_for_timeout(2000)
            page.keyboard.press("Control+Enter")
            page.wait_for_timeout(5000)
            print("✨ 朝のポエム投稿成功！ ✨")
        except Exception as e:
            print(f"❌ エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
