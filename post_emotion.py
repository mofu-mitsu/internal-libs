# post_emotion.py

from atproto import Client
import os
from dotenv import load_dotenv
from pathlib import Path
import requests
from datetime import datetime
import re
from pytz import timezone
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# ------------------------------
# ★ NGワードカウントと置換処理
# ------------------------------
def count_ng_words(poem):
    ng_words = [
        "プロフィール", "【", "美魔女", "商品", "ニュース", "応募規約",
        "投稿締め切り", "投稿規定", "作品", "ご応募", "コンクール", "掲載",
        "ポエム・コラム", "みりんてゃらしい文章で" * 2,
        "弊社", "投稿作品", "応募", "締切", "募集", "キャンペーン", "ホームページ",
        "記載", "注意事項", "規定", "承諾", "SNS", "送信", "応募方法", "書式",
        "未発表", "発表", "入選", "特典", "料理", "番組", "レシピ", "先生", "NHK", "にんじん"
    ]
    return sum(word in poem for word in ng_words)

def clean_poem(poem):
    ng_words = [
        "プロフィール", "【", "美魔女", "商品", "ニュース", "応募規約",
        "投稿締め切り", "投稿規定", "作品", "ご応募", "コンクール", "掲載",
        "ポエム・コラム", "みりんてゃらしい文章で" * 2,
        "弊社", "投稿作品", "応募", "締切", "募集", "キャンペーン", "ホームページ",
        "記載", "注意事項", "規定", "承諾", "SNS", "送信", "応募方法", "書式",
        "未発表", "発表", "入選", "特典", "料理", "番組", "レシピ", "先生", "NHK", "にんじん"
    ]
    if poem.count("いつも、") >= 3:
        return "みりんてゃ、ちょっと考えすぎちゃったみたい…お茶でも飲んで仕切り直すね☕️"
    if any(poem.strip().startswith(word) for word in ["投稿", "作品", "規定", "応募"]):
        return "みりんてゃ、ちょっと真面目すぎたかも…もう一回書き直してみるね🍵"
    if not poem.strip() or "お散歩" in poem:
        return "みりんてゃ、優しい風に誘われて詩を届けるよ…。そっと待っていてね♡"

    # 「文っぽい区切り」を正規表現でカウント
    sentences = re.split(r'[。！？!?〜]+', poem)
    if len(sentences) >= 4:
        cleaned_parts = ["。".join(sentences[:3]) + "…"]
        return cleaned_parts[0]

    for word in ng_words:
        poem = poem.replace(word, "○○")
    return poem

# ------------------------------
# ★ ポエム生成（open-calm-1b使用）
# ------------------------------
def generate_poem(weather, day_of_week):
    tokenizer = AutoTokenizer.from_pretrained("cyberagent/open-calm-1b")  # 3b試したい場合は"cyberagent/open-calm-3b"
    model = AutoModelForCausalLM.from_pretrained("cyberagent/open-calm-1b")  # 3b試したい場合は"cyberagent/open-calm-3b"
    generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

    print(f"DEBUG: Starting generation - Weather: {weather}, Day: {day_of_week}")
    prompt = f"{weather}の{day_of_week}曜日。みりんてゃが空を見上げて、ふわっと優しく短い詩をつぶやく。自己紹介や指示文、数字、引用、媒体情報、特定の作品名・人物名、カタカナ名詞が連続する語句、実在しない人名・固有名詞、抽象概念や難解な思想は使わず、タイトルに依存せず本文で情景を充実させる。ポエムだけに集中し、3〜5文以内で、1つの自然の情景を描き、読後に優しい余韻が残るようにする。空白や「お散歩」メッセージを避ける。"
    print(f"DEBUG: Prompt: {prompt}")

    output = generator(prompt, max_length=150, do_sample=True, temperature=0.9, repetition_penalty=1.2)[0]['generated_text']
    print(f"DEBUG: Raw Output: {output}")
    generated_poem = output[len(prompt):].strip()
    print(f"DEBUG: Generated Poem (raw strip): {generated_poem}")

    print(f"Prompt: {prompt}")
    print(f"Raw Output: {output}")
    print(f"Final Poem (before processing): {generated_poem}")

    with open("poem_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone('Asia/Tokyo'))}: {generated_poem}\n")

    if "詩は" in generated_poem and "作者の心" in generated_poem and "サイバー" in generated_poem:
        print(f"DEBUG: Philosophy mode detected - Poem: {generated_poem}")
        return "みりんてゃ、優しい風に誘われて詩を届けるよ…。そっと待っていてね♡"

    generated_poem = clean_poem(generated_poem)
    print(f"DEBUG: After clean_poem: {generated_poem}")

    if count_ng_words(generated_poem) > 2:
        print(f"DEBUG: NG words count > 2 - Poem: {generated_poem}, Count: {count_ng_words(generated_poem)}")
        return "みりんてゃ、優しい風に誘われて詩を届けるよ…。そっと待っていてね♡"

    if not generated_poem.strip():
        print(f"DEBUG: Poem is empty or whitespace only - Poem: {generated_poem}, Output: {output}")
        return "みりんてゃ、優しい風に誘われて詩を届けるよ…。そっと待っていてね♡"

    print(f"DEBUG: Final Poem: {generated_poem}")
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
    print(f"DEBUG: Weather API response status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        text = data[0]["timeSeries"][0]["areas"][0]["weathers"][0].lower()
        print(f"DEBUG: Raw weather data: {text}")
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
print(f"DEBUG: Attempting login with HANDLE: {HANDLE}")
client.login(HANDLE, APP_PASSWORD)
print(f"DEBUG: Login successful")

now = datetime.now(timezone('Asia/Tokyo'))
weather = get_weather()
day_of_week = get_day_of_week(now)
message = generate_poem(weather, day_of_week)

client.send_post(text=message)
print(f"DEBUG: Posted message: {message}")
print(f"投稿しました: {message}")