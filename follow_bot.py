from atproto import Client, models
import os
from dotenv import load_dotenv

# .env 読み込み
load_dotenv()
HANDLE = os.getenv("HANDLE")
APP_PASSWORD = os.getenv("APP_PASSWORD")


# 怪しいユーザー判定関数
def is_suspicious_user(profile):
    suspicious_keywords = ["援交", "nsfw", "副業", "稼げる", "大人", "出会い", "無料", "click", "副収入"]
    suspicious_domains = ["xyz", "click", "cash", "club"]

    display_name = profile.display_name or ""
    description = profile.description or ""
    handle = profile.handle or ""
    avatar = profile.avatar

    # 表示名・説明に危険ワードが含まれてるか？
    for keyword in suspicious_keywords:
        if keyword.lower() in display_name.lower() or keyword.lower() in description.lower():
            return True

    # ドメインが怪しい（例：username@xyz）
    if any(handle.endswith(f".{domain}") for domain in suspicious_domains):
        return True

    # アイコンなし
    if avatar is None:
        return True

    return False


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

    # フォロバ処理（信頼できるアカウントのみ）
    for did in to_follow:
        try:
            profile = client.app.bsky.actor.get_profile(actor=did)
            if is_suspicious_user(profile):
                print(f"⚠️ 怪しいアカウントをスキップ: {profile.handle}")
                continue

            follow_record = models.AppBskyGraphFollow.Record(
                subject=did,
                created_at=client.get_current_time_iso()
            )
            client.app.bsky.graph.follow.create(repo=self_did, record=follow_record)
            print(f"✅ フォロバしました: {profile.handle}")
        except Exception as e:
            print(f"❌ フォロバ失敗: {did} - {e}")

    # フォロー解除処理
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