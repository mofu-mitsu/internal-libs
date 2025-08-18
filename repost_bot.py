# 🔽 📦 Pythonの標準ライブラリ
import time
import os
import random
from datetime import datetime, timezone, timedelta

# 🔽 🌱 外部ライブラリ
from dotenv import load_dotenv

# 🔽 📡 atproto関連
from atproto import Client

# ------------------------------
# ★ カスタマイズポイント: リポスト対象のハッシュタグとキーワード
# ------------------------------
TARGET_HASHTAGS = [
    '#オリキャラプロフィールメーカー', '#ふわふわ相性診断', '#推しプロフィールメーカー', '#もふみつ工房', '#みりんてゃ', '#みりんてゃbot','#チャッピー供養ギャラリー',
]
TARGET_KEYWORDS = [
    'オリキャラプロフィールメーカー', 'ふわふわ相性診断', '推しプロフィールメーカー', 'もふみつ工房', 'みりんてゃbot','みりんてゃ',
]

# ------------------------------
# ★ カスタマイズポイント: 引用リポストのコメント
# ------------------------------
REPOST_COMMENTS = [
    "キラキラ✨ みりんてゃ推しなのっ♡",
    "ふwaふwa〜！これ超かわいいなのっ♪",
    "えへ〜♪ 君の投稿、めっちゃ好きだよ♡",
    "ぎゅっ♡ このポスト、みりんてゃのお気に入り！",
    "これ見てニコニコしちゃったぁ〜🎀>  ̫ <🎀",
    "キミのセンス、バチバチに光ってるぅ✨✨",
    "だいすきっ♡ もっかい読んじゃったのっ！",
    "ぎゃ〜〜！最高すぎてみりんてゃ昇天✝️♡",
    "尊すぎて語彙力とけた...ふにゃあ〜〜〜〜(꒪꒳꒪ )",
    "これ、みりんてゃの心にずきゅんだよ(ˆ⩌⩊⩌ˆ)💘★",
]

# ✅ 環境変数の読み込み
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

# 📜 セッション内のリポスト履歴
reposted_uris = set()
# 永続ストレージファイル
REPOSTED_FILE = "reposted_uris.txt"
# 統計用カウンター
repost_count = 0
skip_count = 0
error_count = 0

def normalize_uri(uri):
    """URIを正規化（API仕様変更対応）"""
    try:
        if not uri.startswith('at://'):
            uri = f"at://{uri.lstrip('/')}"
        parts = uri.split('/')
        if len(parts) >= 5:
            return f"at://{parts[2]}/{parts[3]}/{parts[4]}"
        return uri
    except Exception as e:
        print(f"⚠️ URI正規化エラー: {e}")
        return uri

