from atproto import Client
import random
import os
from dotenv import load_dotenv
from pathlib import Path
import unicodedata
import re

# 環境変数読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

HANDLE = os.getenv('HANDLE')
APP_PASSWORD = os.getenv('APP_PASSWORD')

POST_MESSAGES = [
    """寂しくてしんじゃいそう……なんちゃって♡ 
#誰かに見つけてほしい""",
    """あなたのオリキャラ、もっと輝かせよ？
アイコン付きでかわいく紹介できるよ〜！

https://mofu-mitsu.github.io/orikyara-profile-maker/

#オリキャラ #創作クラスタ""",
]

# facets生成（絵文字対応＆バイト位置対応）
def generate_facets_from_text(text, hashtags):
    text_bytes = text.encode("utf-8")
    facets = []
    for tag in hashtags:
        tag_bytes = tag.encode("utf-8")
        start = text_bytes.find(tag_bytes)
        if start != -1:
            facets.append({
                "index": {
                    "byteStart": start,
                    "byteEnd": start + len(tag_bytes)
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#tag",
                    "tag": tag.lstrip("#")
                }]
            })
    # URL facets
    url_pattern = r'(https?://[^\s]+)'
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        start = text_bytes.find(url.encode("utf-8"))
        if start != -1:
            facets.append({
                "index": {
                    "byteStart": start,
                    "byteEnd": start + len(url.encode("utf-8"))
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": url
                }]
            })

    return facets

# 文字正規化
def normalize_text(text):
    return unicodedata.normalize("NFKC", text).strip()

# 投稿処理
client = Client()
client.login(HANDLE, APP_PASSWORD)

raw_message = random.choice(POST_MESSAGES)
message = normalize_text(raw_message)
hashtags = [word for word in message.split() if word.startswith("#")]
facets = generate_facets_from_text(message, hashtags)

client.send_post(
    text=message,
    facets=facets if facets else None
)