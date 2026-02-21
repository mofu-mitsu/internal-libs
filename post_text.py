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
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
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

    except Exception as e:
        print(f"⚠️ 気象庁APIエラー: {e}")
        return "くもり"

def get_season():
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"

def get_lucky_item():
    season = get_season()
    if season == "winter":
        return "ぬくぬくカイロ"
    elif season == "summer":
        return "ひんやりジェル"
    elif season == "spring":
        return "さくらミスト"
    else:
        return "ほっこりブランケット"

# ------------------------------
# ★ テンプレ辞書
# ------------------------------
WEATHER_TEMPLATES = {
    "晴れ": f"""🌤️ 晴れの日は、ねこがのびのびする日！🐱  
    おひさまの下でおひるねすると、いい夢が見られるかも…？  
    
    🌟今日のラッキーアイテム：{get_lucky_item()}""",
    "くもり": """🌥 くもりの日は、うさぎがぼんやりする日…🐰  
ぬいぐるみをぎゅっと抱いて、優しい時間をすごしてね♡  

☕ラッキー行動：あったかい紅茶を飲むこと""",
    "雨": """☔ 雨の日は、カエルがすこしさみしい日…🐸  
窓の外の雨音に耳をすませて、ゆっくり深呼吸してみよう  

🧺ラッキーアイテム：ふわふわのタオル""",
    "雪": """❄ 雪の日は、シロクマがまったりする日！🐻‍❄️  
毛布にくるまって、ホットココアでぬくぬくしよう♡  

🧸ラッキー行動：好きなぬいと一緒にお昼寝""",
    "風": """💨 風の強い日は、いぬがそわそわしちゃう日！🐶  
安心できる場所で、好きな音楽を聞いてみてね♪  

🎧ラッキーアイテム：お気に入りのタオルケット""",
    "雷": """⚡ 雷の日は、ハムスターがちょっとびくびくする日…🐹  
でも、毛布の中に隠れてると安心できるよ♡  

🧸ラッキー行動：お気に入りのぬいぐるみを抱っこする"""
}

# ------------------------------
# ★ 画像アップロード関数（MIMEタイプを明示）
# ------------------------------
def upload_image(client, image_path, max_size_kb=976):
    try:
        img = Image.open(image_path)
        print(f"📸 画像読み込み: {image_path}, 形式={img.format}, サイズ={img.size}, モード={img.mode}")

        # 強制リサイズ（デカすぎる画像は縮小）
        max_dimension = 1024
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            print(f"🔄 リサイズ: 新サイズ={new_size}")

        # 透過画像だったらJPEGにする
        force_jpeg = img.mode in ["RGBA", "LA"]
        format = "JPEG" if force_jpeg or img.format != "PNG" else "PNG"
        print(f"🖼️ 出力形式: {format}")

        buffer = io.BytesIO()
        quality = 95
        max_attempts = 10  # ループ上限
        attempt = 0

        while attempt < max_attempts:
            buffer.seek(0)
            buffer.truncate(0)

            if format == "JPEG":
                img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
            else:
                img.convert("P", palette=Image.ADAPTIVE, colors=256).save(buffer, format="PNG", optimize=True)

            size_kb = buffer.tell() / 1024
            print(f"📏 試行{attempt + 1}: サイズ={size_kb:.2f}KB, 品質={quality}")

            if size_kb <= max_size_kb or quality <= 20:
                break

            quality -= 5
            attempt += 1

        if size_kb > max_size_kb:
            print(f"⚠️ 警告: サイズが{size_kb:.2f}KBで{max_size_kb}KBを超えてます")

        buffer.seek(0)
        img_data = buffer.read()
        response = client.com.atproto.repo.upload_blob(img_data)
        print(f"✅ 画像アップロード成功: MIMEタイプ={response.blob.mime_type}, サイズ={size_kb:.2f}KB")
        return response.blob

    except Exception as e:
        print(f"❌ 画像アップロードエラー: {e}")
        raise

# ------------------------------
# ★ 投稿処理（画像付き！）
# ------------------------------
def post_weather_with_image(image_path: str):
    client = Client()
    try:
        client.login(HANDLE, APP_PASSWORD)
        print("✅ Blueskyログイン成功！")
    except Exception as e:
        print(f"❌ Blueskyログイン失敗: {e}")
        return

    weather = get_weather()
    print(f"🌦️ 取得した天気: {weather}")
    message = WEATHER_TEMPLATES.get(weather, WEATHER_TEMPLATES["くもり"])
    print(f"📝 投稿メッセージ: {message}")

    try:
        # 画像をアップロード
        image_blob = upload_image(client, image_path)
        embed = models.AppBskyEmbedImages.Main(images=[
            models.AppBskyEmbedImages.Image(
                alt=f"{weather}のイラスト",
                image=image_blob
            )
        ])

        # 投稿
        client.send_post(text=message, embed=embed)
        print("✅ 投稿しました！")

    except Exception as e:
        print(f"⚠️ 投稿失敗: {e}")
        traceback.print_exc()

# ------------------------------
# ★ 実行（ここに画像ファイル名を書く）
# ------------------------------
if __name__ == "__main__":
    print("🤖 天気占いBot 起動中…")
    post_weather_with_image("images/IMG_5849.png")  # ←ファイル名を差し替えてね！