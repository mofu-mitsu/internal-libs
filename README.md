# 🌟 みりんてゃBot Starter Kit

みりんてゃが「えへへ〜♡ ドキドキなのっ♪」ってリプしてくれるBluesky Bot！このキットで君だけのBotをカスタム💖

---

## ❓ よくある質問（FAQ）

### Q. セットアップがうまくいきません
A. Pythonと必要なライブラリがインストールされているか確認してみてください。  
→ 詳しくは[wikiへ](https://github.com/mofu-mitsu/mirin_bot_once/wiki/Setup-Guide)

### Q. GIST_TOKEN_REPLYが見つかりません
A. GitHub Secretsに正しく登録されているか確認してください。  
→ [Secrets設定ガイド](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

### Q. Botの名前を変更したい
A. `reply_bot.py`の「★ カスタマイズポイント ★」を編集してください。  
→ 詳しくは[wikiへ](https://github.com/mofu-mitsu/mirin_bot_once/wiki/Setup-Guide)

---

## 🛠️ セットアップ手順

1. 必要なファイルをリポジトリに配置します：
   - `reply_bot.py`
   - `.env`
   - `requirements.txt`
   - `.github/workflows/reply_bot.yml`

2. 必要なアカウントとキーを取得します：
   - **GitHub Secrets**：[Managing Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
   - **Bluesky APIキー**：[Blueskyの設定ガイドはこちら](https://github.com/mofu-mitsu/mirin_bot_once/wiki/Bluesky-Guide)

3. `requirements.txt`を使って必要なライブラリをインストールします：
   ```bash
   pip install -r requirements.txt

4. reply_bot.pyを実行して、Botを起動します：

python reply_bot.py

### Q: モデル読み込みでエラーが出る
**A**: `cyberagent/open-calm-3b`のロード失敗は以下を確認：  
1. **ライブラリ**：`pip install torch==2.0.1+cpu transformers==4.36.2`（CPUの場合）。  
2. **キャッシュ**：`rm -rf ~/.cache/huggingface`でクリア。  
3. **ネットワーク**：Hugging Face接続が不安定なら、リトライ（コードに`load_model_with_retry`実装）。  
4. **ハードウェア**：GPUなしの場合、`torch.float32`と`device_map="cpu"`を設定。  
**ログ例**：`❌ Model error: ...`をチェック。

### Q: 「The operation was canceled.」エラーが出る
**A**: AI生成の中断は以下が原因：  
1. **メモリ**：RAM不足（7GB超）。軽量モデル（`open-calm-1b`）を試す。  
2. **タイムアウト**：Actionsの`timeout-minutes: 60`を設定。  
3. **ネットワーク**：Hugging Faceのダウンロード失敗。キャッシュクリア＆リトライ。  
**ログ例**：`RAM: XX%`や`GPU: XX/YY MB`を確認。

### Q: GIST_IDが読み込まれずエラー
**A**: 通常は`.env`やGitHub Secretsに`GIST_ID`を設定（例：`GIST_ID=your_gist_id`）。  
⚠️ **ただし**、GitHub ActionsでSecretsが読めない場合（例：`GIST_ID is None`）：  
1. リポジトリのSettings > Secrets and variables > Actionsで`GIST_ID`再設定。  
2. テスト用に`.yml`に直書き（**公開リポジトリではNG**）。  
**例**：
```yaml
env:
  GIST_ID: ${{ secrets.GIST_ID }}  # 通常
# 動かない場合（テスト用）
env:
  GIST_ID: your_gist_id_here

## 🚀 Botの起動方法（GitHub Actions）

### 1. 手動でBotを実行する
1. リポジトリの[Actionsタブ](https://github.com/mofu-mitsu/mirin_bot_once/actions)にアクセスします。
2. 一覧から「Run Reply Bot」を選択します。
3. 右上の「Run workflow」ボタン（緑色）をクリックします。
4. 必要に応じてパラメータを設定し、「Run workflow」をクリックします。
5. Botが自動的に起動し、返信を開始します！

### 2. 定期実行（オプション）
このBotは定期的に動作するようにも設定できます。
- 設定済みの場合、GitHub Actionsが自動で実行します。
- 実行スケジュールは以下の通りです：
  - 毎時実行（例: `0 * * * *`）

### 3. トラブルシューティング
- Botが動作しない場合、以下を確認してください：
  - GitHub Secretsが正しく登録されているか。
  - GitHub Actionsのログにエラーが表示されていないか。

#### 🕰️ 定期実行の設定方法**

### Q. 定期実行の設定を変更したい（例：実行間隔を短く/長くする）
A. GitHub Actionsの`.yml`ファイルを編集することで、実行間隔を自由に設定できます！

#### 定期実行の設定手順：
1. リポジトリの`.github/workflows/reply_bot.yml`ファイルを開きます。
2. 以下の部分を探してください（例：30分ごとに実行する場合の設定）：
   ```yaml
   schedule:
     - cron: "*/30 * * * *"
   ```
3. 実行間隔を変更したい場合、`cron`の値を編集します。

#### cronの設定例：
- **毎分実行：**  
  ```yaml
  cron: "*/1 * * * *"
  ```
  → Botが毎分実行されます（頻繁すぎる可能性があるので注意）。

- **30分ごとに実行：**  
  ```yaml
  cron: "*/30 * * * *"
  ```

- **毎時実行：**  
  ```yaml
  cron: "0 * * * *"
  ```

- **毎日午前9時に実行：**  
  ```yaml
  cron: "0 9 * * *"
  ```

#### cronのフォーマット：
`cron`は以下の形式で構成されています：
```
* * * * *
- - - - -
| | | | |
| | | | +---- 曜日（0〜7, 0と7は日曜日）
| | | +------ 月（1〜12）
| | +-------- 日（1〜31）
| +---------- 時間（0〜23）
+------------ 分（0〜59）
```

#### 注意：
- 実行頻度が高すぎると、GitHub Actionsの使用制限（無料枠の場合、月間2,000分）を超える可能性があります。
- 必要に応じて、[GitHub Actionsの使用制限](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration)を確認してください。
```

---

#### **Q. 手動実行と定期実行を併用できますか？**
A. はい、`workflow_dispatch`を設定すれば、手動でBotを実行することも可能です。以下のように`.yml`ファイルに両方を設定してください：
```yaml
on:
  workflow_dispatch: # 手動実行
  schedule: # 定期実行
    - cron: "*/30 * * * *" # 30分ごとに実行
```

---

#### **Q. 定期実行のスケジュールが動いていない場合は？**
A. 以下を確認してください：
1. `.yml`ファイルが正しく設定されているか。
2. cronのフォーマットが正しいか。
3. リポジトリが**Private（非公開）**の場合、GitHub Actionsの有効化が必要です。
4. ワークフローが一度も手動実行されていない場合、スケジュールが動作しないことがあります。  
   → 「Actions」タブから一度手動でワークフローを実行してください。

---

## 定期実行の設定方法

### 定期実行のスケジュールを変更する
定期実行のスケジュールは`.github/workflows/reply_bot.yml`ファイル内の`cron`で設定できます。  
以下のフォーマットに従って、スケジュールを自由に変更してください：

#### cronフォーマット：
```
* * * * *
- - - - -
| | | | |
| | | | +---- 曜日（0〜7, 0と7は日曜日）
| | | +------ 月（1〜12）
| | +-------- 日（1〜31）
| +---------- 時間（0〜23）
+------------ 分（0〜59）
```

#### よくある設定例：
- 毎分実行：`cron: "*/1 * * * *"`
- 30分ごとに実行：`cron: "*/30 * * * *"`
- 毎時実行：`cron: "0 * * * *"`
- 毎日午前9時に実行：`cron: "0 9 * * *"`

#### 注意：
- 実行頻度を高くしすぎると、GitHub Actionsの無料枠を超える可能性があります。
- 詳しくは[GitHub Actionsの使用制限](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration)を確認してください。

### Q. 問題が解決しない場合は？
A. [カスタマーサポート](#customer-support)へ！GoogleフォームやblueskyのDMで気軽にどうぞ♡

## 📚 もっと知りたい？
詳細なFAQやカスタマイズ例は[Wiki](https://github.com/mofu-mitsu/mirin_bot_once/wiki/Customization-Guide)へ！