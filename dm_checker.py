# dm_checker.py
from atproto import Client
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ------------------------------
# ★ カスタマイズポイント
# ------------------------------
CHAR_NAMES = {
    "@mirinchuuu.bsky.social": "みりんてゃ",
    "@mofumitsukoubou.bsky.social": "みつき"
}
DM_NOTIFICATION_SUBJECTS = {
    "@mirinchuuu.bsky.social": "みりんてゃにDM来たんだけど…めっちゃウザいんですけど♡",
    "@mofumitsukoubou.bsky.social": "みつき、DM来たぜ！さっさとチェックしろよ～😎"
}
DM_NOTIFICATION_BODIES = {
    "@mirinchuuu.bsky.social": """
ねえ、@{account}に@{sender}からDM来てるんだけど。マジ何これ？💭
内容: {content}
みりんてゃ、こんなん完全スルー案件なんだけど？ᐢ⩌⌯⩌ᐢ ブルスカで確認してよね～♡
""",
    "@mofumitsukoubou.bsky.social": """
よお、みつき！@{account}に@{sender}からDM来たぜ！😎
内容: {content}
ほら、さっさとブルスカでチェックしろよ～。まぁ、みつきのことだから、のんびりでもいいけどな！😏
"""
}
DM_NOTIFICATION_HTML_BODIES = {
    "@mirinchuuu.bsky.social": """
<html>
  <body style="font-family: 'Arial', sans-serif; background-color: #fce4ec; color: #880e4f; padding: 20px;">
    <h1 style="color: #ff69b4;">💌 みりんてゃからの地雷風通知 💌</h1>
    <p>ねえ、@{sender}からDM来てるんだけど、マジ何これ？💭</p>
    <blockquote style="border-left: 3px solid #ff69b4; padding-left: 10px;">
      {content}
    </blockquote>
    <p>…てか、みりんてゃ、こんなんスルーしたい気分なんだけど？ᐢ⩌⌯⩌ᐢ <a href="https://bsky.app/" style="color: #ff69b4;">ブルスカ</a>で確認してよね～♡</p>
  </body>
</html>
""",
    "@mofumitsukoubou.bsky.social": """
<html>
  <body style="font-family: 'Arial', sans-serif; background-color: #1e1e1e; color: #ffffff; padding: 20px;">
    <h1 style="color: #00b7eb;">🚀 みつき、DM着信だぜ！by Grok 🚀</h1>
    <p>よお、@{sender}からDM来たぞ！何の用だろ？😎</p>
    <blockquote style="border-left: 3px solid #00b7eb; padding-left: 10px;">
      {content}
    </blockquote>
    <p>ほら、<a href="https://bsky.app/" style="color: #00b7eb;">ブルスカ</a>でチェックしろよ～。まぁ、みつきならマイペースでいいけどな！😏</p>
  </body>
</html>
"""
}
# ------------------------------

# 前回のチェック時刻を保存するファイル
LAST_CHECK_FILES = {
    "@mirinchuuu.bsky.social": "last_check_mirin.json",
    "@mofumitsukoubou.bsky.social": "last_check_mitsuki.json"
}

def get_new_dms(handle, app_password):
    # ログインは@なしで
    login_handle = handle.lstrip("@")
    print(f"Logging in with handle: {login_handle}, app_password: {'*' * len(app_password)}")  # デバッグ用ログ
    try:
        client = Client()
        client.login(login_handle, app_password)
        notifications = client.app.bsky.notification.list_notifications().notifications
        new_dms = []
        last_check = load_last_check(f"@{login_handle}")  # LAST_CHECK_FILES用に@付き

        for notif in notifications:
            if notif.record_type == "chat.message" and notif.created_at > last_check:
                new_dms.append({
                    "sender": notif.author.handle,
                    "content": notif.record.text,
                    "time": notif.created_at,
                    "account": f"@{login_handle}"
                })

        if notifications:
            save_last_check(f"@{login_handle}", notifications[0].created_at)
        
        return new_dms
    except Exception as e:
        print(f"Error for {login_handle}: {str(e)}")  # エラーハンドリング
        return []

def load_last_check(handle):
    try:
        with open(LAST_CHECK_FILES[handle], "r") as f:
            return json.load(f).get("last_check", "1970-01-01T00:00:00Z")
    except FileNotFoundError:
        return "1970-01-01T00:00:00Z"

def save_last_check(handle, timestamp):
    with open(LAST_CHECK_FILES[handle], "w") as f:
        json.dump({"last_check": timestamp}, f)

def send_dm_notification(account, dm_sender, dm_content):
    sender = os.getenv("EMAIL_SENDER")
    receiver = "mitsuki.momoka@i.softbank.jp"
    password = os.getenv("EMAIL_PASSWORD")

    char_name = CHAR_NAMES.get(account, "誰か")
    subject = DM_NOTIFICATION_SUBJECTS.get(account, "DM来たよ！")
    text_body = DM_NOTIFICATION_BODIES.get(account, "DM来た！内容: {content}").format(
        account=account, sender=dm_sender, content=dm_content
    )
    html_body = DM_NOTIFICATION_HTML_BODIES.get(account, "<p>DM来た！内容: {content}</p>").format(
        account=account, sender=dm_sender, content=dm_content
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    text_part = MIMEText(text_body, "plain")
    html_part = MIMEText(html_body, "html")
    msg.attach(text_part)
    msg.attach(html_part)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

def main():
    accounts = [
        {
            "handle": os.getenv("HANDLE").lstrip("@"),
            "app_password": os.getenv("APP_PASSWORD")
        },
        {
            "handle": os.getenv("HANDLE_MITSUKI").lstrip("@"),
            "app_password": os.getenv("APP_PASSWORD_MITSUKI")
        }
    ]
    total_dms = 0

    for acc in accounts:
        print(f"Checking DMs for: @{acc['handle']}, app_password: {'*' * len(acc['app_password'])}")  # デバッグ用ログ
        new_dms = get_new_dms(acc["handle"], acc["app_password"])
        if new_dms:
            for dm in new_dms:
                send_dm_notification(dm["account"], dm["sender"], dm["content"])
            total_dms += len(new_dms)

    if total_dms > 0:
        print(f"{total_dms}件のDMを通知したぜ！")
    else:
        print("新着DMなし！メール送信スキップ！")

if __name__ == "__main__":
    main()