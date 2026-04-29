# ------------------------------
# ★ 必要なライブラリ
# ------------------------------
from atproto import Client, models
import os
from dotenv import load_dotenv
from pathlib import Path
import requests
from PIL import Image
import io
from datetime import datetime

# ------------------------------
# ★ 認証情報
# ------------------------------
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
HANDLE = os.getenv('HANDLE') or exit("❌ HANDLEが設定されていません")
APP_PASSWORD = os.getenv('APP_PASSWORD') or exit("❌ APP_PASSWORDが設定されていません")

# ------------------------------
# ★ 東京の天気
# ------------------------------
def get_weather():
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
    try:
        data = requests.get(url, timeout=10).json()
        weather = data[0]["timeSeries"][0]["areas"][0]["weathers"][0]

        if "雷" in weather: return "雷"
        if "風" in weather: return "風"
        if "雪" in weather: return "雪"
        if "雨" in weather: return "雨"
        if "晴" in weather: return "晴れ"
        return "くもり"

    except:
        return "くもり"

# ------------------------------
# ★ 全国の天気＋気温
# ------------------------------
CITIES = {
    "130000": "🗼東京",
    "270000": "🐙大阪",
    "400000": "🍜福岡",
    "016000": "⛄️札幌"
}

def parse_weather(text):
    if "雷" in text: return "⚡"
    if "雪" in text: return "❄️"
    if "雨" in text: return "☔"
    if "晴" in text: return "☀️"
    return "☁️"

def get_nationwide_weather():
    results = []

    for code, name in CITIES.items():
        try:
            url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
            data = requests.get(url, timeout=5).json()

            weather = data[0]["timeSeries"][0]["areas"][0]["weathers"][0]
            icon = parse_weather(weather)

            temps = data[0]["timeSeries"][1]["areas"][0].get("temps")
            temp = temps[0] if temps and temps[0] else "--"

            results.append(f"{name}：{icon} {temp}℃")

        except:
            results.append(f"{name}：🐾")

    return "\n".join(results)

# ------------------------------
# ★ 季節＆ラッキー
# ------------------------------
def get_season():
    m = datetime.now().month
    if m in [12,1,2]: return "winter"
    if m in [3,4,5]: return "spring"
    if m in [6,7,8]: return "summer"
    return "autumn"

def get_lucky_item():
    return {
        "winter":"ぬくぬくカイロ",
        "spring":"さくらミスト",
        "summer":"ひんやりジェル",
        "autumn":"ほっこりブランケット"
    }[get_season()]

# ------------------------------
# ★ テンプレ
# ------------------------------
WEATHER_TEMPLATES = {
    "晴れ": f"""🌤️ 東京の天気占い

晴れの日は、ねこがのびのびする日！🐱  
    おひさまの下でおひるねすると、いい夢が見られるかも…？

🌟ラッキーアイテム：{get_lucky_item()}""",

    "くもり": """🌥 東京の天気占い

くもりの日は、うさぎがぼんやりする日…🐰  
ぬいぐるみをぎゅっと抱いて、優しい時間をすごしてね♡

☕ラッキー行動：紅茶を飲む""",

    "雨": """☔ 東京の天気占い

雨の日は、カエルがすこしさみしい日…🐸  
窓の外の雨音に耳をすませて、ゆっくり深呼吸してみよう

🧺ラッキー：ふわふわタオル""",

    "雪": """❄ 東京の天気占い

雪の日は、シロクマがまったりする日！🐻‍❄️  
毛布にくるまって、ホットココアでぬくぬくしよう♡

🧸ラッキー：お昼寝""",

    "風": """💨 東京の天気占い

風の強い日は、いぬがそわそわしちゃう日！🐶  
安心できる場所で、好きな音楽を聞いてみてね♪

🎧ラッキー：音楽""",

    "雷": """⚡ 東京の天気占い

雷の日は、ハムスターがちょっとびくびくする日…🐹  
でも、毛布の中に隠れてると安心できるよ♡

🧸ラッキー：ぬいぐるみ"""
}

# ------------------------------
# ★ 画像アップロード（そのまま）
# ------------------------------
def upload_image(client, image_path):
    img = Image.open(image_path)

    # ⭐これ追加（超重要）
    if img.mode != "RGB":
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)

    blob = client.com.atproto.repo.upload_blob(buffer.getvalue())
    return blob.blob

# ------------------------------
# ★ 投稿
# ------------------------------
def post_weather_with_image(image_path):
    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    weather = get_weather()
    base_text = WEATHER_TEMPLATES.get(weather, WEATHER_TEMPLATES["くもり"])

    nationwide = get_nationwide_weather()

    message = f"""{base_text}

ーーー

🗾 全国のお天気
{nationwide}"""

    print(message)

    blob = upload_image(client, image_path)

    embed = models.AppBskyEmbedImages.Main(images=[
        models.AppBskyEmbedImages.Image(
            alt="天気イラスト",
            image=blob
        )
    ])

    client.send_post(text=message, embed=embed)
    print("✅ 投稿完了！")

# ------------------------------
# ★ 実行
# ------------------------------
if __name__ == "__main__":
    print("🤖 天気Bot起動")
    post_weather_with_image("images/IMG_5849.png")