import os
import random
import time
from playwright.sync_api import sync_playwright

# 環境変数から秘密のCookieを取得
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
CT0 = os.getenv('CT0')

# みりんてゃのターゲットキーワード（ハッシュタグ含む）
TARGET_KEYWORDS = [
    '地雷女', '病み垢', '病みかわ', 'メンヘラ', '量産系', 
    'みりんてゃ', 'みりんてゃーと', 'とりの丘文画部'
    '地雷', '量産', '病み', '可愛い', 'かわいい', 'bot', 'Bot', 'AI',
    '猫', 'ねこ', '相性診断', 'オリキャラ', '推し', 'jirai',
    '創作', 'オリジナル', 'イラスト', 'プロフィールメーカー', 'チャッピー供養ギャラリー','とりの丘',
]

# 1回の実行でいいねする最大件数（安全第一！）
MAX_LIKES_PER_RUN = 5

def random_sleep(min_sec=3, max_sec=10):
    """人間っぽく待機する関数"""
    time.sleep(random.randint(min_sec, max_sec))

def human_like_scroll(page):
    """人間っぽくスクロールして読んでるフリ"""
    print("👀 人間っぽく画面をスクロールして読んでるフリをするよ…")
    
    for _ in range(3):
        page.mouse.wheel(0, random.randint(300, 800))
        random_sleep(2, 5)
def like_tweets_on_page(page, max_likes):
    """開いているページ上のいいねボタンを探して押す"""
    liked_count = 0
    # Xのいいねボタン（まだ押されていないハート）の指定
    like_button_selector = 'button[data-testid="like"]'
    
    # 画面上にあるいいねボタンをすべて取得
    like_buttons = page.locator(like_button_selector).all()
    
    for button in like_buttons:
        if liked_count >= max_likes:
            break
            
        try:
            # 画面内にスクロールして見せる
            button.scroll_into_view_if_needed()
            random_sleep(1, 3)
            
            # いいねを押す！
            button.click(force=True)
            print("❤️ いいねしたよ！")
            liked_count += 1
            
            # 連続で押さないように長めに待機
            random_sleep(5, 15)
            
        except Exception as e:
            print(f"⚠️ いいね失敗（スキップするね）: {e}")
            continue
            
    return liked_count

def main():
    if not AUTH_TOKEN or not CT0:
        print("エラー：AUTH_TOKEN または CT0 がないよ！")
        return

    print("🚀 みりんてゃの LikeBot 起動！")
    total_liked = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])
        page = context.new_page()

        try:
            # ------------------------------------------------
            # ミッション1：キーワード検索していいね！
            # ------------------------------------------------
            keyword = random.choice(TARGET_KEYWORDS)
            print(f"🔍 今日の検索キーワード: {keyword}")
            
            # 検索画面（最新順）にアクセス
            search_url = f"https://x.com/search?q={keyword}&f=live"
            page.goto(search_url)
            page.wait_for_timeout(5000)
            
            print("検索結果の投稿にいいねしていくよ！")
            likes_from_search = like_tweets_on_page(page, MAX_LIKES_PER_RUN)
            total_liked += likes_from_search
            
            # ------------------------------------------------
            # ミッション2：通知欄（メンション・リプ）にいいね！
            # ------------------------------------------------
            if total_liked < (MAX_LIKES_PER_RUN * 2): # まだ余裕があれば
                print("🔔 通知欄（リプやメンション）を見に行くよ！")
                page.goto("https://x.com/notifications/mentions")
                page.wait_for_timeout(5000)
                
                likes_from_mentions = like_tweets_on_page(page, 3) # メンションは最大3件
                total_liked += likes_from_mentions

            print(f"✅ 実行完了: 今日は {total_liked} 件の愛を振りまいたよ♡")

        except Exception as e:
            print(f"エラー起きちゃった…ぴえん🥺\n{e}")

        finally:
            browser.close()

if __name__ == "__main__":
    main()
