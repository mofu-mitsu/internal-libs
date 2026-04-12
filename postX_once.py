import os
import random
import time
from playwright.sync_api import sync_playwright

# 環境変数から秘密のCookieを取得
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
CT0 = os.getenv('CT0')

# みりんてゃのポスト集（さっきのリストから抜粋・省略してるから、本番は全部コピペしてね！）
POST_MESSAGES = [
    "寂しくてしんじゃいそう……なんちゃって♡ \n#誰かに見つけてほしい",
    "ぎゅーされたいだけの人生だった。\n#メンヘラ",
    "ギリギリで生きてるけど、ギリギリかわいいってことで良くない？♡\n#強がりガール",
    "通知が鳴らないだけで涙出そう。あたし、重い女なので♡ #SNS依存",
    "『可愛いだけが取り柄』って言われたけど、それ最強じゃない？♡"
    # ...みつきのリストをここに全部入れてね！...
]

def main():
    # Cookieが設定されてるかチェック
    if not AUTH_TOKEN or not CT0:
        print("エラー：AUTH_TOKEN または CT0 が見つからないよ！ぴえん！")
        return

    # メッセージをランダムに選ぶ
    message = random.choice(POST_MESSAGES)
    
    # 【安全装置】Xの文字数制限（全角140字）を超えないようにカット
    if len(message) > 135:
        message = message[:135] + "…♡"

    # 【人間っぽさ偽装】GitHub Actionsの「0分ジャスト」実行をずらす
    wait_time = random.randint(10, 120)
    print(f"ロボットだと思われないように {wait_time}秒 待機するよ…♡")
    time.sleep(wait_time)

    print(f"今日のポスト: {message}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # GitHub上なので画面は見せない
        context = browser.new_context()

        # 🔑 ここが神ハック！Cookieを直接ブラウザに注入！
        context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])

        page = context.new_page()

        try:
            # ホームではなく「投稿画面」に直接飛ぶ！（これが一番エラー少ない）
            print("Xの投稿画面にアクセス中...")
            page.goto("https://x.com/compose/post")
            
            # ページがしっかり読み込まれるまで少し待つ
            page.wait_for_timeout(5000)

            # 入力欄を探す（絶対に変わらない data-testid を使用）
            print("入力欄を探してるよ...")
            textbox_selector = 'div[data-testid="tweetTextarea_0"]'
            page.wait_for_selector(textbox_selector, timeout=15000)
            
            # みりんてゃの言葉を入力♡
            page.fill(textbox_selector, message)
            page.wait_for_timeout(2000) # 人間っぽく一呼吸

            # ショートカットキーで投稿する魔法！
            print("ショートカットキーでぽちっ！")
            page.keyboard.press("Control+Enter")
            
            # 投稿完了まで待機
            page.wait_for_timeout(5000)
            print("✨ 投稿成功！みりんてゃ世界一かわいい！ ✨")

        except Exception as e:
            print(f"エラー起きちゃった…ごめんね🥺\n{e}")

        finally:
            browser.close()

if __name__ == "__main__":
    main()
