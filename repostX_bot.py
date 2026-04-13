# repostX_bot.py
import os
import json
import subprocess
import time
import random
import re
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import urllib.parse
# ------------------------------
# 🔐 環境変数の読み込み
# ------------------------------
load_dotenv()
AUTH_TOKEN = os.getenv("AUTH_TOKEN") or exit("❌ AUTH_TOKENが設定されていません")
CT0 = os.getenv("CT0") or exit("❌ CT0が設定されていません")
GIST_TOKEN_REPLY = os.getenv("GIST_TOKEN_REPLY") or exit("❌ GIST_TOKEN_REPLYが設定されていません")
GIST_ID = os.getenv("GIST_ID") or exit("❌ GIST_IDが設定されていません")

# ------------------------------
# 📜 カスタマイズ＆設定値
# ------------------------------
# 履歴を保存するGist上のファイル名（リプ用とは分ける！）
REPOSTED_GIST_FILENAME = "reposted_x.json"
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"

# 1回の実行でリポストする最大件数（凍結防止のため少なめに！）
MAX_REPOSTS_PER_RUN = 3

TARGET_KEYWORDS = [
    '#オリキャラプロフィールメーカー', '#ふわふわ相性診断', '#推しプロフィールメーカー', 
    '#もふみつ工房', '#みりんてゃ', '#みりんてゃbot', '#チャッピー供養ギャラリー', 
    '#みりんてゃーと', '#とりの丘文画部',
]

REPOST_COMMENTS = [
    "キラキラ✨ みりんてゃ推しなのっ♡",
    "ふわふわ〜！これ超かわいいなのっ♪",
    "えへ〜♪ 君の投稿、めっちゃ好きだよ♡",
    "ぎゅっ♡ このポスト、みりんてゃのお気に入り！",
    "これ見てニコニコしちゃったぁ〜🎀>  ̫ <🎀",
    "キミのセンス、バチバチに光ってるぅ✨✨",
    "だいすきっ♡ もっかい読んじゃったのっ！",
    "ぎゃ〜〜！最高すぎてみりんてゃ昇天✝️♡",
    "尊すぎて語彙力とけた...ふにゃあ〜〜〜〜(꒪꒳꒪ )",
    "これ、みりんてゃの心にずきゅんだよ(ˆ⩌⩊⩌ˆ)💘★"
]

def random_sleep(min_sec=3, max_sec=10):
    time.sleep(random.randint(min_sec, max_sec))

# ------------------------------
# 📁 Gist履歴管理（リプBotと同じ仕組み）
# ------------------------------
def load_reposted_history():
    print(f"🌐 Gistからリポスト履歴を読み込みます...")
    try:
        curl_command = ["curl", "-X", "GET", GIST_API_URL, "-H", f"Authorization: token {GIST_TOKEN_REPLY}", "-H", "Accept: application/vnd.github+json"]
        result = subprocess.run(curl_command, capture_output=True, text=True)
        if result.returncode == 0:
            gist_data = json.loads(result.stdout)
            if REPOSTED_GIST_FILENAME in gist_data["files"]:
                return set(json.loads(gist_data["files"][REPOSTED_GIST_FILENAME]["content"]))
    except Exception as e:
        print(f"⚠️ 履歴読み込みエラー: {e}")
    return set()

