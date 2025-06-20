# post_image.py

# ------------------------------
# ★ 必要なライブラリ（画像投稿用の魔法の道具！）
# ------------------------------
from atproto import Client
import random
import os
import json
from dotenv import load_dotenv
from pathlib import Path
import re
import unicodedata
import mimetypes
from PIL import Image
import io

# ------------------------------
# ★ 認証情報（.envに書くよ！）
# ------------------------------
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
HANDLE = os.getenv('HANDLE') or exit("❌ HANDLEが設定されていません")
APP_PASSWORD = os.getenv('APP_PASSWORD') or exit("❌ APP_PASSWORDが設定されていません")

# ------------------------------
# ★ 画像投稿用のデータ（post_images.jsonから読み込むよ！）
# 形式: [{"text": "投稿文", "image": "画像パス", "alt": "代替テキスト"}]
# ------------------------------
def load_image_posts():
    with open("messages/post_images.json", "r", encoding="utf-8") as f:
        return json.load(f)

IMAGE_POSTS = load_image_posts()

# ------------------------------
# ★ 画像アップロード処理（拡張子に応じてMIMEタイプも自動設定！）
# ------------------------------

def upload_image(client, image_path, max_size_kb=976):
    img = Image.open(image_path)

    # 強制リサイズ（デカすぎる画像は縮小）
    max_dimension = 1024
    if max(img.size) > max_dimension:
        ratio = max_dimension / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # 透過画像だったらJPEGにする
    force_jpeg = img.mode in ["RGBA", "LA"]
    format = "JPEG" if force_jpeg or img.format != "PNG" else "PNG"

    buffer = io.BytesIO()
    quality = 95

    while True:
        buffer.seek(0)
        buffer.truncate(0)

        if format == "JPEG":
            img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
        else:
            img.convert("P", palette=Image.ADAPTIVE, colors=256).save(buffer, format="PNG", optimize=True)

        size_kb = buffer.tell() / 1024
        if size_kb <= max_size_kb or quality <= 20:
            break
        quality -= 5

    buffer.seek(0)
    img_data = buffer.read()
    response = client.com.atproto.repo.upload_blob(img_data)
    return response.blob

# ------------------------------
# ★ facets生成（ハッシュタグやURLを正しく処理）
# ------------------------------
def generate_facets_from_text(text, hashtags):
    text_bytes = text.encode("utf-8")
    facets = []
    for tag in hashtags:
        tag_bytes = tag.encode("utf-8")
        start = text_bytes.find(tag_bytes)
        if start != -1:
            facets.append(
                {
                    "index": {
                        "byteStart": start,
                        "byteEnd": start + len(tag_bytes)
                    },
                    "features": [
                        {
                            "$type": "app.bsky.richtext.facet#tag",
                            "tag": tag.lstrip("#")
                        }
                    ]
                }
            )
    # URL facets
    url_pattern = r'(https?://[^\s]+)'
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        start = text_bytes.find(url.encode("utf-8"))
        if start != -1:
            facets.append(
                {
                    "index": {
                        "byteStart": start,
                        "byteEnd": start + len(url.encode("utf-8"))
                    },
                    "features": [
                        {
                            "$type": "app.bsky.richtext.facet#link",
                            "uri": url
                        }
                    ]
                }
            )
    return facets

# ------------------------------
# ★ 文字正規化（キレイなテキストにするよ！）
# ------------------------------
def normalize_text(text):
    return unicodedata.normalize("NFKC", text).strip()

# ------------------------------
# ★ 投稿処理（キャラBotがキラキラ画像投稿！）
# ------------------------------
client = Client()
client.login(HANDLE, APP_PASSWORD)

# 画像投稿データをランダムに選択
post_data = random.choice(IMAGE_POSTS)
message = normalize_text(post_data["text"])
image_path = post_data["image"] if "images/" in post_data["image"] else os.path.join("images", post_data["image"])
alt_text = post_data["alt"]

hashtags = [word for word in message.split() if word.startswith("#")]
facets = generate_facets_from_text(message, hashtags)

# 画像アップロード
image_blob = upload_image(client, image_path)

# 画像付き投稿
embed = {
    "$type": "app.bsky.embed.images",
    "images": [
        {
            "image": image_blob,
            "alt": alt_text
        }
    ]
}

client.send_post(
    text=message,
    facets=facets if facets else None,
    embed=embed
)