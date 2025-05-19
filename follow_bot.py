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

    # フォロー一覧（自分がフォローしている）
    follows = client.app.bsky.graph.get_follows(params={"actor": self_did, "limit": 100}).follows
    following_handles = {user.did: user for user in follows}  # dictにしてrkey取得のために保持

    # フォロワー一覧（自分をフォローしてくれている）
    followers = client.app.bsky.graph.get_followers(params={"actor": self_did, "limit": 100}).followers
    follower_handles = set(user.did for user in followers)

    to_follow = follower_handles - set(following_handles.keys())
    to_unfollow = set(following_handles.keys()) - follower_handles

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

    for did in to_unfollow:
        try:
            # 既に取得済みのfollow情報からrkeyを取り出して解除
            follow_user = following_handles.get(did)
            if follow_user and hasattr(follow_user, "uri"):
                rkey = follow_user.uri.split('/')[-1]
                client.app.bsky.graph.unfollow.delete(repo=self_did, rkey=rkey)
                print(f"🔕 フォロー解除しました: {did}")
            else:
                print(f"⚠️ rkey取得失敗: {did}（uriが見つからない）")
        except Exception as e:
            print(f"⚠️ フォロー解除失敗: {did} - {e}")

if __name__ == "__main__":
    start()