def load_reposted_uris():
    """永続リポスト履歴を読み込む"""
    global reposted_uris
    reposted_uris.clear()
    if os.path.exists(REPOSTED_FILE):
        try:
            with open(REPOSTED_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                reposted_uris.update(normalize_uri(line.strip()) for line in lines if line.strip())
            print(f"📂 既存リポスト履歴を読み込み: {len(reposted_uris)}件")
            if reposted_uris:
                print(f"📜 履歴サンプル: {list(reposted_uris)[:5]}")
        except Exception as e:
            print(f"⚠️ 履歴読み込みエラー: {e}")
    else:
        print(f"📂 {REPOSTED_FILE} が見つかりません。新規作成します")
        with open(REPOSTED_FILE, 'w', encoding='utf-8') as f:
            pass

def save_reposted_uri(uri):
    """リポスト履歴を保存"""
    normalized_uri = normalize_uri(uri)
    if normalized_uri in reposted_uris:
        print(f"⏩ 履歴保存スキップ（既存）: {normalized_uri}")
        return
    try:
        with open(REPOSTED_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{normalized_uri}\n")
        reposted_uris.add(normalized_uri)
        print(f"💾 履歴保存: {normalized_uri}")
    except Exception as e:
        print(f"⚠️ 履歴保存エラー: {e}")

def has_reposted(uri, cid):
    """引用リポストまたは通常リポスト済みかチェック"""
    try:
        normalized_uri = normalize_uri(uri)
        # 引用リポストチェック
        feed = client.app.bsky.feed.get_author_feed(params={"actor": self_did, "limit": 100})
        for item in feed.feed:
            post = item.post
            if hasattr(post.record, 'embed') and post.record.embed:
                embed = post.record.embed
                if hasattr(embed, 'record') and normalize_uri(embed.record.uri) == normalized_uri:
                    print(f"📌 引用リポスト検出: URI={uri}")
                    return True
        # 通常リポストチェック
        records = client.com.atproto.repo.list_records(
            params={"repo": self_did, "collection": "app.bsky.feed.repost", "limit": 100}
        )
        for record in records.records:
            if hasattr(record.value, 'subject') and normalize_uri(record.value.subject.uri) == normalized_uri:
                print(f"📌 通常リポスト検出: URI={uri}")
                return True
        print(f"📌 リポストなし: URI={uri}")
        return False
    except Exception as e:
        print(f"⚠️ リポストチェックエラー (URI: {uri}): {e}")
        print(f"🚫 安全のためスキップ: URI={uri}")
        return True

def repost_if_needed(uri, cid, text, post, is_quote=False):
    """リポスト処理"""
    global repost_count, skip_count, error_count
    normalized_uri = normalize_uri(uri)
    if normalized_uri in reposted_uris:
        print(f"⏩ 履歴スキップ: {text[:40]}")
        skip_count += 1
        return
    if has_reposted(uri, cid):
        print(f"⏩ スキップ（リポスト済み）: {text[:40]}")
        skip_count += 1
        return
    try:
        if is_quote:
            comment = random.choice(REPOST_COMMENTS)
            client.app.bsky.feed.post.create(
                repo=client.me.did,
                record={
                    "text": comment,
                    "embed": {
                        "$type": "app.bsky.embed.record",
                        "record": {"uri": str(uri), "cid": str(cid)}
                    },
                    "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            )
            print(f"📬 引用リポスト: {comment[:40]} (元: {text[:40]})")
        else:
            client.app.bsky.feed.repost.create(
                repo=client.me.did,
                record={
                    "subject": {"uri": str(uri), "cid": str(cid)},
                    "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            )
            print(f"🔄 リポスト: {text[:40]}")
        save_reposted_uri(uri)
        repost_count += 1
    except Exception as e:
        print(f"⚠️ リポスト失敗 (URI: {uri}): {e}")
        error_count += 1

def auto_repost_timeline():
    """タイムラインの投稿をチェックし、対象をリポスト"""
    global skip_count, error_count
    print("📡 タイムライン巡回中...")
    try:
        feed_res = client.app.bsky.feed.get_timeline(params={"limit": 100})  # 50→100に増やす
        feed_items = feed_res.feed
        for item in feed_items:
            post = item.post
            text = post.record.text.lower() if hasattr(post.record, 'text') else ""
            uri = post.uri
            cid = post.cid
            author_did = post.author.did
            created_at = post.record.created_at if hasattr(post.record, 'created_at') else None
            if created_at:
                try:
                    created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if created_at_dt < datetime.now(timezone.utc) - timedelta(days=7):
                        print(f"⏩ スキップ（古い投稿）: {text[:40]}")
                        skip_count += 1
                        continue
                except ValueError:
                    print(f"⚠️ 日時パースエラー: {created_at}")
            # 自己投稿とリプライのみスキップ
            if author_did == self_did or (hasattr(post.record, 'reply') and post.record.reply):
                print(f"⏩ スキップ (自己/リプ): {text[:40]}")
                skip_count += 1
                continue
            # ハッシュタグ・キーワードチェック
            if any(tag.lower() in text for tag in TARGET_HASHTAGS) or any(kw.lower() in text for kw in TARGET_KEYWORDS):
                is_quote = random.random() < 0.5
                print(f"🎯 検知: {text[:40]} (タグ/キーワード一致)")
                repost_if_needed(uri, cid, text, post, is_quote=is_quote)
            else:
                print(f"⏩ スキップ (タグ/キーワードなし): {text[:40]}")
    except Exception as e:
        print(f"❌ タイムラインエラー: {e}")
        error_count += 1

def start():
    """リポストBotメイン処理"""
    global repost_count, skip_count, error_count
    print(f"🚀 りぽりんBot 起動しました: @{HANDLE}")
    load_reposted_uris()
    auto_repost_timeline()
    print(f"✅ 実行完了: リポスト {repost_count}件, スキップ {skip_count}件, エラー {error_count}件")

if __name__ == "__main__":
    start()
