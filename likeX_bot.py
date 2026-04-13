import os
import random
import time
import urllib.parse                # 👈 検索ワードの変換に必要！
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# 1. まず先に「箱（.env）」を開ける！
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# 2. そのあとで中身を取り出す！
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
CT0 = os.getenv('CT0')

# みりんてゃのターゲットキーワード
TARGET_KEYWORDS = [
    '地雷女', '病み垢', '病みかわ', 'メンヘラ', '量産系', 
    'みりんてゃ', 'みりんてゃーと', 'とりの丘文画部',
    '地雷', '量産', '病み', '可愛い', 'かわいい', 'bot', 'Bot', 'AI',
    '猫', 'ねこ', '相性診断', 'オリキャラ', '推し', 'jirai',
    '創作', 'オリジナル', 'イラスト', 'プロフィールメーカー', 'チャッピー供養ギャラリー','とりの丘',
]

MAX_LIKES_PER_RUN = 5

def random_sleep(min_sec=3, max_sec=10):
    time.sleep(random.randint(min_sec, max_sec))

def human_like_scroll(page):
    print("👀 人間っぽく画面をスクロールして読んでるフリをするよ…")
    for _ in range(3):
        page.mouse.wheel(0, random.randint(300, 800))
        random_sleep(2, 5)

def like_tweets_on_page(page, max_likes):
    liked_count = 0
    like_button_selector = 'button[data-testid="like"]'
    
    # 画面上のいいねボタンを探す
    like_buttons = page.locator(like_button_selector).all()
    print(f"🔍 画面上に {len(like_buttons)} 件の未いいね投稿を発見！")
    
    for button in like_buttons:
        if liked_count >= max_likes:
            break
        try:
            button.scroll_into_view_if_needed()
            random_sleep(2, 4)
            button.click(force=True)
            print("❤️ いいねしたよ！")
            liked_count += 1
            random_sleep(5, 15)
        except Exception as e:
            print(f"⚠️ スキップ: {e}")
            continue
    return liked_count

def main():
    if not AUTH_TOKEN or not CT0:
        print("エラー：AUTH_TOKEN または CT0 が見つからないよ！ぴえん！")
        return

    print("🚀 みりんてゃの LikeBot 起動！")
    total_liked = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])
        page = context.new_page()
        # ステルス魔法
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            # ミッション1：キーワード検索
            keyword = random.choice(TARGET_KEYWORDS)
            # 👈 キーワードをURL用に変換する処理を追加！
            encoded_keyword = urllib.parse.quote(keyword)
            print(f"🔍 今日の検索キーワード: {keyword}")
            
            search_url = f"https://x.com/search?q={encoded_keyword}&f=live"
            page.goto(search_url)
            page.wait_for_timeout(7000)
            
            human_like_scroll(page)
            total_liked += like_tweets_on_page(page, MAX_LIKES_PER_RUN)
            
            # ミッション2：通知欄
            if total_liked < MAX_LIKES_PER_RUN:
                print("🔔 通知欄（リプやメンション）を見に行くよ！")
                page.goto("https://x.com/notifications/mentions")
                page.wait_for_timeout(7000)
                total_liked += like_tweets_on_page(page, 3)

            print(f"✅ 実行完了: 今日は {total_liked} 件の愛を振りまいたよ♡")

        except Exception as e:
            print(f"❌ エラー起きちゃった…ぴえん🥺\n{e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
