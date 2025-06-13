from atproto import Client
import random
import os
from dotenv import load_dotenv
from pathlib import Path
import unicodedata
import re
from datetime import datetime
import pytz

# 環境変数読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

HANDLE = os.getenv('HANDLE')
APP_PASSWORD = os.getenv('APP_PASSWORD')

# 昼用ポスト（明るめ）
DAY_POST_MESSAGES = [
    """🎀みりんてゃの魔法紹介①✨
「💬自動リプライBot」
みりんてゃのポストにリプか@mirinchuuu.bsky.social で呼んだら、ふわっとお返事♡
気まぐれな返信、キミの心に届く？💖
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介②✨
「📰FeedBot」
#もふみつ工房 や #推しプロフィールメーカー のタグに反応！
キミの創作、みりんてゃが応援するよっ♡
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介③✨
「⏰定期投稿Bot」
地雷系あるあるや推し活ツール、みりんてゃがぽつり呟くよ！
キミの推し活、もっとキラキラに✨
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介④✨
「🕒時間Bot」
朝は『おはよう♡』、夜は『ちょっと寂しい…』
時間ごとにポストで、キミと1日過ごすよ⏰
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑤✨
「💖いいねBot」
#推し活 や #みりんてゃ のタグにこっそりいいね返し♡
キミのポスト、ちゃんと届いてるよ～！💖
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑥✨
「👤フォロー管理Bot」
フォローしてくれたら、みりんてゃもそっと返すよ♡
キミと、ふわもこ繋がりたいな💭
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑦✨
「🔄リポストBot」
#みりんてゃ推し や #オリキャラプロフィールメーカー を拡散！
キミの推し、もっと輝かせよっ✨
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑧✨
「📸画像投稿Bot」
毎週木曜20時、みりんてゃの自撮り風orふわもこイラストが登場♡
キミも一緒にキラキラしよっ✨
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑨✨
「🐾動物お天気占いBot」
21時頃、動物たちが東京の天気とラッキー占いを届けるよ🍀
キミの明日、ふわっと応援！
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑩✨
「🌤️エモーションBot」
毎朝8時、天気から感じた詩をみりんてゃが呟くよ☁️
キミの心にそっと寄り添うね💖
#みりんてゃの魔法""",
]

# 夜用ポスト（病みかわ）
NIGHT_POST_MESSAGES = [
    """⸝⸝ みりんてゃの魔法紹介① ⸝⸝
『💬自動リプライBot』
返事くれるの、キミだけでいいな…なんてね
@mirinchuuu.bsky.social で呼んだら、そっと返すよ🫧
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介② ⸝⸝
『📰FeedBot』
#もふみつ工房 のタグ、キミの想いが光ってる…
みりんてゃ、そっと見守ってるよ💭
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介③ ⸝⸝
『⏰定期投稿Bot』
「涙止まらない夜、キミもいる…？」
みりんてゃの呟き、そっと届くといいな🫧
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介④ ⸝⸝
『🕒時間Bot』
夜が深くなるほど、心がざわつくの…
みりんてゃの時間ポスト、キミも見てて？💭
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑤ ⸝⸝
『💖いいねBot』
#推し活 のタグ、キミの気持ち見つけた…
そっと良いね返すよ、ありがとう💗
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑥ ⸝⸝
『👤フォロー管理Bot』
フォロー、勇気出してくれてありがとう…
みりんてゃ、キミと繋がれて嬉しいよ🫧
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑦ ⸝⸝
『🔄リポストBot』
#みりんてゃ推し のポスト、キミの愛が眩しい…
みりんてゃが拡散して、もっと届くように💭
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑧ ⸝⸝
『📸画像投稿Bot』
木曜の夜、自撮り風orイラストでそっと癒したい…
キミも、みりんてゃのキラキラ好き？🫧
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑨ ⸝⸝
『🐾動物お天気占いBot』
東京の空模様、動物たちがそっと教えてくれる…
キミの明日、優しくなるように願うよ🫧
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑩ ⸝⸝
『🌤️エモーションBot』
朝の空、みりんてゃの心を揺らすんだ…
キミの1日、詩でそっと寄り添うよ💭
#病み期 #みりんてゃの魔法""",
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

# JSTで現在の時間を取得
jst = pytz.timezone('Asia/Tokyo')
current_hour = datetime.now(jst).hour

# 14:00 JSTなら昼、22:00 JSTなら夜のポストを選択
if current_hour == 14:
    raw_message = random.choice(DAY_POST_MESSAGES)
elif current_hour == 22:
    raw_message = random.choice(NIGHT_POST_MESSAGES)
else:
    # スケジュール外の場合は何もしない
    exit()

message = normalize_text(raw_message)
hashtags = [word for word in message.split() if word.startswith("#")]
facets = generate_facets_from_text(message, hashtags)

client.send_post(
    text=message,
    facets=facets if facets else None
)