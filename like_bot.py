# like_bot.py
from atproto import Client
import time
import os
from dotenv import load_dotenv

# ------------------------------
# ★ カスタマイズポイント: いいね対象のハッシュタグとキーワード
# ------------------------------
# 以下のリストを編集して、いいねする投稿をカスタム！
# 例: 忍たんBotなら ['#忍者', '#侍'], ['忍者', '侍']
TARGET_HASHTAGS = [
    '#地雷女', '#病み垢', '#病みかわ', '#可愛い', '#かわいい', '#メンヘラ',
    '#猫', '#ねこ', '#量産系', '#オリキャラ', '#推し', '#jirai',
    '#一次創作', '#オリジナル', '#イラスト', '#推しキャラプロフィールメーカー'
]
TARGET_KEYWORDS = [
    '地雷', '量産', '裏垢', '病み', '可愛い', 'かわいい', 'メンヘラ',
    '猫', 'ねこ', '相性診断', 'オリキャラ', '推し', 'jirai',
    '一次創作', 'オリジナル', 'イラスト', 'プロフィールメーカー'
]

# ✅ 環境変数の読み込み（.env または Secrets）
load_dotenv()
HANDLE = os.getenv("HANDLE") or exit("❌ HANDLEが設定されていません")
APP_PASSWORD = os.getenv("APP_PASSWORD") or exit("❌ APP_PASSWORDが設定されていません")

# 🔐 Blueskyクライアント初期化
client = Client()
try:
    client.login(HANDLE, APP_PASSWORD)
    print("✅ ログイン成功")
    self_did = client.me.did
except Exception as e:
    print(f"❌ ログイン失敗: {e}")
    exit(1)

# 📜 セッション内のいいね履歴（保険）
liked_uris = set()

def like_post_if_needed(uri, cid, text, viewer_like=None):
    """投稿にいいね。すでにいいね済み（viewer_like）またはセッション内履歴（liked_uris）ならスキップ"""
    if viewer_like:
        print(f"⏩ いいね済みスキップ: {text[:40]}")
        return
    if uri in liked_uris:
        print(f"⏩ セッション内スキップ: {text[:40]}")
        return
    try:
        client.app.bsky.feed.like.create(
            repo=client.me.did,
            record={
                "subject": {"uri": uri, "cid": cid},
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        )
        liked_uris.add(uri)
        print(f"❤️ いいね: {text[:40]}")
    except Exception as e:
        print(f"⚠️ いいね失敗: {e}")

def auto_like_timeline():
    """タイムラインの投稿をチェックし、対象にいいね"""
    print("📡 タイムライン巡回中...")
    try:
        feed_res = client.app.bsky.feed.get_timeline(params={"limit": 50})
        feed_items = feed_res.feed
        for item in feed_items:
            post = item.post
            text = post.record.text.lower()
            uri = post.uri
            cid = post.cid
            author_did = post.author.did

            if author_did == self_did:
                print(f"⏩ 自己投稿スキップ: {text[:40]}")
                continue
            if any(tag.lower() in text for tag in TARGET_HASHTAGS) or any(kw.lower() in text for kw in TARGET_KEYWORDS):
                viewer_like = post.viewer.like if hasattr(post, 'viewer') and hasattr(post.viewer, 'like') else None
                like_post_if_needed(uri, cid, text, viewer_like)
    except Exception as e:
        print(f"❌ タイムラインエラー: {e}")

def auto_like_mentions():
    """メンション通知にいいね"""
    print("🔔 メンションチェック中...")
    try:
        notes = client.app.bsky.notification.list_notifications(params={"limit": 50}).notifications
        for note in notes:
            if note.reason == "mention":
                uri = note.uri
                cid = note.cid
                text = note.record.text.lower()
                try:
                    # get_posts に params={} を明示
                    post = client.app.bsky.feed.get_posts(uris=[uri], params={}).posts[0]
                    viewer_like = post.viewer.like if hasattr(post, 'viewer') and hasattr(post.viewer, 'like') else None
                    like_post_if_needed(uri, cid, text, viewer_like)
                except Exception as e:
                    print(f"⚠️ メンション投稿取得エラー (URI: {uri}): {e}")
                    continue
    except Exception as e:
        print(f"❌ メンション通知エラー: {e}")

def auto_like_back():
    """いいねしてくれたユーザーの最新投稿にいいね返し"""
    print("🔁 いいね返し中...")
    try:
        notes = client.app.bsky.notification.list_notifications(params={"limit": 50}).notifications
        for note in notes:
            if note.reason == "like":
                user_did = note.author.did
                if user_did == self_did:
                    print(f"⏩ 自己いいねスキップ")
                    continue
                feed_res = client.app.bsky.feed.get_author_feed(params={"actor": user_did, "limit": 1})
                posts = feed_res.feed
                if not posts:
                    print(f"⏩ 投稿なしスキップ: {user_did}")
                    continue
                post = posts[0].post
                uri = post.uri
                cid = post.cid
                text = post.record.text.lower()
                viewer_like = post.viewer.like if hasattr(post, 'viewer') and hasattr(post.viewer, 'like') else None
                like_post_if_needed(uri, cid, text, viewer_like)
    except Exception as e:
        print(f"❌ いいね返しエラー: {e}")

def start():
    """いいねBotメイン処理"""
    print(f"🚀 LikeBot 起動しました: @{HANDLE}")
    auto_like_timeline()
    auto_like_mentions()
    auto_like_back()
    print(f"✅ 実行完了: いいね {len(liked_uris)}件")

if __name__ == "__main__":
    start()