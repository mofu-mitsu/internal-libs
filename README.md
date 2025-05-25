# 🌟 みりんてゃBotキット ♡ ふwaふwaリプBotを作ろう！

みりんてゃが「えへへ〜♡ ドキドキなのっ♪」ってリプしてくれるBluesky Bot！このキットで君だけのBotをカスタム💖

## ❓ よくある質問（FAQ）

### Q. セットアップがうまくいきません
A. Python 3.10とライブラリをインストールしてください。`pip install -r requirements.txt`を試して！
→ 詳しくは[セットアップガイド](#setup-guide)

### Q. エラー「ModuleNotFoundError」が出ました
A. 必要なライブラリが足りません。`requirements.txt`を確認し、`pip install -r requirements.txt`を実行。

### Q. 「GIST_TOKEN_REPLYが見つかりません」と表示されます
A. GitHub Secretsや`.env`に`GIST_TOKEN_REPLY`を正しく設定してください。
→ 詳しくは[GitHub Secrets設定](#secrets-guide)

### Q. Botの名前や口調を変更したい
A. `reply_bot.py`の`BOT_NAME`や`FIRST_PERSON`を編集！
→ 例は[カスタマイズガイド](#customization-guide)

### Q. リプが来ません
A. ログを確認！「⚠️ スキップ」が出てるなら、メンション（`@your_handle`）やBlueskyの通知をチェック。
→ 詳しくは[Wiki: エラー対処](https://github.com/your_username/mirintya-bot/wiki/Troubleshooting)

### Q. 問題が解決しない場合は？
A. [カスタマーサポート](#customer-support)へ！GoogleフォームやXのDMで気軽にどうぞ♡

## 📚 もっと知りたい？
詳細なFAQやカスタマイズ例は[Wiki](https://github.com/your_username/mirintya-bot/wiki)へ！
