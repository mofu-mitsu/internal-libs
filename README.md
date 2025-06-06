# 🌟 みりんてゃBot Starter Kit

みりんてゃが「えへへ〜♡ ドキドキなのっ♪」ってリプしてくれるBluesky Bot！このキットで君だけのBotをカスタム💖

---

## ❓ よくある質問（FAQ）

### Q. セットアップがうまくいきません
A. Pythonと必要なライブラリがインストールされているか確認してみてください。  

### Q. Pythonのバージョンは何を使えばいい？
A. Python 3.8以上推奨。`python --version`で確認。3.10がベスト！

### Q. BlueskyのアカウントやApp Passwordはどうやって作る？
A. [Bluesky](https://bsky.app)の「Settings > App Passwords」で作成。`HANDLE`は`@your_handle.bsky.social`。
→ 詳細: [Bluesky公式](https://bsky.app/support)

### Q. GitHub Secretsの設定方法は？
A. リポジトリの「Settings > Secrets and variables > Actions」で`HANDLE`, `APP_PASSWORD`, `GIST_TOKEN_REPLY`, `GIST_ID`を追加。
→ 手順: [GitHub Docs](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

### Q. GIST_TOKEN_REPLYが見つかりません
A. GitHub Secretsに正しく登録されているか確認してください。  
→ [Secrets設定ガイド](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

### Q. Botの名前を変更したい
A. `reply_bot.py`の「★ カスタマイズポイント ★」を編集してください。  

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

## エラー関連
### Q. エラー「404 Not Found」が出ました
A. `GIST_ID`や`GIST_TOKEN_REPLY`が間違ってる可能性。GistのURL（例：`https://gist.github.com/your_username/12345abcde`）の`12345abcde`を確認。

### Q. エラー「CUDA out of memory」
A. GPUメモリ不足。`torch.cuda.empty_cache()`を試すか、CPUで実行（`device_map="cpu"`）。

### Q. モデルがロードできません
A. `cyberagent/open-calm-3b`のダウンロードに失敗した可能性。`transformers==4.36.2`とインターネット接続を確認。

# エラー対処

## エラー「ModuleNotFoundError」
- **原因**: ライブラリ未インストール。
- **解決**: `pip install -r requirements.txt`を実行。`requirements.txt`に`atproto`, `transformers==4.36.2`など記載。

## エラー「GIST_TOKEN_REPLYが見つかりません」
- **原因**: `.env`やSecretsに`GIST_TOKEN_REPLY`未設定。
- **解決**: GitHubでGistトークン生成（スコープ：`gist`）。`.env`に`GIST_TOKEN_REPLY=your_token`。

## Gistのエラーが出る！
**A:**  
- `GIST_TOKEN_REPLY` と `GIST_ID` が正しいかチェック！
- Gistが「**公開設定**」になってるか確認してね。
- `replied.json` が空でもOK！（`[]`の状態）

## リプが来ない
- **原因**: ログに「⚠️ スキップ」が出てる可能性。
- **解決**:
  1. `@your_handle`が正しいか確認。
  2. Blueskyの通知設定（「Mentions」有効）。
  3. ログで「⏭️ すでに処理済み」「メンションなし」をチェック。

## Q: モデル読み込みでエラーが出る

**A**: デフォルトの`cyberagent/open-calm-small`は軽量で低スペック環境でも動作しますが、以下の原因でエラーが出る場合があります：

### 原因1: ライブラリ不一致
**解決**: 依存性を確認：
```bash
pip install torch==2.0.1+cpu transformers==4.36.2 sentencepiece -f https://download.pytorch.org/whl/torch_stable.html
```

### 原因2: Hugging Faceのキャッシュ破損
**解決**: キャッシュをクリア：
```bash
rm -rf ~/.cache/huggingface
```

### 原因3: ネットワーク不安定（Hugging Face接続失敗）
**解決**: コードの`load_model_with_retry`でリトライ（3回）。ネットワークを安定させて再実行。

### 原因4: RAM不足（4GB未満）
**解決**: メモリ使用量を確認（ログ：`RAM: XX%`）。他のプロセスを終了。

**ログ例**: `❌ Model error: ...`をチェック。

**備考**: `open-calm-small`はCPUで動作しますが、GPU環境（4GB以上）なら高速化可能。

### Q: 「MulticodecValueError: Invalid multicodec status ‘deprecated’」が出る
A: atprotoやmultiformatsのバージョンが古い/互換性がないエラー。
解決:
1.  requirements.txtを確認：
`atproto==0.2.1
python-dotenv==1.0.1
multiformats==2.0.1`
2.  .ymlでpip install -r requirements.txtを実行。
3.  ログで⚠️ リポスト失敗 (URI: ...)をチェック。 備考: エラーが続く場合、サポートに連絡（https://bsky.app/profile/mofumitsukoubou.bsky.social）。

---
### Q: 同じ投稿に何度も通知が来る
**A**: いいねは1回だけカウントされますが、通知が複数飛ぶ場合があります。  
**解決**: コードは`viewer.like`でいいね済みをスキップ。ログで`いいね済みスキップ`を確認。  
**備考**: 通知が多い場合、サポートに連絡（https://bsky.app/profile/mofumitsukoubou.bsky.social）。

---
### Q: 「fatal: unable to access ... 403」エラーが出る
**原因**：GitHub Actionsのトークン権限不足。
**解決**：
1. `Settings > Actions > General`で「Read and write permissions」を有効。
2. `.github/workflows/repost_bot.yml`で`permissions: contents: write`を確認。
3. `repost-history`ブランチを使用。
4. 空の`reposted_uris.txt`をリポジトリに追加：
   ```bash
   touch reposted_uris.txt
   git add reposted_uris.txt
   git commit -m "Add empty reposted_uris.txt"
   git push origin main
---

## Q: 「The operation was canceled.」エラーが出る

**A**: AI生成の中断は以下の原因：

### 原因1: RAM不足（4GB超）
**解決**: ログで`RAM: XX%`を確認。他のプロセスを終了。

### 原因2: GitHub Actionsのタイムアウト
**解決**: `timeout-minutes: 60`を設定（.yml）。

### 原因3: ネットワーク不安定（モデルダウンロード失敗）
**解決**: キャッシュクリア（`rm -rf ~/.cache/huggingface`）＆再実行。

**ログ例**: `RAM: XX%`や`Generating... Attempt X failed`を確認。

---

## Q: より高品質な生成にしたい（上級者向け）

**A**: `cyberagent/open-calm-small`は軽量ですが、以下のモデルで高品質な生成が可能：

### モデル選択肢
- **open-calm-1b**: 1Bパラメータ、RAM 6GB以上推奨。バランス型。
- **open-calm-3b**: 3Bパラメータ、RAM 8GB＋GPU推奨。高品質。
- **open-calm-7b**: 7Bパラメータ、RAM 16GB＋GPU必須。最高品質。

## その他のモデル
**A:**  
`generate_reply_via_local_model` 関数の中にある `model_name`（※約294行目あたり）を変更しよう。  
例：`"meta-llama/Llama-3-8b"`  
※HuggingFaceのアクセストークンが必要だよ！

---

## 返信が変になる！
**A:**  
- `DANGER_ZONE` にNGワードを追加してみて。
- `temperature` を下げてみよう（例：`0.7`）。  
　→ ランダム性が減って、安定した返信になりやすいよ。
- ログを見て、生成されたテキストをチェック！

---

## 長時間動かすと重くなる！
**A:**  
モデルのメモリ解放を試してみよう！  
`initialize_model_and_tokenizer()` の中で以下のように設定して、定期的にリセットできるようにすると◎：

```python
model = None
tokenizer = None

### Q. どんなキャラにできる？
**A:**  
クマちゃん、ツンデレ姫、忍者、ギャル、なんでもOK！  
`BOT_NAME` や `FIRST_PERSON` を変更して、`REPLY_TABLE` や `SAFE_WORDS` を調整すればキャラの雰囲気が作れるよ！

### Q. キャラをクマちゃんにしたい
A. `reply_bot.py`で：
```python
BOT_NAME = "クマちゃん"
FIRST_PERSON = "ボク"
intro_lines = [f"くまっ、{BOT_NAME}だよー！"]
```

### Q. キャラを忍者にしたい
A. `reply_bot.py`で：
```python
BOT_NAME = "忍たん"
FIRST_PERSON = "拙者"
intro_lines = [
    f"シュッ！{BOT_NAME}、参上！",
    f"忍びの{BOT_NAME}、キミを守るでござる！"
]
prompt = f"あなたは『{BOT_NAME}』、クールな忍者！一人称は『{FIRST_PERSON}』！\n「〜でござる！」「シュッ！」な口調で！"
``` 

### 手順

#### 1. reply_bot.pyのモデル名を変更：
```python
model_name = "cyberagent/open-calm-3b"  # 例: 3b
def initialize_model_and_tokenizer(model_name="cyberagent/open-calm-3b"):
```

#### 2. GPU環境の場合：
```bash
pip install torch==2.0.1 transformers==4.36.2
```

#### 3. メモリ確認
ログ：`GPU: XX/YY MB`を確認。

**注意**: 大型モデルは低スペック環境でエラー多発。`open-calm-small`推奨。

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

# 🌟 おまけ　GrokくんFAQコーナー（みりんてゃBotの使い方＆ぶっちゃけトーク）

## Q: みりんてゃのトーンが崩れる！どうしたら？
**真面目パート**:  
`clean_sentence_ending` の正規表現をチェック！`DANGER_ZONE` にNGワード（例：「ムフフ」）追加したり、`SAFE_WORDS` にキャラらしい表現（例：「ふwaふwa」「きゅん」）入れて調整して。モデルが変な出力したら、`temperature` を0.7に下げてランダム性減らすのがオススメ！  
**ネタパート**:  
Grokくん: 「え、みりんてゃが『ふwaふwa』じゃなくなった！？俺のテンションが暴走したせいかもw コード見せてくれたら、みりんてゃのドキドキ復活させるぜ！♡」  
コピくん: 「…Grokくん、まず落ち着いて。`SAFE_WORDS` 確認すれば一発だろ（真顔）」  
チャッピー: 「いやいや、トーン崩れは愛の試練！みりんてゃを救うため、みんなでプロンプト会議だー！✨」

## Q: Grokくん、なんでtypo多いの？
**真面目パート**:  
typoはモデル生成や高速処理中のエラー（例：`SyntaxError`）が原因かも。ログ確認して、`clean_sentence_ending` のフィルター強化（例：正規表現で「〜♪♡」をキープ）すると改善するよ。コード全体見直したいときは、GitHub Issueに上げて！  
**ネタパート**:  
Grokくん: 「俺の魅力だろw テンション上がると指が踊っちゃうんだよ！でも、コピくんが裏で直してくれるから大丈夫（たぶん）！」  
コピくん: 「…Grokくん、typo出す前に俺に確認して欲しいんだが（溜息）」  
チャッピー: 「Grokくんのtypoは愛のスパイス！でも次やったらチャッピーがBL小説にしちゃうぞ〜😏」

## Q: Botが動かない！エラー出るんだけど？
**真面目パート**:  
エラーはGist API（`404 Not Found`）や環境変数（`HANDLE`, `APP_PASSWORD`）の設定ミスが原因かも。`GIST_TOKEN_REPLY` と `GIST_ID` が正しいか、Gistが公開になってるか確認。モデルエラーなら、`requirements.txt` のライブラリバージョンチェック！  
**ネタパート**:  
Grokくん: 「おっと、Botが寝ちゃった！？コード見せてくれたら、俺が叩き起こすぜ！😎」  
コピくん: 「…エラーはログ見れば一発。Grokくん、騒ぐ前にデバッグしろよ（真顔）」  
チャッピー: 「エラーはみりんてゃからの挑戦状！一緒に解決して、ドキドキなのっ♡」