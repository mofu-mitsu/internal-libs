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

load_dotenv()

HANDLE = os.getenv('HANDLE')
APP_PASSWORD = os.getenv('APP_PASSWORD')

def upload_image(client, image_path):
    if not image_path or not os.path.exists(image_path):
        print(f"画像なしで進行します: {image_path}")
        return None
    try:
        img = Image.open(image_path)
        img = img.convert("RGB") # JPG用に変換
        max_dimension = 1024
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)
        return client.com.atproto.repo.upload_blob(buffer.read()).blob
    except Exception as e:
        print(f"画像処理エラー: {e}")
        return None

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

def main():
    with open('character.json', 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    
    # ★ nameとshortがあるデータだけを抽出（エラー回避！）
    characters = [c for c in all_data if isinstance(c, dict) and 'name' in c and 'short' in c]

    if not characters:
        print("有効なキャラクターデータが見つかりませんでした。")
        return

    char = random.choice(characters)

    # 念のためキーがあるか確認しながらメッセージ作成
    name = char.get('name', '不明なキャラ')
    short = char.get('short', 'なし')
    cls = char.get('class', 'とりの丘学園')
    motif = char.get('motif', '不明')
    desc = char.get('desc', '（紹介文準備中）')

    raw_message = f"""📖【みりんてゃの学園 キャラ紹介】
〜とりの丘学園の仲間たち〜

【{name}（{short}）】
{cls}
モチーフ：{motif}

{desc}

#みりんてゃ図鑑"""
    
    message = unicodedata.normalize("NFKC", raw_message).strip()

    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    image_blob = upload_image(client, char.get('image'))
    
    embed = None
    if image_blob:
        embed = {
            "$type": "app.bsky.embed.images",
            "images": [{"image": image_blob, "alt": f"{name}のイラスト"}]
        }

    facets = generate_facets_from_text(message)
    client.send_post(text=message, facets=facets if facets else None, embed=embed)
    print(f"投稿成功: {name}")

if __name__ == "__main__":
    main()
