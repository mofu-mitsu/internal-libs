from atproto import Client, models
import os
from dotenv import load_dotenv
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 読み込み
load_dotenv()
HANDLE = os.getenv("HANDLE")
APP_PASSWORD = os.getenv("APP_PASSWORD")


# 怪しいユーザー判定関数
def is_suspicious_user(profile):
    suspicious_keywords = ["援交", "nsfw", "稼げる", "click", "副収入"]
    suspicious_domains = ["xyz", "click", "cash", "club"]

    display_name = profile.display_name or ""
    description = profile.description or ""
    handle = profile.handle or ""
    avatar = profile.avatar

    for keyword in suspicious_keywords:
        if keyword.lower() in display_name.lower() or keyword.lower() in description.lower():
            return True

    if any(handle.endswith(f".{domain}") for domain in suspicious_domains):
        return True

    if avatar is None:
        return True

    return False


def get_all_follows(client, self_did):
    follows = set()
    cursor = None
    while True:
        res = client.app.bsky.graph.get_follows(params={
            "actor": self_did,
            "limit": 100,
            **({"cursor": cursor} if cursor else {})
        })
        follows.update(user.did for user in res.follows)
        if not res.cursor:
            break
        cursor = res.cursor
        logger.info(f"📋 フォロー一覧取得中... {len(follows)}件")
    return follows


def get_all_followers(client, self_did):
    followers = set()
    cursor = None
    while True:
        res = client.app.bsky.graph.get_followers(params={
            "actor": self_did,
            "limit": 100,
            **({"cursor": cursor} if cursor else {})
        })
        followers.update(user.did for user in res.followers)
        if not res.cursor:
            break
        cursor = res.cursor
        logger.info(f"📋 フォロワー一覧取得中... {len(followers)}件")
    return followers


def get_all_follow_records(client, self_did):
    did_to_rkey = {}
    cursor = None
    while True:
        res = client.com.atproto.repo.list_records(params={
            "repo": self_did,
            "collection": "app.bsky.graph.follow",
            "limit": 100,
            **({"cursor": cursor} if cursor else {})
        })
        did_to_rkey.update({
            record.value["subject"]: record.uri.split("/")[-1]
            for record in res.records
        })
        if not res.cursor:
            break
        cursor = res.cursor
        logger.info(f"📋 フォロー解除レコード取得中... {len(did_to_rkey)}件")
    return did_to_rkey


def start():
    try:
        client = Client()
        client.login(HANDLE, APP_PASSWORD)
        logger.info("🤝 フォロー管理開始！みりんてゃを守るぜ！")

        self_did = client.me.did

        following_handles = get_all_follows(client, self_did)
        follower_handles = get_all_followers(client, self_did)

        # フォロバ対象（フォロワーだけどフォローしてない）
        to_follow = follower_handles - following_handles
        # フォロー解除対象（フォローしてるけどフォロワーじゃない）
        to_unfollow = following_handles - follower_handles

        # フォロバ処理（信頼できるアカウントのみ）
        for did in to_follow:
            try:
                profile = client.app.bsky.actor.get_profile(params={"actor": did})
                if is_suspicious_user(profile):
                    logger.warning(f"⚠️ 怪しいアカウントをスキップ: {profile.handle}")
                    continue

                follow_record = models.AppBskyGraphFollow.Record(
                    subject=did,
                    created_at=client.get_current_time_iso()
                )
                client.app.bsky.graph.follow.create(repo=self_did, record=follow_record)
                logger.info(f"✅ フォロバしました: {profile.handle}")
            except Exception as e:
                logger.error(f"❌ フォロバ失敗: {did} - {e}")

        # フォロー解除処理
        try:
            did_to_rkey = get_all_follow_records(client, self_did)

            for did in to_unfollow:
                rkey = did_to_rkey.get(did)
                if rkey:
                    try:
                        client.com.atproto.repo.delete_record(
                            data=models.ComAtprotoRepoDeleteRecord.Data(
                                repo=self_did,
                                collection="app.bsky.graph.follow",
                                rkey=rkey
                            )
                        )
                        logger.info(f"🔕 フォロー解除しました: {did}")
                    except Exception as e:
                        logger.error(f"❌ フォロー解除失敗: {did} - {e}")
                else:
                    logger.warning(f"⚠️ rkey取得失敗: {did}（uriが見つからない）")
        except Exception as e:
            logger.error(f"❌ フォロー解除全体で失敗: {e}")

    except Exception as e:
        logger.error(f"❌ フォロー管理全体でエラー: {e}")


if __name__ == "__main__":
    start()