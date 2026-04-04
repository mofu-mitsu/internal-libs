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
# ★ 画像アップロード (画像がなくてもエラーにしない)
# ------------------------------
def upload_image(client, image_path):
    # パスが空、またはファイルが存在しない場合はNoneを返す
    if not image_path or not os.path.exists(image_path):
        print(f"【お知らせ】画像が見つからないため、テキストのみで投稿します: {image_path}")
        return None
    
    try:
        img = Image.open(image_path)
        max_dimension = 1280 
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buffer = io.BytesIO()
        quality = 90
        # 全ての画像をJPG形式に変換して最適化（JPG対応の核心！）
        while True:
            buffer.seek(0)
            buffer.truncate(0)
            img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
            if buffer.tell() / 1024 <= 976 or quality <= 20:
                break
            quality -= 5
        buffer.seek(0)
        return client.com.atproto.repo.upload_blob(buffer.read()).blob
    except Exception as e:
        print(f"【警告】画像処理中にエラーが発生しました。テキストのみで投稿を続行します: {e}")
        return None

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
    # JSON読み込み
    with open('daily.json', 'r', encoding='utf-8') as f:
        posts = json.load(f)

    post = random.choice(posts)
    
    # タイトル付きメッセージ作成
    raw_message = f"""🎀 みりんてゃの放課後日記

{post['text']}"""
    
    message = normalize_text(raw_message)

    # ログイン
    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    # 画像パスがJSONにあるかチェック（なければNoneを渡す）
    image_path = post.get('image', None)
    image_blob = upload_image(client, image_path)
    
    embed = None
    if image_blob:
        embed = {
            "$type": "app.bsky.embed.images",
            "images": [{"image": image_blob, "alt": "みりんてゃの日常写真"}]
        }

    # 投稿
    facets = generate_facets_from_text(message)
    client.send_post(text=message, facets=facets if facets else None, embed=embed)
    print("放課後日記の投稿に成功しました！")

if __name__ == "__main__":
    main()
