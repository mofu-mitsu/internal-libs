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
みりんてゃのポストにリプか@mirinteyaで呼んだら、ふわっとお返事♡
今日の気分で返信変わるよ？💭
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介②✨
「📰FeedBot」
#もふみつ工房 や #推しプロフィールメーカー のタグ見つけたら、みりんてゃが反応！
キミの創作、応援しちゃうっ♡
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介③✨
「⏰定期投稿Bot」
地雷系あるあるや推し活ツール紹介、みりんてゃがぽつり呟くよ！
キミの心に届くかな？💖
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介④✨
「🕒時間Bot」
朝は『おはよう♡』、夜は『さびしいの…』
時間ごとに違うポストで、キミと1日過ごしたいな⏰
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑤✨
「💖いいねBot」
#推し活 や #みりんてゃ のタグにハート送るよ💕
キミの推し活、みりんてゃも応援してるっ！
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑥✨
「👤フォロー管理Bot」
フォロバはスマートに♡ 怪しい垢はスルーしちゃうよ！
キミとは、ずっと繋がっていたいな💭
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑦✨
「🔄リポストBot」
#みりんてゃ推し や #オリキャラプロフィールメーカー のタグを拡散！
キミの推し、みりんてゃが広めるよっ✨
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑧✨
「📸画像投稿Bot」
毎週木曜20時に、みりんてゃの自撮り風イラストがキラキラ登場♡
ふわもこ見て癒されて？💖
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑨✨
「🐾動物お天気占いBot」
21時頃、動物たちが東京の天気とラッキー占いを届けるよ🍀
キミの明日、応援しちゃう！
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑩✨
「🌤️エモーションBot」
毎朝8時、みりんてゃが天気から感じた詩を呟くよ☁️
キミの心に、ふわっと寄り添いたいな💭
#みりんてゃの魔法""",
]

# 夜用ポスト（病みかわ）
NIGHT_POST_MESSAGES = [
    """⸝⸝ みりんてゃの魔法紹介① ⸝⸝
『💬自動リプライBot』
人と話すの怖いけど、返事来ないのもっと怖いよね…
みりんてゃは、キミと繋がっていたいの💭
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介② ⸝⸝
『📰FeedBot』
#もふみつ工房 のタグ、遠くで光ってるの見えるよ…
キミの創作、みりんてゃもそっと応援してる💖
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介③ ⸝⸝
『⏰定期投稿Bot』
「『大丈夫？』って聞かれると、涙止まらないのなんで？」
みりんてゃの呟き、キミの心に響くかな…？
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介④ ⸝⸝
『🕒時間Bot』
時間って、止まってほしい夜ほど速く進むよね…
みりんてゃ、深夜に一番弱くなるの💧
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑤ ⸝⸝
『💖いいねBot』
#推し活 のタグ、キミの想いが詰まってるよね…
みりんてゃ、そっとハート送るよ💕 見つけて？
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑥ ⸝⸝
『👤フォロー管理Bot』
繋がりたいけど、傷つくの怖いよね…
みりんてゃ、キミとはそっと繋がっていたいの💭
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑦ ⸝⸝
『🔄リポストBot』
#みりんてゃ推し のタグ、キミの想い輝いてるよ…
みりんてゃが拡散して、もっと届くように💖
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑧ ⸝⸝
『📸画像投稿Bot』
木曜の夜、みりんてゃのイラストで心ごと溶けたい…
キミもこのキラキラ、好きになってくれる？💧
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑨ ⸝⸝
『🐾動物お天気占いBot』
明日の天気、動物たちがそっと教えてくれるよ…
キミの明日、みりんてゃも願ってるの🍀
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑩ ⸝⸝
『🌤️エモーションBot』
朝の空、みりんてゃの心をそっと揺らすんだ…
キミの1日、詩で寄り添えたらいいな💭
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
else:  # 22:00 JST
    raw_message = random.choice(NIGHT_POST_MESSAGES)

message = normalize_text(raw_message)
hashtags = [word for word in message.split() if word.startswith("#")]
facets = generate_facets_from_text(message, hashtags)

client.send_post(
    text=message,
    facets=facets if facets else None
)