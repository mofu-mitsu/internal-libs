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


def resolve_image_path(image_path):
    """画像パスを解決する。

    character.json に書かれたパスを最優先し、見つからない場合は
    ファイル名だけを取り出して images/characters/ と images/ も探す。
    """
    if not image_path:
        return None

    path = Path(image_path)
    candidates = [
        path,
        Path('images/characters') / path.name,
        Path('images') / path.name,
    ]

    # 重複を避けつつ、最初に存在するものを返す
    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return str(candidate)

    return None


def upload_image(client, image_path, character_name):
    """画像をアップロードする。画像がなければ例外で処理を停止する。"""
    resolved_path = resolve_image_path(image_path)

    if not resolved_path:
        raise FileNotFoundError(
            f"画像が見つかりません: {character_name}\n"
            f"指定されたパス: {image_path}\n"
            f"確認した場所: 指定パス / images/characters/ / images/"
        )

    print(f"画像を使用します: {resolved_path}")

    try:
        img = Image.open(resolved_path)
        img = img.convert("RGB")  # JPG用に変換
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
        raise RuntimeError(f"画像処理・アップロードエラー ({character_name}): {e}") from e


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

    # nameとshortがあるデータだけを抽出（エラー回避！）
    characters = [c for c in all_data if isinstance(c, dict) and 'name' in c and 'short' in c]

    if not characters:
        raise RuntimeError("有効なキャラクターデータが見つかりませんでした。")

    char = random.choice(characters)

    name = char.get('name', '不明なキャラ')
    short = char.get('short', 'なし')
    cls = char.get('class', 'とりの丘学園')
    motif = char.get('motif', '不明')
    desc = char.get('desc', '（紹介文準備中）')
    image_path = char.get('image')

    # 画像がない投稿は絶対に行わない。
    # loginや投稿処理より前にチェックしておくことで、Actionsも失敗扱いになる。
    if not image_path:
        raise FileNotFoundError(
            f"{name} の画像パスが character.json にありません。"
        )

    if not resolve_image_path(image_path):
        raise FileNotFoundError(
            f"{name} の画像ファイルが見つかりません。\n"
            f"character.json の指定: {image_path}\n"
            f"指定パス、images/characters/、images/ を確認しました。"
        )

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

    image_blob = upload_image(client, image_path, name)

    embed = {
        "$type": "app.bsky.embed.images",
        "images": [{"image": image_blob, "alt": f"{name}のイラスト"}]
    }

    facets = generate_facets_from_text(message)
    client.send_post(text=message, facets=facets if facets else None, embed=embed)
    print(f"投稿成功: {name}")


if __name__ == "__main__":
    main()
