# 🔽 📦 Pythonの標準ライブラリ
from datetime import datetime, timezone
import os
import json
import requests
import time
import random

# 🔽 🌱 外部ライブラリ
from dotenv import load_dotenv

# 🔽 📡 atproto関連
from atproto import Client, models
from atproto_client.models import AppBskyFeedPost
from atproto_client.exceptions import InvokeTimeoutError

# 🔧 投稿参照用の強参照生成
def get_strong_ref_from_post(post_obj):
    return {
        "$type": "com.atproto.repo.strongRef",
        "uri": post_obj.uri,
        "cid": post_obj.cid,
    }

# リポストスキップ用
def is_quoted_repost(post):
    """引用リポストかチェック"""
    try:
        if hasattr(post.post.record, 'embed') and post.post.record.embed:
            embed = post.post.record.embed
            if hasattr(embed, 'record'):
                print(f"📌 引用リポスト検出: URI={embed.record.uri}")
                return True
        return False
    except Exception as e:
        print(f"⚠️ 引用リポストチェックエラー: {e}")
        return False

# ふわもこBotの履歴読み込み
def load_fuwamoko_uris():
    FUWAMOKO_FILE = "fuwamoko_empathy_uris.txt"
    if os.path.exists(FUWAMOKO_FILE):
        try:
            with open(FUWAMOKO_FILE, 'r', encoding='utf-8') as f:
                uris = {line.split('|')[0].strip() for line in f if line.strip()}
                print(f"✅ 読み込んだ fuwamoko_uris: {len(uris)}件")
                return uris
        except Exception as e:
            print(f"⚠️ fuwamoko_uris読み込みエラー: {e}")
            return set()
    return set()

# .envファイルを読み込む
load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HANDLE = os.environ['HANDLE']
APP_PASSWORD = os.environ['APP_PASSWORD']
GIST_TOKEN = os.environ["GIST_TOKEN"]
print(f"🪪 現在のGIST_TOKEN: {GIST_TOKEN[:8]}...（先頭8文字だけ表示）")

# Gist URL（直書き）
GIST_RAW_URL_URIS = "https://gist.githubusercontent.com/mofu-mitsu/c16e8c8c997186319763f0e03f3cff8b/raw/replied_uris.json"
GIST_ID_URIS = "c16e8c8c997186319763f0e03f3cff8b"
GIST_RAW_URL_TEXTS = "https://gist.githubusercontent.com/mofu-mitsu/a149431b226cf7b50ba057be4de7eae9/raw/replied_texts.json"
GIST_ID_TEXTS = "a149431b226cf7b50ba057be4de7eae9"

# 🧷 Gistのバックアップ
def backup_gist(gist_id, filename, content):
    backup_filename = filename.replace(".json", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "files": {
            backup_filename: {
                "content": content
            }
        }
    }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"📦 バックアップ作成完了: {backup_filename}")
    else:
        try:
            msg = response.json().get("message", "")
        except:
            msg = response.text
        print(f"⚠️ バックアップ失敗: {response.status_code} {msg}")

# 🔹 replied_uris の読み書き
def load_replied_uris():
    print(f"🌐 Gistから読み込み中: {GIST_RAW_URL_URIS}")
    try:
        response = requests.get(GIST_RAW_URL_URIS)
        if response.status_code == 200:
            uris = json.loads(response.text)
            print(f"✅ 読み込んだ replied_uris: {uris[:5]}")
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
    content = json.dumps(list(replied_uris), ensure_ascii=False, indent=2)
    backup_gist(GIST_ID_URIS, "replied_uris.json", content)
    time.sleep(1)
    data = {
        "files": {
            "replied_uris.json": {
                "content": content
            }
        }
    }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print("💾 replied_uris.json に保存完了！")
    else:
        try:
            msg = response.json().get("message", "")
        except:
            msg = response.text
        print(f"⚠️ replied_uris保存失敗: {response.status_code} {msg}")

# 🔸 replied_texts の読み書き
def load_replied_texts():
    print(f"🌐 Gistから読み込み中: {GIST_RAW_URL_TEXTS}")
    try:
        response = requests.get(GIST_RAW_URL_TEXTS)
        if response.status_code == 200:
            texts = json.loads(response.text)
            print(f"✅ 読み込んだ replied_texts の一部: {list(texts.items())[:3]}")
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
    content = json.dumps(replied_texts, ensure_ascii=False, indent=2)
    backup_gist(GIST_ID_TEXTS, "replied_texts.json", content)
    time.sleep(1)
    data = {
        "files": {
            "replied_texts.json": {
                "content": content
            }
        }
    }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print("💾 replied_texts.json に保存完了！")
    else:
        try:
            msg = response.json().get("message", "")
        except:
            msg = response.text
        print(f"⚠️ replied_texts保存失敗: {response.status_code} {msg}")

