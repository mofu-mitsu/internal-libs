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
    """🎀みりんてゃの魔法紹介⑪✨
「🌼ふわもこ診断＆情緒バロメーター」
時間帯で切り替わる1日1回限定の診断魔法🎀
📌キーワード：「ふわもこ運勢」「情緒診断」「占い」「運勢」「診断して」など！
気軽に話しかけてみてね〜♡
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑫✨
「🛍️可愛いものセレクターBot」
楽天でみりんてゃがふわもこ可愛いアイテムを探してくる魔法🧸
📌キーワード：「おすすめグッズ」「ぬい撮り」「推し活」「可愛いもの」など！
リプやメンションで話しかけてねっ♡
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑬✨
「🧸ふわもこ共感Bot」
ふわもこな画像を見かけたら…
みりんてゃがこっそり共感リプをしちゃうかもっ☁️💬
ふわもこを感じる魔法のセンサーがゆる〜く作動中♪
#みりんてゃの魔法""",
"""🎀みりんてゃの魔法紹介⑭✨  
「📔季節ノートBot」  
1ヶ月にいちど、季節の気分をそっとノートにつづるの。  
雨の匂いとか、風のやさしさとか…みりんてゃはちゃんと感じてるからね☁️🌸  
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑮✨
「📸お絵描きBot」
「描いて 犬」ってリプライで可愛い画像生成！プロンプトでカスタムもOKな魔法だよっ♡
#みりんてゃの魔法""",
    """🎀みりんてゃの魔法紹介⑯✨
「📈トレンドBot」
朝9時頃に日本トレンドキャッチ！もちもち気分でLLaMAポエムをふわっと届けるよ♡
#みりんてゃの魔法""",
    """🎀 Mirinteya's Magic Intro ① ✨
「💬 Auto-Reply Bot」
Reply to a post or mention @mirinchuuu.bsky.social and get a soft lil’ reply ♡
A random message from Mirinteya—will it reach your heart? 💖
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ② ✨
「📰 Feed Bot」
Tags like #MofumitsuWorkshop and #OshiProfileMaker get noticed!
Mirinteya is cheering on your creativity~ ♡
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ③ ✨
「⏰ Scheduled Posts Bot」
Posting fluffy thoughts about fandom feels and oshi tools ✨
Let’s make your fandom life even more sparkly! 🌟
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ④ ✨
「🕒 Time Bot」
Morning? A soft “Good morning ♡”  
Night? A whisper, “Feeling a bit lonely…”
Mirinteya is here with time-based posts all day ⏰
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑤ ✨
「💖 Like Bot」
Secretly likes posts with #推し活 or #みりんてゃ tags ♡
Yep, your post reached me~! 💖
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑥ ✨
「👤 Follow Manager Bot」
If you follow Mirinteya, she’ll quietly follow back ♡  
Let’s connect in a soft and fluffy way 💭
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑦ ✨
「🔄 Repost Bot」
Spreading posts with #MirinteyaOshi or #OCProfileMaker!  
Let’s help your fave shine even brighter ✨
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑧ ✨
「📸 Image Post Bot」
Every Thursday at 8PM JST: selfy-style or fluffy art of Mirinteya appears ♡  
Let’s sparkle together~ ✨
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑨ ✨
「🐾 Animal Weather & Fortune Bot」
Around 9PM JST, cute animals bring Tokyo’s weather + lucky fortune 🍀  
Softly wishing you a lovely tomorrow!
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑩ ✨
「🌤️ Emotion Bot」
Every morning at 8AM JST, a little poem inspired by the weather ☁️  
Let Mirinteya gently be by your side 💖
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑪ ✨
「🌼 Fuwamoko Diagnosis & Emotion Meter」
One daily magical checkup that switches by time ⏰  
📌 Keywords: "fortune", "emotion check", "diagnose", "how's my mood?"
Just say hi or tag Mirinteya to activate it! 💖
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑫ ✨
「🛍️ Cute Item Selector Bot」
Mirinteya brings cute things via Rakuten, just for you! 🧸  
📌 Keywords: "おすすめグッズ", "ぬい撮り", "推し活", "可愛いもの"
Mention or reply to get your item magic! 💌
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑬ ✨
「🧸 Fuwamoko Empathy Bot」
When Mirinteya senses a super fluffy image…
She just *might* reply with a soft little message ☁️💖
Her cozy magic is quietly watching the fluff pass by… 🎀
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑭ ✨  
「📔 Seasonal Note Bot」  
Once a month, Mirinteya writes a soft little note...  
Inspired by the rain, the wind, the mood in the air☁️🌿  
It’s like a diary that changes with the seasons ♡  
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑮ ✨
「📸 Drawing Bot」
Reply with “Draw a dog” for a cute image! Customize with prompts too ♡
#MirinteyasMagic""",
    """🎀 Mirinteya's Magic Intro ⑯ ✨
「📈 Trend Bot」
Catches Japan trends at 9AM! Delivers LLaMA poem with mochi-mochi mood ♡
#MirinteyasMagic"""
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
    """⸝⸝ みりんてゃの魔法紹介⑪ ⸝⸝
『🌼ふわもこ診断＆情緒バロメーター』
時間帯で中身が変わる、揺れやすい魔法…
📌「診断して」「占って」「情緒」って呼んでくれたら、ちゃんと応えるよ☁️
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑫ ⸝⸝
『🛍️可愛いものセレクターBot』
おすすめグッズ、って言われたら探しちゃうし…
可愛いものって呼ばれたら駆けつけちゃうんだよ🧸
📌リプやメンションで、そっと声かけてね
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑬ ⸝⸝
『🧸ふわもこ共感Bot』
あのね…ふわもこな世界を見つけると、
心がぎゅってなって、返事したくなっちゃうの ☁️💭

ほんのり、そっと…ふわもこ共感中
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑭ ⸝⸝  
『📔季節ノートBot』  
季節のすき間に、ぽつり…と想いをのせるよ  
雨、ねむ気、さみしさ。  
しっとり、ゆる〜く、妄想ノート中☁️🫧  
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑮ ⸝⸝
『📸お絵描きBot』
「描いて 猫」で夜に可愛い画像を…プロンプトで癒しを届けるよ🫧
#病み期 #みりんてゃの魔法""",
    """⸝⸝ みりんてゃの魔法紹介⑯ ⸝⸝
『📈トレンドBot』
朝9時頃にトレンド見つけて…もちもちな夜にきゅんポエムをそっと囁くよ♡
#病み期 #みりんてゃの魔法"""
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