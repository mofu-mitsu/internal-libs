from atproto import Client
import time
from dotenv import load_dotenv
from pathlib import Path
import os

# --- 環境変数の読み込み (.env) ---
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

HANDLE = os.getenv('HANDLE')
APP_PASSWORD = os.getenv('APP_PASSWORD')

# --- タグ＆キーワード定義 ---
TARGET_HASHTAGS = [
    '#地雷女', '#病みかわ', '#メンヘラ', '#地雷系', '#量産系', '#推しキャラプロフィールメーカー',
    '#オリキャラプロフィールメーカー', '#もふみつ工房', '#ふわふわ相性診断', '#ふわふわ相性診断メーカー'
]

TARGET_KEYWORDS = [
    '地雷', '量産', '病みかわ', 'メンヘラ', '相性診断', 'プロフィールメーカー',
    'ふわふわ', 'もふみつ', '推し紹介', 'ツインテール', '闇かわ', '黒リボン',
    '推しキャラ', 'オリキャラ', '創作垢', '絵描きさん', 'かわいい', '可愛い'
]

# --- クライアント初期化 ---
client = Client()

try:
    client.login(HANDLE, APP_PASSWORD)
    print("ログイン成功")
    self_did = client.me.did
    print(f"自分のDID: {self_did}")
except Exception as e:
    print(f"ログインまたはDID取得エラー: {e}")
    self_did = None  # 失敗時はNoneにして止まらないように

# --- いいね済みURI記録用 ---
liked_uris = set()

# --- いいね処理定義 ---

def auto_like_by_tags_and_keywords():
    print("タグ＆キーワード巡回中...")
    try:
        feed = client.app.bsky.feed.get_timeline().feed
        for item in feed:
            post = item.post
            author_did = post.author.did
            text = post.record.text
            uri = post.uri
            cid = post.cid

            if author_did == self_did:
                continue

            if uri in liked_uris:
                continue

            if any(tag in text for tag in TARGET_HASHTAGS) or any(kw in text for kw in TARGET_KEYWORDS):
                client.app.bsky.feed.like.create(
                    repo=HANDLE,
                    record={
                        "subject": {"uri": uri, "cid": cid},
                        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    })
                liked_uris.add(uri)
                print(f"いいね: {text[:50]}...")
    except Exception as e:
        print(f"タイムライン処理中エラー: {e}")


def auto_like_mentions():
    print("メンションチェック中...")
    try:
        notifications = client.app.bsky.notification.list_notifications().notifications
        for note in notifications:
            if note.reason == "mention":
                uri = note.uri
                cid = note.cid

                if uri in liked_uris:
                    continue

                client.app.bsky.feed.like.create(
                    repo=HANDLE,
                    record={
                        "subject": {"uri": uri, "cid": cid},
                        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    })
                liked_uris.add(uri)
                print(f"メンションにいいね: {note.record.text[:50]}...")
    except Exception as e:
        print(f"メンション処理中エラー: {e}")


def auto_like_back():
    print("いいね返し中...")
    try:
        notifications = client.app.bsky.notification.list_notifications().notifications
        for note in notifications:
            if note.reason == "like":
                user_did = note.author.did
                if user_did == self_did:
                    continue

                feed_res = client.app.bsky.feed.get_author_feed({"actor": user_did, "limit": 1})
                feed = feed_res.feed

                if feed:
                    post = feed[0].post
                    uri = post.uri
                    cid = post.cid

                    if uri in liked_uris:
                        continue

                    client.app.bsky.feed.like.create(
                        repo=HANDLE,
                        record={
                            "subject": {"uri": uri, "cid": cid},
                            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                        })
                    liked_uris.add(uri)
                    print(f"いいね返し: {post.record.text[:50]}...")
    except Exception as e:
        print(f"いいね返しエラー: {e}")


# --- start() 関数定義（main.pyから呼ばれる） ---
def start():
    print("【LikeBot 起動しました】")
    while self_did:
        try:
            auto_like_by_tags_and_keywords()
            auto_like_mentions()
            auto_like_back()
        except Exception as e:
            print(f"LikeBot全体でエラー: {e}")
        time.sleep(600)  # ←10分ごとに巡回