# 🔹 りぽりんBotの履歴（オプション）
def load_reposted_uris():
    REPOSTED_FILE = "reposted_uris.txt"
    if os.path.exists(REPOSTED_FILE):
        try:
            with open(REPOSTED_FILE, 'r', encoding='utf-8') as f:
                uris = set(line.strip() for line in f if line.strip())
                print(f"✅ 読み込んだ reposted_uris: {len(uris)}件")
                return uris
        except Exception as e:
            print(f"⚠️ reposted_uris読み込みエラー: {e}")
            return set()
    return set()

# ------------------------------
# ★ カスタマイズポイント: キーワード返信（REPLY_TABLE）
# ------------------------------
KEYWORD_RESPONSES = {
    "みりんてゃちゃん": "てゃちゃん！？てゃちゃんって……かわいすぎる呼び方っ♡ 呼び続けてほしいの〜っ！",
    "みりんてゃー": "え〜ん、のばして呼ばれたら照れちゃうっ♡ 今日も一番かわいいって言ってぇ〜っ！",
    "みりんちゃん": "あ、もしかして本名で呼んでくれたのっ？♡ ふふっ、ちょっとだけ照れちゃうけど……そういうの、実はうれしいんだよね♡",
    "美琳": "あ、もしかして本名で呼んでくれたのっ？♡ ふふっ、ちょっとだけ照れちゃうけど……そういうの、実はうれしいんだよね♡",
    "みりてゃ": "えっ、呼んだ〜！！？みりてゃ参上っ♡ 今日も世界の中心でかわいいしてるよぉっ！",
    "みりんてゃ": "みりんてゃのこと呼んだ〜？？♡もぉ〜っ！かまってくれて嬉しいに決まってるじゃん♡",
    "もふみつ工房": "わぁっ、見てくれたの〜？♡ みりんてゃの本拠地、気に入ってもらえたらうれしすぎて鼻血でちゃうかもっ",
    "推しプロフィールメーカー": "それな〜っ！推しはプロフィールまで尊い♡ みりてゃの推しは……えへへ、ヒミツ♡",
    "オリキャラプロフィールメーカー": "オリキャラって…自分の分身でしょ？ うちの子語り、聞かせてよ〜♡ みりんてゃも聞きた〜い！",
    "ふわふわ相性診断": "ふたりの相性…ふわふわで、とけちゃいそうっ♡ 結果どうだった〜？教えて教えてっ！",
}

# Facet（ハッシュタグなど）の位置を取得
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


def run_once():
    try:
        client = Client()
        client.login(HANDLE, APP_PASSWORD)
        print("📨 投稿を確認中…")

        # --- ✨ エラー回避のバリア！ ---
        try:
            timeline = client.app.bsky.feed.get_timeline(params={"limit": 20})
            feed = timeline.feed
        except Exception as e:
            print(f"⚠️ タイムライン取得エラー（Blueskyの新しい仕様が原因かも）: {e}")
            print("💡 GitHub Actionsで 'pip install --upgrade atproto' を実行してね！今回は安全にスキップするよ。")
            return
        # -----------------------------

        replied_uris = load_replied_uris()
        replied_texts = load_replied_texts()
        reposted_uris = load_reposted_uris()
        fuwamoko_uris = load_fuwamoko_uris()

        for post in feed:
            time.sleep(random.uniform(10, 20))
            text = getattr(post.post.record, "text", None)
            uri = str(post.post.uri)
            post_id = uri.split('/')[-1]
            author = post.post.author.handle

            replied_post_ids = set(u.split('/')[-1] for u in replied_uris)
            reposted_post_ids = set(u.split('/')[-1] for u in reposted_uris)
            fuwamoko_post_ids = set(u.split('/')[-1] for u in fuwamoko_uris)

            print(f"📝 処理対象URI: {uri}")

            # スキップ条件
            if author == HANDLE or post_id in replied_post_ids or post_id in fuwamoko_post_ids or not text:
                continue
            if hasattr(post.post.record, "reply") and post.post.record.reply is not None:
                continue
            if post_id in reposted_post_ids:
                continue
            if hasattr(post, 'reason') and getattr(post.reason, '$type', None) == 'app.bsky.feed.defs#reasonRepost':
                continue
            if is_quoted_repost(post):
                continue

            print(f"👀 チェック中 → @{author}: {text}")
            matched = False
            reply_text = ""

            for keyword, response in KEYWORD_RESPONSES.items():
                if keyword in text.lower():
                    reply_text = response
                    matched = True
                    print(f"✨ キーワード「{keyword}」にマッチ！")
                    break

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
                replied_uris.add(uri)
                save_replied_uris(replied_uris)
                replied_texts[text] = True
                save_replied_texts(replied_texts)
                print(f"✅ 返信しました → @{author}")
            except Exception as e:
                print(f"⚠️ 返信エラー: {e}")

    except InvokeTimeoutError:
        print("⚠️ APIタイムアウト！Bluesky側の応答がないか、接続に時間がかかりすぎたみたい。")
    except Exception as e:
        print(f"❌ 予期せぬエラーで停止しました: {e}")

if __name__ == "__main__":
    run_once()
