# dm_checker.py
from atproto import Client
import json
import os
import smtplib
from email.mime.text import MIMEText

# ------------------------------
# ★ カスタマイズポイント
# ------------------------------
# メールの文面をキャラに合わせて変更可能！
DM_NOTIFICATION_SUBJECT = "みりんてゃにDM来たんだけど…めっちゃウザいんですけど♡"
DM_NOTIFICATION_BODY = """
ねえ、@{sender}からDM来てるよ。マジ何？
内容: {content}

…てか、みりん、こんなん返事する気分じゃないかも？
ブルスカで確認してよね～、ほんとめんどいんだけど♡
"""
# ------------------------------

# 前回のチェック時刻を保存するファイル
LAST_CHECK_FILE = "last_check.json"

def get_new_dms():
    client = Client()
    client.login(os.getenv("HANDLE"), os.getenv("APP_PASSWORD"))
    notifications = client.app.bsky.notification.list_notifications().notifications
    new_dms = []
    last_check = load_last_check()

    for notif in notifications:
        if notif.record_type == "chat.message" and notif.created_at > last_check:
            new_dms.append({
                "sender": notif.author.handle,
                "content": notif.record.text,
                "time": notif.created_at
            })

    if notifications:
        save_last_check(notifications[0].created_at)
    
    return new_dms

def load_last_check():
    try:
        with open(LAST_CHECK_FILE, "r") as f:
            return json.load(f).get("last_check", "1970-01-01T00:00:00Z")
    except FileNotFoundError:
        return "1970-01-01T00:00:00Z"

def save_last_check(timestamp):
    with open(LAST_CHECK_FILE, "w") as f:
        json.dump({"last_check": timestamp}, f)

def send_dm_notification(dm_sender, dm_content):
    sender = os.getenv("EMAIL_SENDER")
    receiver = "mitsuki.momoka@i.softbank.jp"
    password = os.getenv("EMAIL_PASSWORD")

    msg = MIMEText(DM_NOTIFICATION_BODY.format(sender=dm_sender, content=dm_content))
    msg["Subject"] = DM_NOTIFICATION_SUBJECT
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.mail.yahoo.co.jp", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

def main():
    new_dms = get_new_dms()
    if new_dms:
        for dm in new_dms:
            send_dm_notification(dm["sender"], dm["content"])
        print(f"{len(new_dms)}件のDMを通知したぜ！")
    else:
        print("新着DMなし！メール送信スキップ！")

if __name__ == "__main__":
    main()