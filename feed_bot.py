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

# 🔧 get_strong_ref を投稿用にちゃんと動くよう調整
def get_strong_ref_from_post(post_obj):
    return {
        "$type": "com.atproto.repo.strongRef",
        "uri": post_obj.uri,
        "cid": post_obj.cid,
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
def save_replied_uris(uris):
    with open("replied_uris.txt", "w") as f:
        for uri in uris:
            f.write(uri + "\n")

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
    
# 保存済みURIを読み込む関数
def load_replied_uris():
    if not os.path.exists(REPLIED_FILE):
        return set()
    with open(REPLIED_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))
        
# 投稿を確認して返信する関数
def run_once():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    print("📨 投稿を確認中…")
    replied_uris = load_replied_uris()
    print(f"📄 保存済みURI読み込み完了 → 件数: {len(replied_uris)}")
    print(f"🔍 一部サンプル: {list(replied_uris)[:5]}")

    # 投稿IDだけで重複チェックするためのセットも作る
    replied_post_ids = set(uri.split('/')[-1] for uri in replied_uris)
    replied_texts = set()  # ←ここ！

    # タイムラインから最新20件を取得
    timeline = client.app.bsky.feed.get_timeline(params={"limit": 20})
    feed = timeline.feed

    for post in feed:
        text = getattr(post.post.record, "text", None)
        uri = str(post.post.uri)
        post_id = uri.split('/')[-1]  # ← 投稿IDだけ取り出す

        print(f"📝 処理対象URI: {uri}")
        print(f"📂 保存済みURIsの一部: {list(replied_uris)[-5:]}")
        print(f"🆔 投稿ID: {post_id}")

        author = post.post.author.handle

    if author == HANDLE or post_id in replied_post_ids or not text or text in replied_texts:
        if post_id in replied_post_ids:
            print(f"⏩ スキップ（既にリプ済み）→ @{author}: {text}")
            print(f"    🔁 スキップ理由：ID一致 → {post_id}")
        elif author == HANDLE:
            print(f"⏩ スキップ（自分の投稿）→ @{author}: {text}")
        elif not text:
            print(f"⏩ スキップ（テキストなし）→ @{author}")
        elif text in replied_texts:
            print(f"⏩ スキップ（同じテキスト）→ @{author}: {text}")
            continue

        print(f"👀 チェック中 → @{author}: {text}")

        matched = False
        reply_text = ""

        # 🔍 キーワードマッチ判定
        for keyword, response in KEYWORD_RESPONSES.items():
            if keyword in text:
                reply_text = response
                matched = True
                print(f"✨ キーワード「{keyword}」にマッチ！")
                break

        # 🔁 メンションに反応（AI生成）
        if not matched and f"@{HANDLE}" in text:
            prompt = f"みりんてゃは地雷系ENFPで、甘えん坊でちょっと病みかわな子。フォロワーが「{text}」って投稿したら、どう返す？\nみりんてゃ「"
            reply_text = generate_reply(prompt)
            print(f"🤖 AI返信生成: {reply_text}")
            matched = True

        if not matched:
            print("🚫 スキップ: 条件に合わない投稿")
            continue

        # 🔖 ハッシュタグとfacetsの生成
        hashtags = [word for word in text.split() if word.startswith("#")]
        facets = generate_facets_from_text(reply_text, hashtags)

        # 🔁 リプライ参照情報の作成
        reply_ref = AppBskyFeedPost.ReplyRef(
            root=get_strong_ref_from_post(post.post),
            parent=get_strong_ref_from_post(post.post)
        )

        # ✉️ 投稿送信（成功したら保存）
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
        except Exception as e:
            print(f"⚠️ 返信エラー: {e}")
        else:
            replied_uris.add(uri)
            save_replied_uris(replied_uris)
            replied_texts.add(text)  # ←ここ追加！
            print(f"✅ 返信しました → @{author}")
            print(f"📁 保存されたURI一覧（最新20件）: {list(replied_uris)[-20:]}")
            print(f"🗂 現在の保存数: {len(replied_uris)} 件")

# 🔧 エントリーポイント
if __name__ == "__main__":
    run_once()