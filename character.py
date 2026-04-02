# -*- coding: utf-8 -*-
from atproto import Client
import os
import json
import re
import io
import unicodedata
from datetime import datetime
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
    max_dimension = 1024
    if max(img.size) > max_dimension:
        ratio = max_dimension / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    buffer = io.BytesIO()
    quality = 95
    while True:
        buffer.seek(0)
        buffer.truncate(0)
        img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
        # 1MB(976KB)制限対策
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
    
    # ハッシュタグ検出
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
    with open('character.json', 'r', encoding='utf-8') as f:
        characters = json.load(f)

    # 投稿するキャラを決定（日付ベースで順番に）
    day_of_year = datetime.now().timetuple().tm_yday
    char_index = day_of_year % len(characters)
    char = characters[char_index]

    # メッセージ作成（チャッピーおすすめ構成）
    raw_message = f"""【{char['name']}（{char['short']}）】
{char['class']}

モチーフ：{char['motif']}

{char['desc']}

#みりんてゃ図鑑"""
    
    message = normalize_text(raw_message)

    # ログイン
    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    # 画像アップロード
    image_blob = upload_image(client, char['image'])
    
    embed = None
    if image_blob:
        embed = {
            "$type": "app.bsky.embed.images",
            "images": [{"image": image_blob, "alt": f"{char['name']}のイラスト"}]
        }

    # 投稿
    facets = generate_facets_from_text(message)
    client.send_post(text=message, facets=facets if facets else None, embed=embed)
    print(f"投稿完了: {char['name']}")

if __name__ == "__main__":
    main()
