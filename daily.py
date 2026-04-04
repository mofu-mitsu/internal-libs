# -*- coding: utf-8 -*-
from atproto import Client
import os
import json
import random
import re
import io
import unicodedata
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image

# 環境変数読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

HANDLE = os.getenv('HANDLE')
APP_PASSWORD = os.getenv('APP_PASSWORD')

# ------------------------------
# ★ 画像アップロード (圧縮対応)
# ------------------------------
def upload_image(client, image_path):
    if not os.path.exists(image_path):
        print(f"画像が見つかりません: {image_path}")
        return None
    
    img = Image.open(image_path)
    max_dimension = 1280 
    if max(img.size) > max_dimension:
        ratio = max_dimension / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    buffer = io.BytesIO()
    quality = 90
    while True:
        buffer.seek(0)
        buffer.truncate(0)
        img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
        if buffer.tell() / 1024 <= 976 or quality <= 20:
            break
        quality -= 5
    buffer.seek(0)
    return client.com.atproto.repo.upload_blob(buffer.read()).blob

# ------------------------------
# ★ facets & 正規化
# ------------------------------
def generate_facets_from_text(text):
    text_bytes = text.encode("utf-8")
    facets = []
    hashtag_pattern = r'#([^\s#]+)'
    for match in re.finditer(hashtag_pattern, text):
        tag = match.group(0)
        tag_bytes = tag.encode("utf-8")
        start = text_bytes.find(tag_bytes)
        if start != -1:
            facets.append({
                "index": {"byteStart": start, "byteEnd": start + len(tag_bytes)},
                "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": tag.lstrip("#")}]
            })
    return facets

def normalize_text(text):
    return unicodedata.normalize("NFKC", text).strip()

# ------------------------------
# ★ メイン処理
# ------------------------------
def main():
    with open('daily.json', 'r', encoding='utf-8') as f:
        posts = json.load(f)

    post = random.choice(posts)
    
    # ★ 日記用のタイトルを追加して組み立て！
    raw_message = f"""🎀 みりんてゃの放課後日記

{post['text']}"""
    
    message = normalize_text(raw_message)

    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    image_blob = upload_image(client, post['image'])
    
    embed = None
    if image_blob:
        embed = {
            "$type": "app.bsky.embed.images",
            "images": [{"image": image_blob, "alt": "みりんてゃの日常写真"}]
        }

    facets = generate_facets_from_text(message)
    client.send_post(text=message, facets=facets if facets else None, embed=embed)
    print("日記投稿完了！")

if __name__ == "__main__":
    main()
