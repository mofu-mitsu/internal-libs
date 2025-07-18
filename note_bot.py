from playwright.sync_api import sync_playwright
import time
import json

# スパムキーワード（競艇とか怪しいやつをブロック）
SPAM_KEYWORDS = ["ギャンブル", "賭博", "副業", "稼ぐ", "投資"]

def save_cookies(context, path="note_cookies.json"):
    """cookieを保存"""
    context.storage_state(path=path)
    print("✅ cookie保存完了！")

def load_cookies(context, path="note_cookies.json"):
    """cookieを読み込み"""
    try:
        context = context.new_context(storage_state=path)
        print("✅ cookie読み込み成功！")
        return context
    except Exception as e:
        print(f"❌ cookie読み込み失敗: {e}")
        return None

def get_following_list(page):
    """フォロー中のユーザー一覧を取得"""
    page.goto("https://note.com/following")
    page.wait_for_load_state("networkidle")
    users = page.query_selector_all(".o-userListItem__link")
    return [user.get_attribute("href").replace("/", "") for user in users]

def get_followers_list(page):
    """フォロワーのユーザー一覧を取得"""
    page.goto("https://note.com/followers")
    page.wait_for_load_state("networkidle")
    users = page.query_selector_all(".o-userListItem__link")
    return [user.get_attribute("href").replace("/", "") for user in users]

def note_auto_like_follow_back():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context = load_cookies(context) or context
        page = context.new_page()

        # 初回ログイン（必要なら）
        if not context.storage_state().get("cookies"):
            print("🔐 初回ログインが必要です！")
            page.goto("https://note.com/login")
            # 手動ログイン後、cookie保存（みつきがブラウザでログイン操作）
            input("ログインしたらEnter押してね！")
            save_cookies(context)

        # 通知チェック
        page.goto("https://note.com/notifications")
        page.wait_for_load_state("networkidle")
        notifications = page.query_selector_all(".o-notificationItem")
        actions_done = 0

        for note in notifications:
            if actions_done >= 10:  # 1日上限10件
                print("⏩ 上限到達、処理終了")
                break
            content = note.inner_text().lower()
            if any(kw.lower() in content for kw in SPAM_KEYWORDS):
                print(f"⏩ スパム通知スキップ: {content[:40]}")
                continue
            if "フォロー" in content:
                username = note.query_selector("a").get_attribute("href").replace("/", "")
                page.goto(f"https://note.com/{username}")
                if page.query_selector("button:has-text('フォロー中')"):
                    print(f"⏩ フォロー済み: {username}")
                    continue
                follow_btn = page.query_selector("button:has-text('フォロー')")
                if follow_btn:
                    follow_btn.click()
                    print(f"✅ フォロー返し: {username}")
                    actions_done += 1
                    time.sleep(2)
            elif "スキ" in content:
                username = note.query_selector("a").get_attribute("href").replace("/", "")
                page.goto(f"https://note.com/{username}")
                like_btn = page.query_selector("button:has-text('スキ')")
                if like_btn and not like_btn.get_attribute("disabled"):
                    like_btn.click()
                    print(f"❤️ いいね返し: {username}")
                    actions_done += 1
                    time.sleep(2)

        # フォロー解除チェック
        following = set(get_following_list(page))
        followers = set(get_followers_list(page))
        to_unfollow = following - followers
        for username in to_unfollow:
            if actions_done >= 10:
                print("⏩ 上限到達、解除処理終了")
                break
            page.goto(f"https://note.com/{username}")
            unfollow_btn = page.query_selector("button:has-text('フォロー中')")
            if unfollow_btn:
                unfollow_btn.click()
                print(f"🔕 フォロー解除: {username}")
                actions_done += 1
                time.sleep(2)

        save_cookies(context)
        browser.close()

if __name__ == "__main__":
    note_auto_like_follow_back()