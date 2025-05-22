import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.environ["GIST_TOKEN_REPLY"]
gist_id = "40391085a2e0b8a48935ad0b460cf422"
url = f"https://api.github.com/gists/{gist_id}"

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

# 書き込みテスト：hello.json に簡単な内容を書き込む
data = {
    "files": {
        "hello.json": {
            "content": "👋 これは書き込みテストです！"
        }
    }
}

res = requests.patch(url, headers=headers, json=data)
print("📡 STATUS:", res.status_code)
print(res.text)