def save_reposted_history(history_set):
    print(f"💾 リポスト履歴をGistに保存します...")
    try:
        payload = {"files": {REPOSTED_GIST_FILENAME: {"content": json.dumps(list(history_set), ensure_ascii=False, indent=2)}}}
        curl_command = ["curl", "-X", "PATCH", GIST_API_URL, "-H", f"Authorization: token {GIST_TOKEN_REPLY}", "-H", "Accept: application/vnd.github+json", "-H", "Content-Type: application/json", "-d", json.dumps(payload, ensure_ascii=False)]
        result = subprocess.run(curl_command, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 履歴の保存完了！")
    except Exception as e:
        print(f"⚠️ 履歴保存エラー: {e}")

# ------------------------------
# 🔄 Xでの検索＆リポスト処理
# ------------------------------
def get_target_tweets(page):
    """キーワードでOR検索して、最新のツイートURLを拾ってくる"""
    print("🔍 Xの検索画面を確認中...")
    
    # キーワードを「OR」で繋いで一網打尽にする！
    search_query = " OR ".join(TARGET_KEYWORDS)
    encoded_query = urllib.parse.quote(search_query)
    
    # f=live で「最新順」のタブを表示
    page.goto(f"https://x.com/search?q={encoded_query}&f=live")
    page.wait_for_timeout(5000)

    tweets = page.locator('article[data-testid="tweet"]').all()
    found_urls = []
    
    for tweet in tweets[:10]: # 上から10件を確認
        try:
            time_element = tweet.locator('a[href*="/status/"]').first
            url = "https://x.com" + time_element.get_attribute("href")
            found_urls.append(url)
        except:
            continue
            
    return found_urls

def do_repost(page, url, is_quote=False):
    """ツイートをリポスト（または引用リポスト）する"""
    if is_quote:
        # 💬 【引用リポスト】自分のタイムラインにURL付きで投稿する（これが一番確実）
        comment = random.choice(REPOST_COMMENTS)
        post_text = f"{comment}\n\n{url}"
        print(f"📬 引用リポストするよ: {comment}")
        
        page.goto("https://x.com/compose/post")
        page.wait_for_timeout(4000)
        page.fill('div[data-testid="tweetTextarea_0"]', post_text)
        random_sleep(2, 4)
        page.keyboard.press("Control+Enter")
        page.wait_for_timeout(5000)
    else:
        # 🔄 【通常リポスト】対象のツイート画面に行ってRTボタンを押す
        print(f"🔄 通常リポストするよ: {url}")
        page.goto(url)
        page.wait_for_timeout(5000)
        
        # リツイートボタンを探す
        retweet_btn = page.locator('button[data-testid="retweet"]').first
        if retweet_btn.count() > 0:
            retweet_btn.click(force=True)
            random_sleep(1, 3)
            # 確認メニューの「リポスト」を押す
            confirm_btn = page.locator('div[data-testid="retweetConfirm"]').first
            confirm_btn.click(force=True)
            page.wait_for_timeout(3000)
        else:
            print("⚠️ リポストボタンが見つからなかった（すでにRT済みかも？）")

def main():
    print("🚀 りぽりんBot（X版）起動しました！")
    
    reposted_history = load_reposted_history()
    repost_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_cookies([
            {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/"}
        ])
        
        page = context.new_page()
        # 🧙‍♂️ ステルス魔法（ロボットですよっていう証拠を消し去る！）
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            # ツイートを拾ってくる
            tweet_urls = get_target_tweets(page)
            print(f"🎯 検索結果から {len(tweet_urls)} 件の対象を発見！")

            for url in tweet_urls:
                if repost_count >= MAX_REPOSTS_PER_RUN:
                    print(f"⏹️ 最大件数（{MAX_REPOSTS_PER_RUN}件）に達したから終了するね！")
                    break
                    
                if url in reposted_history:
                    print(f"⏩ スキップ（すでに履歴あり）: {url}")
                    continue

                # 50%の確率で引用リポストか通常リポストかを決める
                is_quote = random.random() < 0.5
                do_repost(page, url, is_quote=is_quote)

                # 履歴に追加して保存
                reposted_history.add(url)
                save_reposted_history(reposted_history)
                repost_count += 1
                
                # 人間っぽく待機
                print("ロボット避けの待機中...☕️")
                random_sleep(15, 30)

            print(f"✨ 実行完了: 今回は {repost_count} 件リポストしたよ！ ✨")

        except Exception as e:
            print(f"❌ エラー起きちゃった…ぴえん🥺\n{e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
