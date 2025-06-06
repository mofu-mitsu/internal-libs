# post_text.py

# ------------------------------
# ★ 必要なライブラリ
# ------------------------------
from atproto import Client
import os
from dotenv import load_dotenv
from pathlib import Path
import requests

# ------------------------------
# ★ 認証情報（.envに書くよ！）
# ------------------------------
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
HANDLE = os.getenv('HANDLE') or exit("❌ HANDLEが設定されていません")
APP_PASSWORD = os.getenv('APP_PASSWORD') or exit("❌ APP_PASSWORDが設定されていません")

# ------------------------------
# ★ 気象庁APIで天気取得（例：東京都）
# ------------------------------
def get_weather():
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        weather = data[0]["timeSeries"][0]["areas"][0]["weathers"][0].lower()
        
        if "雷" in weather:
            return "雷"
        elif "風" in weather:
            return "風"
        elif "雪" in weather:
            return "雪"
        elif "雨" in weather:
            return "雨"
        elif "晴" in weather:
            return "晴れ"
        elif "曇" in weather or "くもり" in weather:
            return "くもり"
        
    return "くもり"  # デフォルト

# ------------------------------
# ★ テンプレ辞書
# ------------------------------
WEATHER_TEMPLATES = {
    "晴れ": "🌤️ 晴れの日は、ねこがのびのびする日！🐱 おひさまの下でおひるねすると、いい夢が見られるかも…？今日のラッキーアイテム：ひんやりジェル",
    "くもり": "🌥 くもりの日は、うさぎがぼんやりする日…🐰 ぬいぐるみをぎゅっと抱いて、優しい時間をすごしてね♡ ラッキー行動：あったかい紅茶を飲むこと",
    "雨": "☔ 雨の日は、カエルがすこしさみしい日…🐸 窓の外の雨音に耳をすませて、ゆっくり深呼吸してみよう ラッキーアイテム：ふわふわのタオル",
    "雪": "❄ 雪の日は、シロクマがまったりする日！🐻‍❄️ 毛布にくるまって、ホットココアでぬくぬくしよう♡ ラッキー行動：好きなぬいと一緒にお昼寝",
    "風": "💨 風の強い日は、いぬがそわそわしちゃう日！🐶 安心できる場所で、好きな音楽を聞いてみてね♪ ラッキーアイテム：お気に入りのタオルケット",
    "雷": "⚡ 雷の日は、ハムスターがちょっとびくびくする日…🐹 でも、毛布の中に隠れてると安心できるよ♡ ラッキー行動：お気に入りのぬいぐるみを抱っこする"
}

# ------------------------------
# ★ 投稿処理
# ------------------------------
client = Client()
client.login(HANDLE, APP_PASSWORD)

weather = get_weather()
message = WEATHER_TEMPLATES.get(weather, WEATHER_TEMPLATES["くもり"])  # デフォルトはくもり

client.send_post(text=message)

print(f"投稿しました: {message}")