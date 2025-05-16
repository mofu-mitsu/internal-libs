from atproto import Client, models
import time
import requests
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()
HF_API_TOKEN = os.getenv(
    "HF_API_TOKEN")  # .envには HF_API_TOKEN=xxxxxxx の形で記載してね

# Blueskyアカウント情報
HANDLE = os.environ['HANDLE']
APP_PASSWORD = os.environ['APP_PASSWORD']


# Hugging Face APIで返信を生成する関数
def generate_reply(prompt):
    API_URL = "https://api-inference.huggingface.co/models/rinna/japanese-gpt2-small"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 100,
            "do_sample": True,
            "temperature": 0.8,
            "top_k": 50,
            "top_p": 0.95
        }
    }

    try:
        response = requests.post(API_URL,
                                 headers=headers,
                                 json=payload,
                                 timeout=10)
        result = response.json()
        if isinstance(result, list):
            return result[0]["generated_text"].split("みりんてゃ「")[-1].strip()
        else:
            return "えへへ、なんかうまく考えつかなかったかも〜…"
    except Exception as e:
        print("APIエラー:", e)
        return "ちょっとだけ、おやすみ中かも…また話してね♡"


# 特定のキーワードに反応する返答一覧
KEYWORD_RESPONSES = {
    "みりんてゃ": 'みりんてゃのこと呼んだ〜？♡もぉ〜っ！かまってくれて嬉しいに決まってるじゃん♡',
    "みりてゃ": "えっ、呼んだ〜！？みりてゃ参上っ♡ 今日も世界の中心でかわいいしてるよぉっ！",
    "みりんてゃー": "え〜ん、のばして呼ばれたら照れちゃうっ♡ 今日も一番かわいいって言ってぇ〜っ！",
    "みりんてゃちゃん": "てゃちゃん！？てゃちゃんって……かわいすぎる呼び方っ♡ 呼び続けてほしいの〜っ！",
    "もふみつ工房": "わぁっ、見てくれたの〜？♡ みりんてゃの本拠地、気に入ってもらえたらうれしすぎて鼻血でちゃうかもっ",
    "推しプロフィールメーカー": "それな〜っ！推しはプロフィールまで尊い♡ みりてゃの推しは……えへへ、ヒミツ♡",
    "オリキャラプロフィールメーカー": "オリキャラって…自分の分身でしょ？ うちの子語り、聞かせてよ〜♡ みりんてゃも聞きた〜い！",
    "ふわふわ相性診断": "ふたりの相性…ふわふわで、とけちゃいそうっ♡ 結果どうだった〜？教えて教えてっ！",
}


def start():
    print("監視を開始します…")
    replied_uris = set()

    while True:
        timeline = client.app.bsky.feed.get_timeline(params={"limit": 20})
        feed = timeline.feed

        for post in feed:
            text = post.post.record.text
            uri = post.post.uri
            cid = post.post.cid
            author = post.post.author.handle

            if author != HANDLE and uri not in replied_uris and f"@{HANDLE}" in text:
                matched = False
                for keyword, response in KEYWORD_RESPONSES.items():
                    if keyword in text:
                        print(f"キーワード検出: 「{keyword}」→ {text}")
                        reply_text = response
                        matched = True
                        break

                if not matched:
                    prompt = f"みりんてゃは地雷系ENFPで、甘えん坊でちょっと病みかわな子。フォロワーが「{text}」って投稿したら、どう返す？\nみりんてゃ「"
from atproto import Client, models
import time
import requests
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# Blueskyアカウント情報
HANDLE = os.environ['HANDLE']
APP_PASSWORD = os.environ['APP_PASSWORD']

# Hugging Face APIで返信を生成する関数
def generate_reply(prompt):
    API_URL = "https://api-inference.huggingface.co/models/rinna/japanese-gpt2-small"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 100,
            "do_sample": True,
            "temperature": 0.8,
            "top_k": 50,
            "top_p": 0.95
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        result = response.json()
        if isinstance(result, list):
            return result[0]["generated_text"].split("みりんてゃ「")[-1].strip()
        else:
            return "えへへ、なんかうまく考えつかなかったかも〜…"
    except Exception as e:
        print("APIエラー:", e)
        return "ちょっとだけ、おやすみ中かも…また話してね♡"

