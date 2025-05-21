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
from atproto_client.exceptions import InvokeTimeoutError

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
GIST_TOKEN = os.environ["GIST_TOKEN"]

# Blueskyにログイン
client = Client()
client.login(HANDLE, APP_PASSWORD)

# Gist URL（直書き）
GIST_RAW_URL_URIS = "https://gist.githubusercontent.com/mofu-mitsu/c16e8c8c997186319763f0e03f3cff8b/raw/988fab2c442f9137d8f3ca5d7d254b0c18f71b0f/replied_uris.json"
GIST_ID_URIS = "c16e8c8c997186319763f0e03f3cff8b"

GIST_RAW_URL_TEXTS = "https://gist.githubusercontent.com/mofu-mitsu/a149431b226cf7b50ba057be4de7eae9/raw/94587c4feaf678c6d03d4c8dfc090302eda676ac/replied_texts.json"
GIST_ID_TEXTS = "a149431b226cf7b50ba057be4de7eae9"

# 🔹 replied_urisの読み書き
def load_replied_uris():
    print(f"🌐 Gistから読み込み中: {GIST_RAW_URL_URIS}")
    try:
        response = requests.get(GIST_RAW_URL_URIS)
        if response.status_code == 200:
            uris = json.loads(response.text)
            print(f"✅ 読み込んだreplied_uris: {uris[:5]}")
            return set(uris)
        else:
            print(f"⚠️ Gist読み込み失敗（uris）: {response.status_code}")
            return set()
    except Exception as e:
        print(f"⚠️ エラー（urisの読み込み）: {e}")
        return set()

def save_replied_uris(replied_uris):
    url = f"https://api.github.com/gists/{GIST_ID_URIS}"
    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "files": {
            "replied_uris.json": {
                "content": json.dumps(list(replied_uris), ensure_ascii=False, indent=2)
            }
        }
    }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print("💾 replied_uris.json に保存完了！")
    else:
        print("⚠️ replied_uris保存失敗:", response.status_code, response.text)

# 🔸 replied_textsの読み書き
def load_replied_texts():
    print(f"🌐 Gistから読み込み中: {GIST_RAW_URL_TEXTS}")
    try:
        response = requests.get(GIST_RAW_URL_TEXTS)
        if response.status_code == 200:
            texts = json.loads(response.text)
            print(f"✅ 読み込んだreplied_textsの一部: {list(texts.items())[:3]}")
            return texts
        else:
            print(f"⚠️ Gist読み込み失敗（texts）: {response.status_code}")
            return {}
    except Exception as e:
        print(f"⚠️ エラー（textsの読み込み）: {e}")
        return {}

def save_replied_texts(replied_texts):
    url = f"https://api.github.com/gists/{GIST_ID_TEXTS}"
    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "files": {
            "replied_texts.json": {
                "content": json.dumps(replied_texts, ensure_ascii=False, indent=2)
            }
        }
    }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print("💾 replied_texts.json に保存完了！")
    else:
        print("⚠️ replied_texts保存失敗:", response.status_code, response.text)

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
    "みりんてゃ": 'みりんてゃのこと呼んだ〜？？♡もぉ〜っ！かまってくれて嬉しいに決まってるじゃん♡',
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
    try:
        client = Client()
        client.login(HANDLE, APP_PASSWORD)

        print("📨 投稿を確認中…")
        replied_uris = load_replied_uris()
        replied_texts = set(load_replied_texts())

        print(f"📄 保存済みURI読み込み完了 → 件数: {len(replied_uris)}")
        print(f"🗂 保存済みテキスト読み込み完了 → 件数: {len(replied_texts)}")
        print(f"🔍 URIサンプル: {list(replied_uris)[:5]}")
        print(f"🔍 テキストサンプル: {list(replied_texts)[:5]}")

        replied_post_ids = set(uri.split('/')[-1] for uri in replied_uris)

        timeline = client.app.bsky.feed.get_timeline(params={"limit": 20})
        feed = timeline.feed

        for post in feed:
            text = getattr(post.post.record, "text", None)
            uri = str(post.post.uri)
            post_id = uri.split('/')[-1]

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

            for keyword, response in KEYWORD_RESPONSES.items():
                if keyword in text:
                    reply_text = response
                    matched = True
                    print(f"✨ キーワード「{keyword}」にマッチ！")
                    break

            if not matched and f"@{HANDLE}" in text:
                prompt = f"みりんてゃは地雷系ENFPで、甘えん坊でちょっと病みかわな子。フォロワーが「{text}」って投稿したら、どう返す？\nみりんてゃ「"
                reply_text = generate_reply(prompt)
                print(f"🤖 AI返信生成: {reply_text}")
                matched = True

            if not matched:
                print("🚫 スキップ: 条件に合わない投稿")
                continue

            hashtags = [word for word in text.split() if word.startswith("#")]
            facets = generate_facets_from_text(reply_text, hashtags)

            reply_ref = AppBskyFeedPost.ReplyRef(
                root=get_strong_ref_from_post(post.post),
                parent=get_strong_ref_from_post(post.post)
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
            except Exception as e:
                print(f"⚠️ 返信エラー: {e}")
            else:
                replied_uris.add(uri)
                replied_texts.add(text)
                print(f"✅ 返信しました → @{author}")
                print(f"📁 保存されたURI一覧（最新5件）: {list(replied_uris)[-5:]}")
                print(f"🗂 現在の保存数: {len(replied_uris)} 件")

        try:
            save_replied_uris(replied_uris)
            print(f"💾 URI保存成功 → 合計: {len(replied_uris)} 件")
            print(f"📁 最新URI一覧: {list(replied_uris)[-5:]}")

            save_replied_texts({t: True for t in replied_texts})
            print(f"💾 テキスト保存成功 → 合計: {len(replied_texts)} 件")
            print("📦 最新保存テキスト（抜粋）:")
            print(json.dumps(list(replied_texts)[-5:], ensure_ascii=False, indent=2))

        except Exception as e:
            print(f"❌ 保存失敗: {e}")

    except InvokeTimeoutError:
        print("⚠️ APIタイムアウト！Bluesky側の応答がないか、接続に時間がかかりすぎたみたい。")
        
# 🔧 エントリーポイント
if __name__ == "__main__":
    run_once()