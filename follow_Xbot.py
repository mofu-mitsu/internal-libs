# follow_Xbot.py
import os
import random
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
HANDLE = os.getenv("HANDLE") or exit("❌ HANDLEが設定されていません")
AUTH_TOKEN = os.getenv("AUTH_TOKEN") or exit("❌ AUTH_TOKENが設定されていません")
CT0 = os.getenv("CT0") or exit("❌ CT0が設定されていません")

# Xのハンドル名から @ を消しておく
CLEAN_HANDLE = HANDLE.replace("@", "")

# 1回の実行での最大処理人数（凍結対策で極限まで少なく！）
MAX_ACTIONS = 3

def random_sleep(min_sec=2, max_sec=7):
    """人間っぽく待機する"""
    time.sleep(random.randint(min_sec, max_sec))

# ----------------------------------------------------
# 🛡️ 誤爆回避！最強の怪しいアカウント判定ロジック
# ----------------------------------------------------
def is_suspicious_user(profile_text):
    text = profile_text.lower()
    
    # 【ステップ1】セーフフレーズ（これがあれば許す言葉）を文章から消し去る！
    safe_phrases = ["裏垢お断り", "裏垢ng", "裏垢✖", "エロ垢お断り", "副業お断り", "副業ng", "スパムお断り"]
    for phrase in safe_phrases:
        text = text.replace(phrase.lower(), "")
        
    # 【ステップ2】残った文章の中にNGワードがないかチェックする！
    ng_words = ["裏垢", "稼げる", "副業", "援交", "エロ", "パパ活", "マン凸", "プロフ見て", "固ツイ見て", "現金プレゼント"]
    for word in ng_words:
        if word.lower() in text:
            print(f"🚨 NGワード「{word}」を検知しました！")
            return True # 怪しいアカウント！
            
    return False # 健全アカウント！

# ----------------------------------------------------
# 🔄 フォロー・フォロワー管理メイン処理
# ----------------------------------------------------
def process_follows(page):
    action_count = 0
    
    print("👀 フォロワー一覧を見に行くよ！")
    page.goto(f"https://x.com/{CLEAN_HANDLE}/followers")
    page.wait_for_timeout(5000)

    # 画面上のユーザーセルを取得
    user_cells = page.locator('button[data-testid^="UserCell"]').all()
    
    for cell in user_cells:
        if action_count >= MAX_ACTIONS:
            break
            
        try:
            # 「フォローする (Follow)」ボタンがあるかチェック（未フォロバの相手）
            follow_button = cell.locator('button[data-testid$="-follow"]').first
            
            if follow_button.count() > 0 and follow_button.is_visible():
                # アカウントのハンドル（@xxx）を取得
                handle_element = cell.locator('div[dir="ltr"]').filter(has_text="@").first
                target_handle = handle_element.inner_text().replace("@", "")
                
                print(f"👤 フォロバ候補を発見！: @{target_handle}")
                
                # --- プロフィール画面へ飛んで自己紹介文をチェック！ ---
                page.goto(f"https://x.com/{target_handle}")
                page.wait_for_timeout(4000)
                
                # 自己紹介文の取得
                bio_locator = page.locator('div[data-testid="UserDescription"]')
                bio_text = bio_locator.inner_text() if bio_locator.count() > 0 else ""
                
                # 名前の取得
                name_locator = page.locator('div[data-testid="UserName"]')
                name_text = name_locator.inner_text() if name_locator.count() > 0 else ""
                
                full_profile_text = name_text + " " + bio_text
                
                if is_suspicious_user(full_profile_text):
                    print(f"⚠️ 怪しいアカウントをスキップしたよ: @{target_handle}")
                else:
                    # 健全ならフォローボタンを押す！
                    profile_follow_btn = page.locator('button[data-testid$="-follow"]').first
                    if profile_follow_btn.count() > 0:
                        profile_follow_btn.click(force=True)
                        print(f"✅ フォロバ完了！: @{target_handle}")
                        action_count += 1
                
                # リスト画面に戻る
                page.goto(f"https://x.com/{CLEAN_HANDLE}/followers")
                random_sleep(5, 10)
                
        except Exception as e:
            print(f"⚠️ 処理中にエラー（スキップ）: {e}")
            continue

    return action_count

def process_unfollows(page):
    action_count = 0
    
    print("👀 フォロー中一覧を見に行くよ（片思い解除チェック）！")
    page.goto(f"https://x.com/{CLEAN_HANDLE}/following")
    page.wait_for_timeout(5000)

    # 画面上のユーザーセルを取得
    user_cells = page.locator('button[data-testid^="UserCell"]').all()
    
    for cell in user_cells:
        if action_count >= MAX_ACTIONS:
            break
            
        try:
            # 相手が自分をフォローしているか（「フォローされています」のバッジがあるか）チェック
            follows_you_badge = cell.locator('text="フォローされています"').count() > 0 or cell.locator('text="Follows you"').count() > 0
            
            if not follows_you_badge:
                # バッジがない＝片思い状態！アンフォローする
                handle_element = cell.locator('div[dir="ltr"]').filter(has_text="@").first
                target_handle = handle_element.inner_text().replace("@", "") if handle_element.count() > 0 else "不明"
                
                unfollow_button = cell.locator('button[data-testid$="-unfollow"]').first
                if unfollow_button.count() > 0 and unfollow_button.is_visible():
                    # アンフォローボタンを押すと確認ポップアップが出る
                    unfollow_button.click(force=True)
                    random_sleep(1, 3)
                    
                    # ポップアップの「フォロー解除 (Unfollow)」ボタンを押す
                    confirm_btn = page.locator('button[data-testid="confirmationSheetConfirm"]')
                    if confirm_btn.count() > 0:
                        confirm_btn.click(force=True)
                        print(f"🔕 リムバ（片思い解除）したよ: @{target_handle}")
                        action_count += 1
                        random_sleep(5, 15)
                        
        except Exception as e:
            print(f"⚠️ 解除処理中にエラー（スキップ）: {e}")
            continue

def main():
    print("🤝 フォロー管理開始！みりんてゃを守るぜ！")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 🔑 Cookie注入
        context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])
        
        page = context.new_page()
        # 🧙‍♂️ ステルス魔法（ロボットですよっていう証拠を消し去る！）
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            # 1. フォロバ処理
            process_follows(page)
            
            # 人間っぽく大きく待機
            random_sleep(15, 30)
            
            # 2. リムバ（片思い解除）処理
            process_unfollows(page)

            print("✨ 今日のフォロー管理おわりっ！ ✨")
            
        except Exception as e:
            print(f"エラー起きちゃった…🥺\n{e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
