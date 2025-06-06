# post_emotion.py

from atproto import Client
import os
from dotenv import load_dotenv
from pathlib import Path
import requests
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# ------------------------------
# ★ ポエム生成（open-calm-1b使用）
# ------------------------------
def generate_poem(weather, day_of_week):
    tokenizer = AutoTokenizer.from_pretrained("cyberagent/open-calm-1b")
    model = AutoModelForCausalLM.from_pretrained("cyberagent/open-calm-1b")
    generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

    prompt = f"{weather}の{day_of_week}にぴったりな、やさしくてふんわりした一言ポエムをひとつ作ってください。"
    output = generator(prompt, max_length=60, do_sample=True, temperature=0.8)[0]['generated_text']
    generated_poem = output[len(prompt):].strip()  # プロンプト部分を除去

    # デバッグ用ログ
    print(f"Prompt: {prompt}")
    print(f"Raw Output: {output}")
    print(f"Final Poem: {generated_poem}")

    # オプション：内容フィルター
    if "プロフィール" in generated_poem or "【" in generated_poem:
        return "えへへ〜♡ 何か変になっちゃったなのっ！また挑戦するね♪"

    return generated_poem

# ------------------------------
# ★ 天気取得
# ------------------------------
WEATHER_KEYWORDS = {
    "雷": "雷",
    "風": "風",
    "雪": "雪",
    "雨": "雨",
    "晴": "晴れ",
    "曇": "くもり",
    "くもり": "くもり"
}

def get_weather():
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
    response = requests.get(url)
    if response.status_code == 200:
        text = response.json()[0]["timeSeries"][0]["areas"][0]["weathers"][0].lower()
        for keyword, label in WEATHER_KEYWORDS.items():
            if keyword in text:
                return label
    return "くもり"

# ------------------------------
# ★ 曜日取得
# ------------------------------
def get_day_of_week(now):
    days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    return days[now.weekday()]

# ------------------------------
# ★ 認証と投稿
# ------------------------------
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
HANDLE = os.getenv('HANDLE') or exit("❌ HANDLEが設定されていません")
APP_PASSWORD = os.getenv('APP_PASSWORD') or exit("❌ APP_PASSWORDが設定されていません")

client = Client()
client.login(HANDLE, APP_PASSWORD)

now = datetime.now()
weather = get_weather()
day_of_week = get_day_of_week(now)
message = generate_poem(weather, day_of_week)

client.send_post(text=message)
print(f"投稿しました: {message}")