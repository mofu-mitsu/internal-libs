from atproto import Client, models
import os
from dotenv import load_dotenv

# .env 読み込み
load_dotenv()
HANDLE = os.getenv("HANDLE")
APP_PASSWORD = os.getenv("APP_PASSWORD")

def start():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)
    print("🤝 フォロー管理開始！")

    self_did = client.me.did

    # 自分のフォロー一覧（プロフィール情報だけ）
    follows = client.app.bsky.graph.get_follows(params={"actor": self_did, "limit": 100}).follows
    following_dids = set(user.did for user in follows)

    # 自分をフォローしてくれてる人
    followers = client.app.bsky.graph.get_followers(params={"actor": self_did, "limit": 100}).followers
    follower_dids = set(user.did for user in followers)

    to_follow = follower_dids - following_dids
    to_unfollow = following_dids - follower_dids

    # 🔍 自分の follow レコード一覧（ここに rkey や uri がある！）
    repo_follows = client.com.atproto.repo.list_records(
        repo=self_did,
        collection="app.bsky.graph.follow",
        limit=100
    ).records

    # did をキーに、uriとrkeyをひもづける辞書を作る
    did_to_record = {}
    for record in repo_follows:
        value = record.value
        if isinstance(value, dict) and "subject" in value:
            did_to_record[value["subject"]] = {
                "uri": record.uri,
                "rkey": record.uri.split("/")[-1]
            }

    # フォロー処理
    for did in to_follow:
        try:
            follow_record = models.AppBskyGraphFollow.Record(
                subject=did,
                created_at=client.get_current_time_iso()
            )
            client.app.bsky.graph.follow.create(repo=self_did, record=follow_record)
            print(f"✅ フォロバしました: {did}")
        except Exception as e:
            print(f"❌ フォロー失敗: {did} - {e}")

    # フォロー解除処理
    for did in to_unfollow:
        try:
            record_info = did_to_record.get(did)
            if record_info:
                client.app.bsky.graph.unfollow.delete(repo=self_did, rkey=record_info["rkey"])
                print(f"🔕 フォロー解除しました: {did}")
            else:
                print(f"⚠️ フォロー解除失敗: {did}（rkey見つからない）")
        except Exception as e:
            print(f"⚠️ フォロー解除失敗: {did} - {e}")

if __name__ == "__main__":
    start()