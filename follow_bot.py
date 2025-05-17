from atproto import Client
import os
from dotenv import load_dotenv

# .env 読み込み
load_dotenv()
HANDLE = os.getenv("HANDLE")
APP_PASSWORD = os.getenv("APP_PASSWORD")

def start():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    print("フォロー管理開始！")

    # 自分がフォローしているユーザー一覧
follows = client.app.bsky.graph.get_follows(params={"actor": HANDLE, "limit": 100}).follows
following_handles = set(user.did for user in follows)

# 自分をフォローしてくれているユーザー一覧
followers = client.app.bsky.graph.get_followers(params={"actor": HANDLE, "limit": 100}).followers
follower_handles = set(user.did for user in followers)

    # フォロバすべきユーザー
    to_follow = follower_handles - following_handles
    # フォロー解除すべきユーザー（※任意）
    to_unfollow = following_handles - follower_handles

    for did in to_follow:
        try:
            client.app.bsky.graph.follow(repository=HANDLE, subject=did)
            print(f"フォロバしました: {did}")
        except Exception as e:
            print(f"フォロー失敗: {did} - {e}")

    # （※任意）フォロー解除処理
    for did in to_unfollow:
        try:
            client.app.bsky.graph.unfollow(repository=HANDLE, subject=did)
            print(f"フォロー解除しました: {did}")
        except Exception as e:
            print(f"フォロー解除失敗: {did} - {e}")

if __name__ == "__main__":
    start()
