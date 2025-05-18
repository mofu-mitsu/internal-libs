from atproto import Client
import time
import os

# ✅ GitHub Actions の Secrets から直接環境変数を取得
HANDLE = os.environ["HANDLE"]
APP_PASSWORD = os.environ["APP_PASSWORD"]

# 🎯 いいね対象のハッシュタグとキーワード
TARGET_HASHTAGS = ['#地雷女', '#病みかわ', '#メンヘラ', '#量産系', '#推しキャラプロフィールメーカー']
TARGET_KEYWORDS = ['地雷', '量産', '病みかわ', 'メンヘラ', '相性診断', 'プロフィールメーカー']

client = Client()

try:
    client.login(HANDLE, APP_PASSWORD)
    print("✅ ログイン成功")
    self_did = client.me.did
except Exception as e:
    print(f"❌ ログイン失敗: {e}")
    self_did = None

liked_uris = set()

def like_post_if_needed(uri, cid, text):
    if uri in liked_uris:
        return
    try:
        client.app.bsky.feed.like.create(
            repo=client.me.did,
            record={
                "subject": {"uri": uri, "cid": cid},
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
        liked_uris.add(uri)
        print(f"❤️ いいね: {text[:40]}")
    except Exception as e:
        print(f"⚠️ いいね失敗: {e}")

def auto_like_timeline():
    print("📡 タイムライン巡回中...")
    try:
        feed_res = client.app.bsky.feed.get_timeline()
        feed_items = feed_res.feed
        for item in feed_items:
            post = item.post
            text = post.record.text
            uri = post.uri
            cid = post.cid
            author_did = post.author.did

            if author_did == self_did:
                continue
            if any(tag in text for tag in TARGET_HASHTAGS) or any(kw in text for kw in TARGET_KEYWORDS):
                like_post_if_needed(uri, cid, text)
    except Exception as e:
        print(f"❌ タイムラインエラー: {e}")

def auto_like_mentions():
    print("🔔 メンションチェック中...")
    try:
        notes = client.app.bsky.notification.list_notifications().notifications
        for note in notes:
            if note.reason == "mention":
                uri = note.uri
                cid = note.cid
                text = note.record.text
                like_post_if_needed(uri, cid, text)
    except Exception as e:
        print(f"❌ メンションエラー: {e}")

def auto_like_back():
    print("🔁 いいね返し中...")
    try:
        notes = client.app.bsky.notification.list_notifications().notifications
        for note in notes:
            if note.reason == "like":
                user_did = note.author.did
                if user_did == self_did:
                    continue

                feed_res = client.app.bsky.feed.get_author_feed({"actor": user_did, "limit": 1})
                posts = feed_res.feed
                if not posts:
                    continue

                post = posts[0].post
                uri = post.uri
                cid = post.cid
                text = post.record.text
                like_post_if_needed(uri, cid, text)
    except Exception as e:
        print(f"❌ いいね返しエラー: {e}")

def start():
    print("🚀 LikeBot 起動しました")
    auto_like_timeline()
    auto_like_mentions()
    auto_like_back()

if __name__ == "__main__":
    start()