# 特定のキーワードに反応する返答一覧
KEYWORD_RESPONSES = {
    "みりんてゃ": 'みりんてゃのこと呼んだ〜？♡もぉ〜っ！かまってくれて嬉しいに決まってるじゃん♡',
    "みりてゃ": "えっ、呼んだ〜！？みりてゃ参上っ♡ 今日も世界の中心でかわいいしてるよぉっ！",
    "みりんてゃー": "え〜ん、のばして呼ばれたら照れちゃうっ♡ 今日も一番かわいいって言ってぇ〜っ！",
    "みりんてゃちゃん": "てゃちゃん！？てゃちゃんって……かわいすぎる呼び方っ♡ 呼び続けてほしいの〜っ！",
    "もふみつ工房": "わぁっ、見てくれたの〜？♡ みりんてゃの本拠地、気に入ってもらえたらうれしすぎて鼻血でちゃうかもっ",
    "推しプロフィールメーカー": "それな〜っ！推しはプロフィールまで尊い♡ みりてゃの推しは……えへへ、ヒミツ♡",
    "オリキャラプロフィールメーカー": "オリキャラって…自分の分身でしょ？ うちの子語り、聞かせてよ〜♡ みりんてゃも聞きた〜い！",
    "ふわふわ相性診断": "ふたりの相性…ふわふわで、とけちゃいそうっ♡ 結果どうだった〜？教えて教えてっ！",
}

# Facet（ハッシュタグなど）の位置を取得する関数
def generate_facets_from_text(text, hashtags):
    facets = []
    for tag in hashtags:
        if tag not in text:
            continue

        byte_start = text.encode("utf-8").find(tag.encode("utf-8"))
        byte_end = byte_start + len(tag.encode("utf-8"))

        if byte_start == -1:
            continue  # タグが見つからなかったらスキップ

        facet = models.AppBskyRichtextFacet.Main(
            index=models.AppBskyRichtextFacet.ByteSlice(
                byte_start=byte_start,
                byte_end=byte_end
            ),
            features=[models.AppBskyRichtextFacet.Tag(tag=tag.replace("#", ""))]
        )
        facets.append(facet)

    return facets

# メインのBot起動関数
def start():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    print("監視を開始します…")
    replied_uris = set()

    while True:
        timeline = client.app.bsky.feed.get_timeline(params={"limit": 20})
        feed = timeline.feed

        for post in feed:
            text = post.post.record.text
            uri = post.post.uri
            cid = post.post.cid
            author = post.post.author.handle

            if author != HANDLE and uri not in replied_uris and f"@{HANDLE}" in text:
                matched = False
                for keyword, response in KEYWORD_RESPONSES.items():
                    if keyword in text:
                        print(f"キーワード検出: 「{keyword}」→ {text}")
                        reply_text = response
                        matched = True
                        break

                if not matched:
                    prompt = f"みりんてゃは地雷系ENFPで、甘えん坊でちょっと病みかわな子。フォロワーが「{text}」って投稿したら、どう返す？\nみりんてゃ「"
                    reply_text = generate_reply(prompt)
                    print(f"AI返信: {reply_text}")

                # Facet自動生成（任意：ハッシュタグとかあれば）
                hashtags = [word for word in text.split() if word.startswith("#")]
                facets = generate_facets_from_text(reply_text, hashtags)

                client.send_post(
                    text=reply_text,
                    reply_to=models.create_reply_reference(uri=uri, cid=cid),
                    facets=facets if facets else None
                )

                replied_uris.add(uri)

        time.sleep(60)
        reply_text = generate_reply(prompt)
        print(f"AI返信: {reply_text}")

        client.send_post(text=reply_text,
                                 reply_to=models.create_reply_reference(
                                     uri=uri, cid=cid))
        replied_uris.add(uri)

        time.sleep(60)  # 1分ごとにチェック
