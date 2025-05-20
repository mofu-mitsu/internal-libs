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

    follows = client.app.bsky.graph.get_follows(params={"actor": self_did, "limit": 100}).follows
    following_handles = set(user.did for user in follows)

    followers = client.app.bsky.graph.get_followers(params={"actor": self_did, "limit": 100}).followers
    follower_handles = set(user.did for user in followers)

    to_follow = follower_handles - following_handles
    to_unfollow = following_handles - follower_handles

    # フォロバ処理
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

    # フォロー解除処理（delete_record で対応）
    try:
        repo_follows = client.com.atproto.repo.list_records(params={
            "repo": self_did,
            "collection": "app.bsky.graph.follow",
            "limit": 100
        }).records

        did_to_rkey = {record.value["subject"]: record.uri.split('/')[-1] for record in repo_follows}

        for did in to_unfollow:
            rkey = did_to_rkey.get(did)
            if rkey:
                client.com.atproto.repo.delete_record(
                    data=models.ComAtprotoRepoDeleteRecord.Data(
                        repo=self_did,
                        collection="app.bsky.graph.follow",
                        rkey=rkey
                    )
                )
                print(f"🔕 フォロー解除しました: {did}")
            else:
                print(f"⚠️ rkey取得失敗: {did}（uriが見つからない）")

    except Exception as e:
        print(f"❌ フォロー解除全体で失敗: {e}")

if __name__ == "__main__":
    start()