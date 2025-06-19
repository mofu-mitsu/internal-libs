# dm_checker.py
from atproto import Client
import json
import os
import smtplib
import requests
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
    <p>ほら, <a href="https://bsky.app/" style="color: #00b7eb;">ブルスカ</a>でチェックしろよ～。まぁ、みつきならマイペースでいいけどな！😏</p>
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
    login_handle = handle.lstrip("@")
    print(f"Logging in with handle: {login_handle}, app_password: {'*' * len(app_password)}")  # デバッグ用ログ
    try:
        client = Client()
        client.login(login_handle, app_password)
        # 通知APIで全応答確認
        notifications = client.app.bsky.notification.list_notifications().notifications
        print(f"🔍 Available bsky methods: {dir(client.app.bsky)}")  # デバッグ: 利用可能メソッド
        print(f"🔍 Full notification response: {json.dumps(notifications, indent=2, default=str)}")  # 全応答ログ
        new_dms = []
        last_check = load_last_check(f"@{login_handle}")

        for notif in notifications:
            print(f"🔍 Notification dict: {json.dumps(notif.__dict__, indent=2, default=str)}")
            print(f"🔍 Record dict: {json.dumps(notif.record.__dict__ if hasattr(notif, 'record') else {}, indent=2, default=str)}")
            record_type = getattr(notif.record, "$type", "") if hasattr(notif, "record") else ""
            record_text = getattr(notif.record, "text", "") if hasattr(notif, "record") else ""
            indexed_at = notif.__dict__.get("indexedAt", "")
            print(f"🔍 record type: {record_type}, content: {record_text}, indexed_at: {indexed_at}")
            if record_type == "app.bsky.chat.message" and indexed_at and indexed_at > last_check:
                new_dms.append({
                    "sender": notif.author.handle,
                    "content": record_text,
                    "time": indexed_at,
                    "account": f"@{login_handle}"
                })

        # チャットAPIをHTTPで直接試行
        headers = {"Authorization": f"Bearer {client.session.get('accessJwt')}"}
        chat_response = requests.get("https://bsky.social/xrpc/app.bsky.chat.listMessages", headers=headers)
        print(f"🔍 Chat API response: {json.dumps(chat_response.json(), indent=2)}")
        if chat_response.status_code == 200:
            messages = chat_response.json().get("messages", [])
            for message in messages:
                message_type = message.get("$type", "")
                message_text = message.get("content", {}).get("text", "")
                message_time = message.get("createdAt", "")
                sender_handle = message.get("sender", {}).get("handle", "")
                print(f"🔍 message type: {message_type}, content: {message_text}, time: {message_time}, sender: {sender_handle}")
                if message_type == "app.bsky.chat.message" and message_time and message_time > last_check:
                    new_dms.append({
                        "sender": sender_handle,
                        "content": message_text,
                        "time": message_time,
                        "account": f"@{login_handle}"
                    })

        if notifications or messages:
            first_time = (notifications[0].__dict__.get("indexedAt", "") if notifications else
                         messages[0].get("createdAt", "")) if notifications or messages else ""
            if first_time:
                save_last_check(f"@{login_handle}", first_time)
        
        return new_dms
    except Exception as e:
        print(f"Error for {login_handle}: {str(e)}")
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
        print(f"Checking DMs for: @{acc['handle']}, app_password: {'*' * len(acc['app_password'])}")
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