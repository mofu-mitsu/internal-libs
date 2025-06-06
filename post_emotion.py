# post_emotion.py

from atproto import Client
import os
from dotenv import load_dotenv
from pathlib import Path
import requests
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# ------------------------------
# ★ NGワードカウントと置換処理
# ------------------------------
def count_ng_words(poem):
    ng_words = ["プロフィール", "【", "さん", "美魔女", "商品", "ニュース", "応募規約", "未発表", "応募作品", "字程度"]
    return sum(word in poem for word in ng_words)

def clean_poem(poem):
    ng_words = ["プロフィール", "【", "さん", "美魔女", "商品", "ニュース", "応募規約", "未発表", "応募作品", "字程度"]
    for word in ng_words:
        poem = poem.replace(word, "○○")
    return poem

# ------------------------------
# ★ ポエム生成（open-calm-1b使用）
# ------------------------------
def generate_poem(weather, day_of_week):
    tokenizer = AutoTokenizer.from_pretrained("cyberagent/open-calm-1b")
    model = AutoModelForCausalLM.from_pretrained("cyberagent/open-calm-1b")
    generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

    prompt = f"{weather}の{day_of_week}に合う、みりんてゃらしい癒し系の**一言ポエム**を作ってください。セリフ形式ではなく、詩的で短く、優しい文体にしてください。"
    output = generator(prompt, max_length=60, do_sample=True, temperature=0.8)[0]['generated_text']
    generated_poem = output[len(prompt):].strip()  # プロンプト部分を除去

    # デバッグ用ログ
    print(f"Prompt: {prompt}")
    print(f"Raw Output: {output}")
    print(f"Final Poem: {generated_poem}")

    # ログ保存
    with open("poem_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()}: {generated_poem}\n")

    # 哲学モード検知
    if "詩は" in generated_poem and "作者の心" in generated_poem and "サイバー" in generated_poem:
        return "みりんてゃ、サイバー空間でポem迷子になっちゃったみたい♡ ちょっと探してくるね…！"

    # NGワード置換
    generated_poem = clean_poem(generated_poem)

    # NGワードが3つ以上なら再生成
    if count_ng_words(generated_poem) > 2:
        return "みりんてゃ、おやつ食べながら考えてたら、ポエムがどっかいっちゃったみたい…またすぐ届けるね♡"

    # 空欄対策
    if not generated_poem.strip():
        return "みりんてゃ、言葉を探しにお散歩に出かけちゃったみたい...またすぐ帰ってくるね♡"

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