from atproto import Client
import time
import os
import re
from dotenv import load_dotenv

# ------------------------------
# ★ カスタマイズポイント: いいね対象のハッシュタグとキーワード
# ------------------------------
TARGET_HASHTAGS = [
    '#地雷女', '#病み垢', '#病みかわ', '#可愛い', '#かわいい', '#メンヘラ', '#bot', 
    '#猫', '#ねこ', '#量産系', '#オリキャラ', '#推し', '#jirai', '#みりんてゃ',
    '#一次創作', '#オリジナル', '#イラスト', '#推しキャラプロフィールメーカー'
]
TARGET_KEYWORDS = [
    '地雷', '量産', '裏垢', '病み', '可愛い', 'かわいい', 'メンヘラ', 'bot', 'Bot',
    '猫', 'ねこ', '相性診断', 'オリキャラ', '推し', 'jirai', 'みりんてゃ',
    '創作', 'オリジナル', 'イラスト', 'プロフィールメーカー', 'チャッピー供養ギャラリー',
]

# ✅ 環境変数の読み込み
load_dotenv()
HANDLE = os.getenv("HANDLE") or exit("❌ HANDLEが設定されていません")
APP_PASSWORD = os.getenv("APP_PASSWORD") or exit("❌ APP_PASSWORDが設定されていません")

# 🔐 Blueskyクライアント初期化
client = Client()
try:
    client.login(HANDLE, APP_PASSWORD)
    print(f"✅ ログイン成功: @{HANDLE}")
    self_did = client.me.did
except Exception as e:
    print(f"❌ ログイン失敗: {e}")
    exit(1)

# 📜 セッション内のいいね履歴
liked_uris = set()

def like_post_if_needed(uri, cid, text, viewer_like=None):
    """投稿にいいね。すでにいいね済みならスキップ"""
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
        print(f"⚠️ いいね失敗 (URI: {uri}): {e}")

def is_priority_post(text):
    """@mirinchuuuを含む投稿を優先判定"""
    return "@mirinchuuu" in text.lower()

def auto_like_timeline():
    """タイムラインの投稿をチェック、対象にいいね"""
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
            reply = getattr(post.record, "reply", None)
            if reply is not None and not is_priority_post(text):
                print(f"⏩ リプライスキップ (非@mirinchuuu, reply={reply}): {text[:40]}")
                continue
            if any(tag.lower() in text for tag in TARGET_HASHTAGS) or any(kw.lower() in text for kw in TARGET_KEYWORDS) or is_priority_post(text):
                viewer_like = post.viewer.like if hasattr(post, 'viewer') and hasattr(post.viewer, 'like') else None
                like_post_if_needed(uri, cid, text, viewer_like)
            else:
                print(f"⏩ 条件外スキップ: {text[:40]}")
    except Exception as e:
        print(f"❌ タイムラインエラー: {e}")

def auto_like_mentions():
    """メンション通知にいいね、@mirinchuuu優先"""
    print("🔔 メンションチェック中...")
    try:
        notes = client.app.bsky.notification.list_notifications(params={"limit": 50}).notifications
        print("📜 通知一覧:")
        for note in notes:
            print(f"  - 理由: {note.reason}, URI: {note.uri}, テキスト: {getattr(note.record, 'text', 'なし')[:40]}")
        for note in notes:
            if note.reason == "mention":
                uri = note.uri
                cid = note.cid
                text = note.record.text.lower() if hasattr(note, 'record') and hasattr(note.record, 'text') else ""
                if not text:
                    print(f"⏩ メンション無効スキップ (URI: {uri}): テキストなし")
                    continue
                try:
                    posts = client.app.bsky.feed.get_posts({"uris": [str(uri)]}).posts
                    if not posts:
                        print(f"⚠️ メンション投稿取得失敗（空）(URI: {uri})")
                        continue
                    post = posts[0]
                    reply = getattr(post.record, "reply", None)
                    if reply is not None and not is_priority_post(text):
                        print(f"⏩ リプライスキップ (非@mirinchuuu, reply={reply}): {text[:40]}")
                        continue
                    viewer_like = post.viewer.like if hasattr(post, 'viewer') and hasattr(post.viewer, 'like') else None
                    like_post_if_needed(uri, cid, text, viewer_like)
                except Exception as e:
                    print(f"⚠️ メンション投稿取得エラー (URI: {uri}): {e}")
                    continue
    except Exception as e:
        print(f"❌ メンション通知エラー: {e}")

def auto_like_back():
    """いいねしてくれたユーザーの最新投稿（リプライ除外）にいいね返し"""
    print("🔁 いいね返し中...")
    try:
        notes = client.app.bsky.notification.list_notifications(params={"limit": 50}).notifications
        for note in notes:
            if note.reason == "like":
                user_did = note.author.did
                if user_did == self_did:
                    print(f"⏩ 自己いいねスキップ")
                    continue
                feed_res = client.app.bsky.feed.get_author_feed(params={"actor": user_did, "limit": 5})
                posts = feed_res.feed
                if not posts:
                    print(f"⏩ 投稿なしスキップ: {user_did}")
                    continue
                for feed_post in posts:
                    post = feed_post.post
                    text = post.record.text.lower()
                    reply = getattr(post.record, "reply", None)
                    if reply is not None and not is_priority_post(text):
                        print(f"⏩ リプライスキップ (非@mirinchuuu, reply={reply}): {text[:40]}")
                        continue
                    uri = post.uri
                    cid = post.cid
                    viewer_like = post.viewer.like if hasattr(post, 'viewer') and hasattr(post.viewer, 'like') else None
                    like_post_if_needed(uri, cid, text, viewer_like)
                    break
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