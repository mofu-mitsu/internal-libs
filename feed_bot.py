# 🔽 📦 Pythonの標準ライブラリ
from datetime import datetime, timezone
import os
import json
import requests

# 🔽 🌱 外部ライブラリ
from dotenv import load_dotenv

# 🔽 📡 atproto関連
from atproto import Client, models
from atproto_client.models import AppBskyFeedPost

# 🔧 get_strong_refを自作で定義（もうimportしなくてOK！）
def get_strong_ref(record):
    return {
        "$type": "com.atproto.repo.strongRef",
        "uri": record.uri,
        "cid": record.cid,
    }

# .envファイルを読み込む
load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HANDLE = os.environ['HANDLE']
APP_PASSWORD = os.environ['APP_PASSWORD']
REPLIED_FILE = "replied_uris.json"

client = Client()
client.login(HANDLE, APP_PASSWORD)

# リプライ済みURIをファイルから読み込む
def load_replied_uris():
    if os.path.exists(REPLIED_FILE):
        with open(REPLIED_FILE, "r") as f:
            return set(json.load(f))
    return set()

# リプライ済みURIを保存
def save_replied_uris(replied_uris):
    with open(REPLIED_FILE, "w") as f:
        json.dump(list(replied_uris), f)

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
        if isinstance(result, list) and result[0]["generated_text"]:
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
from atproto_client.models import AppBskyRichtextFacet
def generate_facets_from_text(text, hashtags):
    facets = []
    for tag in hashtags:
        if tag not in text:
            continue
        byte_start = text.encode("utf-8").find(tag.encode("utf-8"))
        byte_end = byte_start + len(tag.encode("utf-8"))
        if byte_start == -1:
            continue

        facet = AppBskyRichtextFacet.Facet(
            index=AppBskyRichtextFacet.ByteSlice(
                byte_start=byte_start,
                byte_end=byte_end
            ),
            features=[AppBskyRichtextFacet.Tag(tag=tag.replace("#", ""))]
        )
        facets.append(facet)
    return facets

# 投稿を確認して返信する関数
def run_once():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    print("📨 投稿を確認中…")
    replied_uris = load_replied_uris()

    timeline = client.app.bsky.feed.get_timeline(params={"limit": 20})
    feed = timeline.feed

    for post in feed:
        text = getattr(post.post.record, "text", None)
        uri = post.post.uri
        cid = post.post.cid
        author = post.post.author.handle

        if author == HANDLE or uri in replied_uris or not text:
            continue

        print(f"👀 チェック中 → @{author}: {text}")

        matched = False
        reply_text = ""

        # キーワードマッチ
        for keyword, response in KEYWORD_RESPONSES.items():
            if keyword in text:
                reply_text = response
                matched = True
                print(f"✨ キーワード「{keyword}」にマッチ！")
                break

        # メンションされた場合
        if not matched and f"@{HANDLE}" in text:
            prompt = f"みりんてゃは地雷系ENFPで、甘えん坊でちょっと病みかわな子。フォロワーが「{text}」って投稿したら、どう返す？\nみりんてゃ「"
            reply_text = generate_reply(prompt)
            print(f"🤖 AI返信生成: {reply_text}")
            matched = True

        if not matched:
            print("🚫 スキップ: 条件に合わない投稿")
            continue

        # 🔽 ハッシュタグ抽出と facets 生成（ここ大事！）
        hashtags = [word for word in text.split() if word.startswith("#")]
        facets = generate_facets_from_text(reply_text, hashtags)

        # 🔽 リプライ参照を生成（重要！）
        reply_ref = AppBskyFeedPost.ReplyRef(
            root=get_strong_ref(post),
            parent=get_strong_ref(post)
        )

        try:
            client.app.bsky.feed.post.create(
                record=AppBskyFeedPost.Record(
                    text=reply_text,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    reply=reply_ref,
                    facets=facets if facets else None
                ),
                repo=client.me.did
            )

            # 🔽 投稿送信（リプライとして送る！）
            client.app.bsky.feed.post.create(
                record=AppBskyFeedPost.Record(
                    text=reply_text,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    reply=reply_ref,
                    facets=facets if facets else None
                ),
                repo=client.me.did
            )
        except Exception as e:
            print(f"⚠️ 返信エラー: {e}")
        else:
            replied_uris.add(uri)
            save_replied_uris(replied_uris)
            print(f"✅ 返信しました → @{author}")
            
# 🔧 エントリーポイント
if __name__ == "__main__":
    run_once()
