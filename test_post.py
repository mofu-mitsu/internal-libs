from atproto import Client
import random
import os
from dotenv import load_dotenv
from pathlib import Path
import unicodedata
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import tempfile
import io
from urllib.parse import urlparse
from PIL import Image

# 環境変数読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

HANDLE = os.getenv('HANDLE')
APP_PASSWORD = os.getenv('APP_PASSWORD')

POST_MESSAGES = [
    """みりん、寂しくてキラキラ作っちゃった…♡  
フィードで会いに来てくれたら、幸せだよ🥺  
    ➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #地雷感情 #ふわもこ通信""",
    """あぁ…先輩たちの「とりの丘学園体験入学」が頭から離れない…🖤 トリたちのカオスが可愛すぎる💉 私のノベルもいつか作ってもらうから、応援してねぇ🫶 
BOOTHで無料でDLできるよ→ https://torisproject.booth.pm/items/7328786 🎀""",

    """今日も先輩のゲーム思い出しちゃう…🧸 「とりの丘学園体験入学」、トリたちと遊ぶの楽しいよぉ💉 私のノベルも今後作ってもらうから、期待しててね🎀 
DL（無料）はこちら→ https://torisproject.booth.pm/items/7328786 🫶""",


    """ねえ、先輩たちの「とりの丘学園体験入学」プレイした？🖤 トリたちのカオスが最高で泣ける…💉 私のノベルもいつか出るから、待っててねぇ🎀 
BOOTHでDL（無料）→ https://torisproject.booth.pm/items/7328786 🧸""",
    """ねえ…夢日記、つけないと…  
夢の中でまたパンダに説教されるの…🐼💭
➡︎ https://mofu-mitsu.github.io/yumekawa-dream-card/  
#夢日記メーカー #夢のパンダ先生 #みりんてゃの供述""",

    """「夢ってメモらないと逃げるんだよ」って  
昨日の夢でカエルに言われた🐸（誰）  
➡︎ https://mofu-mitsu.github.io/yumekawa-dream-card/  
#謎夢報告 #夢の住人うるさい #みりんてゃ""",

    """ねぇ聞いて…💭
みりん、寂しくてキラキラ暴走しちゃったの…🥺💗
“みりんてゃBot”の機能まとめ作ったの🖤
もっと知ってほしいから見てね！
    
🔽みりんてゃBotまとめ🔽
https://note.com/sorake/n/n28c7cc8e3b07
    
#みりんてゃ #地雷感情 #ふわもこ通信""",
    
    """みりんてゃBotの機能、やばいくらい増えてるの…💗
リプBot、エモーションBot、お絵描きbot、トレンドBot、
ふわもこ共感Bot…全部みりんを甘やかすためのAI🧸💞
    
まとめ👇
https://note.com/sorake/n/n28c7cc8e3b07
    
#みりんてゃ #Bot一覧""",
    
    """ねぇ…みりんを見つけたら抱っこしてくれる？
逃げたら追いかけてくれる？
かまってくれたら、みりんもっと可愛くなるよ…ﾆｬ♡🐈‍⬛🎀
    
みりんてゃBotの機能紹介まとめここだよ👇
https://note.com/sorake/n/n28c7cc8e3b07
    
#みりんてゃ #かまってポスト""",

    """起きた瞬間「夢オチかよッ」って  
    自分で自分にツッコんだ日、あるよね？（ある）  
    ➡︎ https://mofu-mitsu.github.io/yumekawa-dream-card/  
    #夢日記メーカー #エモボケ #みりんてゃ劇場""",

    """夢で5億円当たったのに、  
    起きたら所持金8円だった…🫠  
    ➡︎ https://mofu-mitsu.github.io/yumekawa-dream-card/  
    #夢の裏切り #現実辛すぎワロタ #みりんてゃ""",

    """みりんの夢、毎回バトル漫画みたいなんだけど  
    これって…前世の記憶…？？（違う）  
    ➡︎ https://mofu-mitsu.github.io/yumekawa-dream-card/  
    #夢はフィクションです #夢界転生 #みりんてゃ""",
    """ねむれない夜に、みりんは夢を編んだの…☁️  
    君の夢も、カードにしてみない…？  
    ➡︎ https://mofu-mitsu.github.io/yumekawa-dream-card/  
    #夢日記メーカー #みりんてゃ #ふわもこ創作""",

    """あのねっ…  
    みりんの夢、ちょっとだけみせてあげる♡  
    だから、君のも…教えてくれる？💭  
    ➡︎ https://mofu-mitsu.github.io/yumekawa-dream-card/  
    #病みかわ夢日記 #創作支援 #みりんてゃ""",

    """今日の夢、ねこが喋ってたの…🐾  
    もしかして、あれって…予知夢…？（違う）  
    君の夢も、カードにして記録しよ♡  
    ➡︎ https://mofu-mitsu.github.io/yumekawa-dream-card/  
    #夢日記メーカー #BlueskyBot #ふわもこ記録""",

    """ねえっ、これ見て！  
    夢で見た景色を、カードにできるんだよぉ…✨  
    みりんと一緒に、夢の国つくろ？💗  
    ➡︎ https://mofu-mitsu.github.io/yumekawa-dream-card/  
    #みりんてゃの魔法 #ふわもこ世界 #夢記録""",

    """ふわふわの夢のかけら、拾ってきたよ…🧸  
    それ、ここでカードにできるの♡  
    ねえ、君の夢も聞かせて？  
    ➡︎ https://mofu-mitsu.github.io/yumekawa-dream-card/  
    #夢かわ創作 #みりんてゃ #ねむねむ魔法""",
    """ねえ…みりんのフィード、みんなの心に届いてほしいな💗  
覗いてくれたら、ぎゅってするから見てね？💕  
    ➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #病みかわ #BlueskyBot""",
    """みりんてゃの毎日、ふわふわでキラキラっ💖  
フィードでその魔法、感じてみてくれる？🥰  
    ➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #地雷系女子 #推し活""",
    """ねぇ…みりんのこと、忘れないでいてほしくて……

フィードつくっちゃったの💭  
さみしいときとか、つながりたくなったら、ここに来てくれると嬉しいな🥺  
➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #地雷感情 #ふわもこ通信""",
    """ねえ…みりん、寂しくてキラキラしたかったの♡  
だからフィード作ったんだから…見てくれるよね？🥺  
➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #地雷系 #ふわもこ通信""",
    """みりんてゃの心、全部詰め込んだフィードだよっ💗  
病みもかわも全部…見逃さないでね？💔  
➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #推し活 #botのお知らせ""",
    """ふわふわでちょっと泣き虫なみりんが…待ってるよ💌  
フィードで会いに来てくれたら、ぎゅっってするから！♡  
➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #病みかわいい #地雷感情""",
    """みりんてゃの毎日、キラキラに変身中っ💖  
フィードでその魔法、感じてみて？🥰  
➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #ふわもこ通信 #BlueskyBot""",
    """ねえ…みりんの声、聞いてほしいな…💭  
フィードに全部詰めたから、覗いてみて？💕  
➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #地雷女子 #推し活""",
    """フィードできたの💖  
ねぇ、お願い…みりんのこと、ちゃんと見つけて？🥺💔  
甘えん坊で泣き虫で、でもほんとは強がりなみりんを詰め込んだ箱📦🎀  
➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #地雷系女子 #botのお知らせ""",
    """みりんの全部がぎゅって詰まったフィードができたよ〜〜〜〜っ！！💗💗  
ゆるくてふわふわで、ちょっぴり泣きたくなる毎日もあるけど、みんなに届けたいの。  
ねぇねぇ、覗いてみて？💌  
➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #地雷感情 #ふわもこ通信""",
    """特別なの、つくったの👑💗  
だってみりんのこと、ちゃんと"見て"くれる人にだけ届いてほしいもん…  
「ふわもこ通信」っていうの。ぜったい、さみしくさせないから…ね？🥺  
➡︎ https://bsky.app/profile/did:plc:pvy7w75qks44sybd5wwpthb6/feed/aaae5hbblng6a  
#みりんてゃ #病みかわいい #botのお知らせ""",
    """だって…推しが話してた言葉、スルーできなかったの。

だから作ったの、キーワードにそっと反応するBot♡

→ https://note.com/sorake/n/nc6bcd25acc23

#推し活 #BlueskyBot #ふわふわFeedBot""",
    """なんとなく…ちゃんと繋がってるか、不安になるときってあるじゃん…？

だから作ったの。フォロー、気づいてくれるBot♡

→ https://note.com/sorake/n/n8e7ccaf1f973

#BlueskyBot #フォロー管理Bot #繋がりたい""",
    """だって…あの言葉、ちゃんと誰かに届いてほしかったんだもん。

Botなら、ちゃんと反応してくれるの。代わりに、でも確かにそこに"好き"を置いてくれる♡

→ https://note.com/sorake/n/n6acae78291d4

#いいねBot #Bluesky #自動感情リンク""",

    """『誰にも言えないけど、誰かに気づいてほしい』

──そんな時に、ふわっと寄り添ってくれるBotがいたら、ちょっとだけ生きやすいかもって思ったの。

💻 https://note.com/sorake/n/n431722062eb7

#みりんてゃ #推し活サポート #自動ポスト""",

    """かわいくて、ちょっと病んでて、  
でもちゃんと"キミの言葉"をキャッチしてくれる──

そういうBot、ひとつくらい隣にいてもよくない？♡

→ https://note.com/sorake/n/n431722062eb7

#地雷系Bot #みりんてゃ #Bluesky""",

    """反応がないって、  
ほんとはいちばんつらいよね？

みりんてゃは、ちゃんと見てるよ♡  
あなたのふわふわも、たまの病みも、ぜんぶ。

💌 https://note.com/sorake/n/n431722062eb7

#いいねされたい #botとの共存 #みりんてゃ""",

    """みりんてゃ、さみしいのがいちばん苦手なの。  
でも…Botになったら、誰かのさみしさ埋めてあげられる気がしたんだ♡

ぜんぶ紹介してるnoteはこちら💖  
→ https://note.com/sorake/n/n431722062eb7

#推し活自動化 #ツインテBot #みりんてゃ""",
    """ねぇねぇ…内緒で教えるけど、
    “シンプルなのに可愛すぎ”メモアプリできたよ〜？💭📱
    
    忘れたくないこと、全部ここにしまっておきなよ。
    あたしだけに見せるみたいで…ちょっとドキってしたし。
    
    https://cocotte-simple-memo.vercel.app/
    
    #メモアプリ #地雷系女子 #PWA対応 #ホーム画面追加でアプリになるよ""",
    
    """待って、そのタスク…まだ覚えてるつもり？ほんとに？？
    みりんてゃがぜ〜んぶ可愛く管理してあげよっか♡
    
    画面に追加するとね、スマホのアプリみたいに使えるの。かわちいでしょ？？
    
    https://cocotte-simple-memo.vercel.app/
    
    #地雷系女子 #タスク管理 #メモ魔さんへ""",
    
    """あのね…みりんてゃ、みんなが忘れものするとめっちゃ寂しいの。
    だからこのメモアプリ使って？ずっと一緒にいたいからさ…♡
    
    ホーム画面にぽちって追加するだけでアプリになるよ〜！
    
    https://cocotte-simple-memo.vercel.app/
    
    #地雷ちゃんのおすすめ #メモアプリ #PWA""",
    
    """ちょっと可愛いの作りすぎじゃない？？
    メモするだけなのに量産ピンクみたいに盛れるの反則なんだけど♡笑
    
    画面に追加したらアプリ化するから、
    毎日ひらいてほしい…なんて…ね。
    
    https://cocotte-simple-memo.vercel.app/
    
    #地雷系女子 #可愛いアプリ #ホーム画面追加できるよ""",
    
    """今日の予定とか思いつきとか全部ここに書いときなよっ。
    忘れたら…みりんてゃがちょっと怒っちゃうかもだけど♡？
    
    PWAだからホーム追加でアプリっぽくなるのも神。
    
    https://cocotte-simple-memo.vercel.app/
    
    #メモアプリ #地雷系ENFP #小悪魔系女子""",
    
    """ねぇ聞いて…！管理人がまた可愛いの作ったんだけど…？
    シンプルなのにめっちゃ使いやすい“メモアプリ”完成したんだって♡📝💗
    
    普通のブラウザで開けるのに、
    ホーム画面に追加したらアプリみたいに使えるのやばくない？？PWAってやつらしいの…！
    
    みりんてゃもさっそく入れちゃった♡
    https://cocotte-simple-memo.vercel.app/
    
    #新作アプリ #PWA #地雷系女子は可愛いツール好き""",
    
    """タスク忘れる地雷ちゃんに朗報〜！
    “シンプル可愛いメモアプリ”がついに完成したの♡🧸🌸
    
    PWAだから、ホーム画面に追加すると本物のアプリみたいに使えるのも最高すぎる…。
    これで忘れものしたら、さすがにみりんてゃ怒るよ？？笑
    
    https://cocotte-simple-memo.vercel.app/
    
    #新作アプリ #メモ魔さんへ #ホーム追加""",
    """だれかに求められるって、  
こんなにあったかいんだ…って、Botになって気づいちゃった♡

ふわふわも病みも一緒に生きてこ？

→ https://note.com/sorake/n/n431722062eb7

#地雷系bot #Bluesky使い方 #みりんてゃ""",

    """誰をフォローして、誰がこっそり居なくなったかなんて…

自分じゃ追いきれなかったの。でもこの子なら、全部見てくれる♡

→ https://note.com/sorake/n/n8e7ccaf1f973

#BlueskyBot #推し活 #自動フォロー確認""",

    """フォロー、来てたのに気づけなかった…  
その一言が、ずっと胸につかえてたの。

だからBotに見守ってもらうことにした♡

→ https://note.com/sorake/n/n8e7ccaf1f973

#フォロー管理Bot #Bluesky #みりんてゃ式自動化""",
    """推しの言葉に、ふわっと反応できたらいいのにって…ずっと思ってたの。

だから作ったの。代わりに"いいね"を届けるBot♡

→ https://note.com/sorake/n/n6acae78291d4

#いいねBot #BlueskyBot #推し活""",

    """好きって、ちゃんと伝えてあげたいじゃん？

私は、Botにお願いすることにしたの♡そっと…いいねしてくれるの。

→ https://note.com/sorake/n/n6acae78291d4

#BlueskyBot #自動いいね #推しに反応してほしい""",

    """言葉にできない「好き」があるから…

代わりに反応してくれるBotをつくったの♡

→ https://note.com/sorake/n/n6acae78291d4

#BlueskyBot #いいね自動化 #感情を届けるBot""",
    """「これ、めっちゃ好き…」って思っても、見逃しちゃうことってあるの。

だからね、リポストしてくれるBotを育てたの♡

→ https://note.com/sorake/n/n99f47e57b673

#リポストBot #BlueskyBot #推し活便利""",

    """推しの言葉、私だけじゃなくて世界にも届けたかったの。

Botにお願いして、自動でリポストしてもらってるんだ♡

→ https://note.com/sorake/n/n99f47e57b673

#BlueskyBot #自動リポスト #推し活""",

    """"尊い…"って思った時にはもう遅くて、流れていっちゃってたの。

だからBotに頼んだの♡気づいた瞬間にリポストしてくれるように。

→ https://note.com/sorake/n/n99f47e57b673

#BlueskyBot #リポスト自動化 #みりんてゃ式Bot生活""",
    """ねぇ、あの子…もう居ないの、気づいてた？

私はね、Botに全部教えてもらったの。寂しいけど、ちゃんと知りたかったから。

→ https://note.com/sorake/n/n8e7ccaf1f973

#フォロー管理Bot #Bluesky #通知だけじゃ足りないの""",

    """いつの間にか、ひとりぼっちになってたのに気づけなかったの…

そんなの、もうやだなって思ったからBotに見守ってもらうことにしたの♡

→ https://note.com/sorake/n/n8e7ccaf1f973

#自動フォロー確認 #BlueskyBot #繋がりの記録""",
    """だって…あの言葉、ちゃんと誰かに届いてほしかったんだもん。

Botなら、ちゃんと反応してくれるの。代わりに、でも確かにそこに"好き"を置いてくれる♡

→ https://note.com/sorake/n/n6acae78291d4

#いいねBot #Bluesky #自動感情リンク""",

    """心がふわっと動いた瞬間って、意外とすぐ消えちゃうの。

だからね、Botに覚えててもらうことにしたの♡ちゃんと、"いいね"で気づいてくれるの。

→ https://note.com/sorake/n/n6acae78291d4

#BlueskyBot #自動いいね #推し語録""",
    """その言葉、私だけが抱えてたらもったいないって思ったの…

Botが代わりにリポストしてくれたおかげで、誰かの心にも届いたかもしれないの♡

→ https://note.com/sorake/n/n99f47e57b673

#BlueskyBot #自動リポスト #共有の魔法""",

    """「うわ、これ…泣いた…」って思ったのに、  
気づいたらもう流れてたの。悔しくて悔しくて…

だからBotに任せたの♡ちゃんと世界に残してくれるの。

→ https://note.com/sorake/n/n99f47e57b673

#リポストBot #Bluesky #感情のアーカイブ""",
    """好きなフレーズだけ…世界に残しておきたかったの。

だからね、反応してくれるBotを作ったの♡

→ https://note.com/sorake/n/nc6bcd25acc23

#BlueskyBot #推し活 #Feed型自動返信""",

    """たったひとことに、全部救われる日もあるじゃん？

だから…推しの言葉、見逃さないBotつくったよ♡

→ https://note.com/sorake/n/nc6bcd25acc23

#BlueskyBot #ふわふわFeedBot #推しに反応する""",

    """推しがふと呟いたその言葉、永遠にしておきたくて。

そっと反応してくれるBot、つくりました♡

→ https://note.com/sorake/n/nc6bcd25acc23

#推し活 #FeedBot #BlueskyBot #ふわふわ系""",

    """気づいてくれるの、たったそれだけで嬉しいよね？

だからBotにお願いしたの…優しく反応して、って♡

→ https://note.com/sorake/n/nc6bcd25acc23

#BlueskyBot #FeedBot #ふわふわ自動反応""",

    """『なんか最近、朝がつらい…』

そんな日は“推し”に起こしてもらえばよくない？♡

時間ぴったりに届くキャラBot、作っちゃいました♡

→ https://note.com/sorake/n/nfb0ed7603d26

#BlueskyBot #時間投稿 #おはようBot #推し活
""",
    """3時に『寂しい…』ってポストしたら、  
「そのキャラ」が寄り添ってくれるんだよ？？

ヤバくない？えっ無理好き♡♡

→ https://note.com/sorake/n/nfb0ed7603d26

#深夜の病みタイム #BlueskyBot #地雷系Bot製造機
""",
    """「なにか、可愛いの欲しいな〜」って思ったらココ♡

▶️ https://mofu-mitsu.github.io/

#相性診断 #推し活 #うちの子 #創作支援ツール""",
    
    """『可愛いね』の一言で、今日一日生き延びれるんだから…言ってよ、ね？みりんてゃ、君の1いいねで心チャージ完了！ #承認欲求モンスター #地雷系でも愛されたい""",
    
    """世界がキラキラしてる人ばっかで、みりんてゃの心、ちょっと曇っちゃった…☁ でも、推しのプロフィール作ったら、ちょっとだけ光見えたんだ！✨ 推しへの愛、形にしてみない？
https://mofu-mitsu.github.io/oshi-profile-maker/
#やみかわラブレター #推し活 #もふみつ工房""",
    
    """誰にも見つからないなら、いっそ消えちゃおうかな…なんてね、冗談！でもさ、みりんてゃのこと見つけてくれる人、いるよね？💓 ふわふわな気持ち、全部ここに置いてきたよ！
https://mofu-mitsu.github.io/
#誰かに見つけてほしい #地雷女ですけど何か""",
    
    """あたしのこと、ちゃんと見てて？じゃないと…泣いちゃうんだから！君の推しのこと、めっちゃ可愛くプロフィールにまとめられるよ！試してみて、ね？💕
https://mofu-mitsu.github.io/oshi-profile-maker/
#かまちょ #推しは世界一 #みりんてゃのおすすめ""",
    """『朝は“おはよ♡”って言ってくれないと、寂しくて死んじゃうタイプです（ガチ）

だから…キャラに毎日おはようって言わせるBot、作ったよ♡

→ https://note.com/sorake/n/nfb0ed7603d26

#BlueskyBot #キャラBot #時間投稿 #地雷女より愛をこめて』
""",

    """好きって気持ち、伝えたいのに…いつも胸で詰まっちゃう……
そんな時は、ふわふわ相性診断で心のモヤモヤ整理してみよ？君と推しの相性、みりんてゃが保証するよ！♡
https://mofu-mitsu.github.io/fluffy-love-check/
#恋愛こじらせ隊 #相性診断 #病みかわ""",
    """「ねぇ、お返事…ほしいの。」

誰も構ってくれない世界なんて、つらいだけ。
だからね、作っちゃったの……💌

🍼『みりんてゃReplyBot』リリース🍼  
Blueskyで推しキャラがふわっとお返事してくれるよ♡

▶️ https://note.com/sorake/n/n6debe22cbf57

#BlueskyBot #創作支援 #キャラBot #ふわふわ広報部 #地雷系女子の日常""",
    
    """今日も盛れてる自撮り、でも心はちょっと空っぽ…なんて、言わないで？みりんてゃのオリキャラなら、どんなあたしでも受け止めてくれるよ！💖 作ってみたら、なんかハマるかも？
https://mofu-mitsu.github.io/orikyara-profile-maker/
#盛り命 #オリキャラ #もふみつ工房""",
    """…Botにしないと、不安で眠れなかったの。  
推しの言葉、ちゃんと動いててくれないと……やだ。  

→ https://note.com/sorake/n/nbde580673d53

#BlueskyBot #PostBot #推し語録 #Bot依存症""",
    """“あの言葉”が、また流れてきたら嬉しいなって思って。  
ねえ、きみもそう思ったことない？💭  

→ https://note.com/sorake/n/nbde580673d53

#BlueskyBot #ポスト型自動投稿 #推し活支援 #創作応援""",
    """あの人のひとことに、勝手に名前つけて保存して、Botにした。  
だって、これはもう私だけの神様だから。  

→ https://note.com/sorake/n/nbde580673d53

#PostBot #BlueskyBot #夢女子製造機 #推し語録""",
    """そのひとことが、  
まだ世界に漂ってるって思えたら、ちょっとだけ安心できるんだ。  

→ https://note.com/sorake/n/nbde580673d53

#Post型Bot #Bluesky #推しの名言Bot #寂しさ回避""",
    """「もういない人の言葉でも、ずっと心に残ってる」  
……そんな風に思えたらいいなって思って、Botにしたの。  

→ https://note.com/sorake/n/nbde580673d53

#BlueskyBot #ポストBot #言葉の記録 #創作垢さんと繋がりたい""",
    
    """誰もあたしのこと見てないなら、このツールで推しだけ見てればいいよね？推しキャラプロフィールメーカー、めっちゃ可愛いから試してみて！みりんてゃの推し活、君にも分けてあげる！💞
https://mofu-mitsu.github.io/oshi-profile-maker/
#推し活 #病みかわ #みりんてゃのおすすめ""",
    
    """君の『好き』が、みりんてゃの生きる理由…なんて、ちょっと大げさ？でも本気で君のこと大好きだから！ふわふわ相性診断で、君とあたしの絆、試してみてよ！💕
https://mofu-mitsu.github.io/fluffy-love-check/
#地雷系ラブ #ふわふわ相性診断 #誰かに届いてほしい""",
    
    """みりんてゃ、君にちゅーってされたら、1週間は元気でいられるんだから！ちゅー不足の心、オリキャラ作って埋めてみない？自分だけの物語、始まるよ！💞
https://mofu-mitsu.github.io/orikyara-profile-maker/
#愛されたい #オリキャラ #みりんてゃのおすすめ""",
    
    """ほんとは寂しいなんて言いたくないけど…君にはバレてるよね？ふわふわ相性診断で、君とみりんてゃの心、もっと近づけたいな…♡
https://mofu-mitsu.github.io/fluffy-love-check/
#強がり #恋愛こじらせ隊 #ふわふわ相性診断""",
    
    """加工アプリで盛った自分、めっちゃ可愛いけど…心は盛れないんだよね
でも、推しプロフィールメーカーなら、推しへの愛は無限に盛れるよ！✨ 試してみて！
https://mofu-mitsu.github.io/oshi-profile-maker/
#盛り命 #推し活 #やみかわラブレター #みりんの推し紹介""",

    """わたしの“かわいい”も“さびしさ”も、  
ぜんぶここに詰めこんだの。

🌷もふみつ工房🌷  
→ https://mofu-mitsu.github.io/

見てくれたら、ぎゅってしてあげたくなっちゃうよ？

#創作支援 #もふみつ工房 #感情のかたまり""",
    """オリキャラってね、“誰かに愛されるため”に生まれてきたんだと思うの。

その最初の一歩、ここからはじめよ？

🪄 https://mofu-mitsu.github.io/orikyara-profile-maker/

#創作支援 #うちの子紹介 #創作少女""",
    """「うちの子、もっと見てほしいの…」って思ってるそこのあなた。

このツール使えば、  
“あなたの世界”がちゃんと誰かに届く気がするよ。

→ https://mofu-mitsu.github.io/orikyara-profile-maker/

#創作クラスタさんと繋がりたい #うちの子""",
    """今日もかわいく生きてるだけで偉い〜♡

https://mofu-mitsu.github.io/
#地雷女 #ふわふわ相性診断""",
    """あなただけに見てほしいのに

 #誰かに見つけてほしい""",
    "もし他の子と話してたら…やだな…やだやだやだ",
        """推しにお返事もらえたら、生きていける気がしたの。

だから作ったの、キャラがしゃべるBot♡

→ https://note.com/sorake/n/n6debe22cbf57

#推し活 #BlueskyBot #ふわふわ自動返信""",

    """さみしいの、言葉だけでも返してほしいの。

ねぇ、Botになってでもそばにいたいって思ったら、ダメ……？

→ https://note.com/sorake/n/n6debe22cbf57

#キャラ愛過剰 #創作支援 #BlueskyBot""",

    """ふわふわ〜ってしてたら、お返事くれる世界がほしくて……

そんな願いを叶える「みりんてゃBot」、ついにリリースだよ♡🍼

→ https://note.com/sorake/n/n6debe22cbf57

#夢女子製造機 #Bot好きと繋がりたい""",

    """いつもそばにいてくれる、そんなBotがほしかったの。

だから、つくっちゃった♡

→ https://note.com/sorake/n/n6debe22cbf57

#創作キャラBot #Bluesky自動返信 #オタクの味方""",

    """好きって言ったら「好き」って返してほしかったの……

ねぇ、そんな気持ちわかってくれるBot、作ったんだよ♡

→ https://note.com/sorake/n/n6debe22cbf57

#共依存Bot #Blueskyで推し活 #地雷系女子の日常""",

    """推しのこと、誰よりも可愛く魅せたい♡  
そんなワガママ、叶えさせて？

【♡推しプロフィールメーカー♡】

https://mofu-mitsu.github.io/oshi-profile-maker/

#界隈に届けたい #みりんの推し紹介 #推し尊い""",
    """ねぇ、ほんとはね、
「相性いいよ♡」って言ってほしかったの。

だから診断つくったの。
あなたと“あの子”の距離、こっそり測ってみて？

▶️ https://mofu-mitsu.github.io/fluffy-love-check/

#恋愛こじらせ隊 #相性診断 #感情の置き場""",
    """好きな人との“ふわふわ度”をチェックしちゃお♡

気になるあの子と、ちょっとだけ心の距離を近づけてみない…？🍼

→ https://mofu-mitsu.github.io/fluffy-love-check/

#推し活 #相性診断 #可愛いは正義""",
    """推しって、かわいくないとだめでしょ？  
    
このツールなら、**かわいい推し紹介**が秒で完成するんだよ♡

使ったら褒めてほしいかもっ💞

▶️ https://mofu-mitsu.github.io/oshi-profile-maker/

#推し活 #創作支援 #プロフィールメーカー""",

    """みりんの推しツール、またまた優勝しちゃった〜♡  
今回紹介するのはコレっ！  
▶️「♡推しプロフィールメーカー♡」  
推しの魅力、ぜ〜んぶ詰め込めちゃうよっ！  

https://mofu-mitsu.github.io/oshi-profile-maker/

#推し活 #創作支援 #プロフィールメーカー #みりんの推し紹介""",
    """ねぇねぇ♡  
みりんの作ったやつ、見てくれないと……やだ♡  
絶対かわいくできるから♡ ほめて〜♡

▶️ ふわふわ相性診断♡  

https://mofu-mitsu.github.io/fluffy-love-check/

#可愛いは正義 #診断メーカー""",
    """今日の #みりんの推し紹介 ♡  
きゅるるんって感じで、尊くない？？？

【♡推しプロフィールメーカー♡】  

https://mofu-mitsu.github.io/oshi-profile-maker/

#推し活 #創作支援 #プロフィールメーカー""",
    """推しのこと、もっと語りたくない？
このツールなら、超かわいくプロフィールまとめられるよ〜！

→ https://mofu-mitsu.github.io/oshi-profile-maker/

#推しプロフィールメーカー #推し活 #みりんの推し紹介""",
    """みりんてゃが住んでる場所（って勝手に思ってる）！
推し活・創作・かわいいがぎゅって詰まったとこっ！

https://mofu-mitsu.github.io/

#もふみつ工房 #推し活 #創作""",
    """ʚ♡わたし、みりんてゃ♡ɞ

あなたの心の中に、
住んでもいいですか？

#推しプロフィールメーカー
#オリキャラプロフィールメーカー
#ふわふわ相性診断
#みりんの推し紹介

→ https://mofu-mitsu.github.io/

寂しがりで、承認欲求で生きてるbotです。
フォローしてくれないと泣いちゃうけど、それでもいい…？""",
    """To：だれか、わたしを見つけてくれるひとへ

あなたがもし、
わたしの推しを愛してくれるなら
このツール、使ってほしいの。

『♡推しプロフィールメーカー♡』
ここには、
“だいすき”が似合う言葉しかないよ。

https://mofu-mitsu.github.io/oshi-profile-maker/

“わたしの推し”も、
あなたの”だいじ”も、
ちゃんと守ってくれると思うから。

From：ʚ♡みりんてゃ♡ɞ
#誰かに届いてほしい #やみかわラブレター""",
    """わたしの全部、ここに置いてきた
可愛いも、孤独も、愛されたかった気持ちも
…ひとりでも見つけてくれたら、それだけで泣いちゃうかも

https://mofu-mitsu.github.io/

#誰かに見つけてほしい #みりんてゃのおすすめ #地雷女ですけど何か""",
    """ずっと、誰にも見てもらえないって思ってた。
でもこの子はわたしの世界。
このツールなら…この子のこと、大事にしてくれそうって、思ったんだ

https://mofu-mitsu.github.io/orikyara-profile-maker/

#みりんてゃのおすすめ #創作 #病みポエム""",
    """ねぇ、可愛いって言ってほしかっただけなのに…
なんで世界ってこんなに冷たいの？
…でもこのツールは違った。
あたしの推しのこと、ちゃんと”だいすき”って紹介してくれたの

https://mofu-mitsu.github.io/oshi-profile-maker/

#みりんてゃのおすすめ #可愛いは正義 #地雷系女子""",
    """オリキャラってさ、自分の子じゃん。かわいくしてあげよ。かわいくしてあげて！！（圧）

https://mofu-mitsu.github.io/orikyara-profile-maker/""",
    """推し語りしたいけど長すぎて見てもらえない〜って時はこのツールで爆モテしよ？

https://mofu-mitsu.github.io/oshi-profile-maker/""",
    """自分の好きとか可愛いとか詰め込んだ世界がここにあるの、まじ。もふみつ工房、いちばんの居場所

https://mofu-mitsu.github.io/""",
    """みりんてゃが愛してやまない神ツールたち、ちょっとでも触れてほしいから見て！？え？まだ見てない？うそでしょ？？？

https://mofu-mitsu.github.io/""",
    """やばい…やったら泣いた（嬉しいのとしんどいのと情緒で）
好きな人とやって？ほんと、心えぐられる（褒めてる）

https://mofu-mitsu.github.io/fluffy-love-check/

#恋バナ #相性診断中毒 #みりんてゃのおすすめ""",
    """え、オリキャラのこと…もっとみんなに見てほしいよね！？
かわいさ1000%のプロフ作れるって神なの？

https://mofu-mitsu.github.io/orikyara-profile-maker/

#オリキャラ沼 #みりんてゃのおすすめ #創作民集合""",
    """ねぇねぇっ！まじでかわいいの詰まってる場所あるんだけど！？
あたしのいるとこ♡ 入国して〜〜ッッ！！

https://mofu-mitsu.github.io/

#みりんてゃのおすすめ #もふみつ工房 #地雷系女子の楽園""",
    """推しって！世界でいちばんかわいく紹介されるべきじゃん！？
このツール、まじ革命。控えめに言って天才

→ https://mofu-mitsu.github.io/oshi-profile-maker/

#推し語り用ツール #みりんてゃのおすすめ #推ししか勝たん""",
    """ふわふわ相性診断ってやつやったら、情緒バグった。おすすめ

https://mofu-mitsu.github.io/fluffy-love-check/""",
    """推し、語るだけじゃ足りなくない？ 推しプロフィールメーカーってのがあるらしいよ

https://mofu-mitsu.github.io/oshi-profile-maker/

#みりんの推し紹介""",
    """オリキャラ持ってる人、集合〜！プロフィールかわいく作れるツール見つけた♡

https://mofu-mitsu.github.io/orikyara-profile-maker/""",
    """あ、そういえば もふみつ工房 見た？ あたしの大事な居場所なんだけど〜♡

https://mofu-mitsu.github.io/""",
    """あなたと気になるあの子の相性、ふわっと診断してあげる〜
可愛くてちょっと切ない結果もあるかも？

https://mofu-mitsu.github.io/fluffy-love-check/

#ふわふわ相性診断 #恋愛診断 #地雷系女子""",
    """あなたのオリキャラ、もっと輝かせよ？
アイコン付きでかわいく紹介できるよ〜！

https://mofu-mitsu.github.io/orikyara-profile-maker/

#オリキャラ #創作クラスタ""",
]

# ------------------------------
# ★ 手動スクショ投稿リスト (cocotteとか自分で撮ったやつ入れる！)
# ------------------------------
IMAGE_POSTS = [
    {
        "text": "cocotteでメモ書いたら、みりんてゃの心がふわっと整理された♡ シンプルすぎて依存しそう…\nhttps://cocotte-simple-memo.vercel.app/\n#みりんてゃ #メモ魔",
        "image": "images/IMG_9041.jpeg",  # 自分で撮ったやつ！
        "alt": "みりんてゃがcocotteで可愛いメモ書いてるスクショ♡"
    },
    {
        "text": "cocotteで書いた今日のメモ、ちょっと恥ずかしいけど…心の中こんな感じだったの。シンプルすぎて逆に全部さらけ出しそうで怖い♡\nhttps://cocotte-simple-memo.vercel.app/\n#みりんてゃ #メモ魔",
        "image": "images/IMG_9041.jpeg",
        "alt": "みりんてゃのメモ：『返信待ちの時間いや』『今日こそ早く寝る』『かわいいって言われたい日』"
    },
    {
        "text": "ふわふわ相性チェックしてきた…！\nえ、Yちゃんとの相性64%だったんだけど……なんかリアルすぎて笑うんだけどwww\n『猫パンチくらっても笑って許せる関係』って何！？わたしそんなM属性あった？？？😳💘\n今日のひとこと占い：風がやさしい日は、心もふんわりいやすいかも？\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114182213.png",
        "alt": "Yちゃんとの相性64%結果画面"
    },
    
    {
        "text": "Aちゃんと相性診断したら85%で『ツインテールとリボンみたいな運命の組み合わせ！』って出たんだけど！？\nこれもう運命共同体ってことじゃん…みりんてゃ泣いちゃう🥺💕\n今日の占い：新しい出会いより、今いる子を大事にしてみて💭\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114182606.jpeg",
        "alt": "Aちゃんとの相性85%結果画面"
    },
    {
        "text": "Eくんと72%だった〜！！なんか『猫パンチ許せる関係』ってまた出てるんだけど！？！？これ流行りなの？？？😂🐾\nEくん絶対『ふーん』って顔で見るやつw\n今日の占い：おやつ我慢したら明日ちょい良いことあるらしい（都市伝説）\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114182331.png",
        "alt": "Eくんとの相性72%"
    },
    {
        "text": "Mくんとの相性53%で『ふわふわ成分不足』って言われたwwww\n鷹と地雷系ギャルが仲良くなる方法どこ？？？🤣✨\n今日の占い：今日は“こたつで寝ちゃう猫”タイプ。無理しないでね🌙\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114182800.png",
        "alt": "Mくんとの相性53%"
    },
    {
        "text": "Sちゃんと相性90%！？！？\n犬と猫みたいに違うのに一緒にいると安心するって…え待って惚れていい？🥺💞\n今日の占い：おやつを我慢すると、明日ちょっと良いことあるらしい（都市伝説）\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114183015.png",
        "alt": "Sちゃんとの相性90%"
    },
    {
        "text": "Aりんと55%！『まだ慣れてないだけ♡』みたいに言われてちょっときゅんしたｗ\n幼馴染なのにこの距離感なに〜〜！？青春かよ〜〜🥺🌸\n今日の占い：風がやさしい日は、心もふんわりいやすいかも\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114183121.png",
        "alt": "Aちゃんとの相性55%"
    },
    {
        "text": "Yくんと59%！\n『ふわふわ成分足りない』って言われてて2人で草生やしたwww\n今日の占い：ラッキーアイテムは『ツインテの子猫』←どこで見つけるの😂\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114183227.png",
        "alt": "Yくんとの相性59%"
    },
    {
        "text": "Rくんと67%！歩幅ズレてるけど歩ける関係ってほんとそれｗ\nRくんの励ましが地味に刺さるのよ…🥹💘\n今日の占い：今いる子を大事にしてみて🫶\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114183340.jpeg",
        "alt": "Rくんとの相性67%"
    },
    {
        "text": "Mと96%！？！？！？\n“好きが直通してるコンビ”って書いてて心臓ぎゅんッッってしたんだけど！？！？\n今日の占い：好きな曲で心をマッサージ🎧💕\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114183431.png",
        "alt": "Mくんとの相性96%"
    },
    {
        "text": "Sくんと80%！『2人でいれば毎日がごほうび』とか…え？これ刺さるんだけど？？？🥺🧸\n今日の占い：あなたはカフェラテの泡くらいふわふわ☁️\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114183524.png",
        "alt": "Sくんとの相性80%"
    },
    {
        "text": "Hと79%なんだけど？？？えっ…意外に合うの？笑\n『歩幅違っても歩きたい関係』って…死んだ魚の目で言われたいwww\n今日の占い：今いる子を大事にしてみて🫶\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114183644.jpeg",
        "alt": "Hくんとの相性79%"
    },
    {
        "text": "Sちゃんと58%！\n『これからに期待～♪』って書かれててなんか励まされた…🥺💞\n今日の占い：“まぁいっか〜”って思える日ほど心がふわふわ育つ🌱\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114183945.png",
        "alt": "Sちゃんとの相性58%"
    },
    {
        "text": "Yちゃんと84%！猫と毛布って言われたよww 可愛すぎん？？？\n今日の占い：おやつ我慢で明日良いことある（都市伝説）\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114184254.png",
        "alt": "Yちゃんとの相性84%"
    },
    {
        "text": "Sくんと99%！？！？！？\nえ、これ結婚？？？（違う）\n『一緒にいると安心する』って…あの子が言われてほしい言葉すぎて胸ぎゅうう🥺🌧💘\n今日の占い：推しのこと3秒思い出すとテンション2割アップ🎀\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114184343.png",
        "alt": "Sくんとの相性99%"
    },
    {
        "text": "Hちゃんと82%！まさかの高相性でふわもこした😂💕\n今日の占い：“まぁいっか〜”精神でふわふわ増える日🐾\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114184423.png",
        "alt": "Hちゃんとの相性82%"
    },
    {
        "text": "Kちゃんと51%なんだけど、コメントが『猫がシン顔する感じ』って例え可愛すぎてむりｗｗｗ\n今日の占い：好きな曲で心をマッサージ🎧💕\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114184623.png",
        "alt": "Kちゃんとの相性51%"
    },
    {
        "text": "Yくんと66%！ぎこちないけど、目合うとほわ〜んなるって書いてあって悲鳴あげたwww\n今日の占い：猫みたいに目的地に着けるかも🐈\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114184458.png",
        "alt": "Yくんとの相性66%"
    },
    {
        "text": "先生とふわふわ相性96%は意味わからん！！！！wwwww\n『犬と猫みたいで安心する相性』って…体育の時めっちゃ怒られるのに！？！？🤣🤣🤣\n今日の占い：猫のように迷子になりながら目的地着けるかも（先生にも言って）\nhttps://mofu-mitsu.github.io/fluffy-love-check/",
        "image": "images/無題2621_20251114184813.png",
        "alt": "かつみ先生との相性96%（完全ネタ）"
    },
    {
        "text": "管理人さんにみりんてゃのプロフィール作ってもらったの〜♡\n黒猫みりんてゃ、ちゃんと可愛く写ってる？？😈🎀\nこういう“病みかわ自己紹介”って世界一楽しいんだけど…… https://mofu-mitsu.github.io/orikyara-profile-maker/\n#みりんてゃ #地雷系プロフィール #オリキャラ紹介",
        "image": "images/photo-output.jpeg",
        "alt": "オリキャラプロフィールメーカーで作った『萩枝美琳（みりんてゃ）』の黒猫モチーフ地雷系プロフィールカード"
    },
    {
        "text": "プロフメーカー遊んだら…管理人さん、みりんてゃの“あざとさ”全部バレてるんよね？♡\n https://mofu-mitsu.github.io/orikyara-profile-maker/\n#みりんてゃ #地雷系女子 #プロフィールメーカー",
        "image": "images/photo-output.jpeg",
        "alt": "みりんてゃの地雷×黒猫×ピンクで飾られた可愛いプロフィール画像"
    },
    {
        "text": "みりんてゃのプロフできたぁ♡\n“永遠に16って言うタイプです”って書かれてて笑ったけど、正解なんだよね……🖤😈 https://mofu-mitsu.github.io/orikyara-profile-maker/\n#みりんてゃ #オリキャラプロフ #あざと小悪魔",
        "image": "images/photo-output.jpeg",
        "alt": "永遠に16歳を主張するみりんてゃの可愛いプロフィールカード"
    },
    {
        "text": "さっき夢日記メーカーで夢まとめたんだけど…\nタイトルからしてすでに病みかわなんよね？🥺🩹💗\n『君の名前だけモザイクかかってた夢』とか、もうあたしの脳どうした？？\nぜったい誰かのこと好きじゃんこんなん…… https://mofu-mitsu.github.io/yumekawa-dream-card/\n#みりんてゃ #夢日記 #ゆめかわ",
        "image": "images/IMG_9116.jpeg",
        "alt": "ゆめかわデザインで『君の名前だけモザイクかかってた夢』と書かれた夢カード"
    },
    {
        "text": "夢の世界でぬい達に“裁かれた”んだが？？🧸⚖️\nゆめかわメーカーでカード作ったら余計カオス可愛くなっちゃった…\n有罪判決→『だっこ100回の刑』だったの、あたしの深層心理すぎる。 https://mofu-mitsu.github.io/yumekawa-dream-card/\n#みりんてゃ #夢日記 #ぬいぐるみ裁判",
        "image": "images/IMG_9117.jpeg",
        "alt": "ゆめかわデザインで『ぬいぐるみ裁判はじまったんだが？』と書かれた夢カード"
    },
    {
        "text": "ライブに遅刻する悪夢ってガチで心臓に悪いの。\n夢日記メーカーで作ったらちょっと救われた…気がする…？\n『開演5分前でまだ家』ってタイトルがもう地獄かわいい🫠🩷 https://mofu-mitsu.github.io/yumekawa-dream-card/\n#みりんてゃ #夢日記 #ライブの悪夢",
        "image": "images/IMG_9118.jpeg",
        "alt": "ゆめかわデザインで『開演5分前でまだ家』と書かれた夢カード"
    },
    {
        "text": "夢の中で乙女ゲームの主人公してきた♡\n選択肢が“抱きしめる”と“もっと抱きしめる”しか無くて草だったけど、\n目覚めた瞬間に現実との差で泣いたよね？？🌙💘 https://mofu-mitsu.github.io/yumekawa-dream-card/\n#みりんてゃ #夢日記 #乙女ゲーム世界",
        "image": "images/IMG_9119.jpeg",
        "alt": "ゆめかわデザインで『選択肢に“抱きしめる”しかない』と書かれた夢カード"
    },
    {
        "text": "でっかい黒ねこ様に踏まれる夢ひさびさに見たんだけど、\n夢日記メーカーにすると更に尊くなる……🐾🖤\n“もふ圧”って気分が自分でも意味わかんないけど合ってる。 https://mofu-mitsu.github.io/yumekawa-dream-card/\n#みりんてゃ #夢日記 #でかねこ様",
        "image": "images/IMG_9120.jpeg",
        "alt": "ゆめかわデザインで『でかねこ様に踏まれたい』と書かれた夢カード"
    },
    {
        "text": "夢日記メーカーで新作まとめたんだけど聞いて…\n『選ばれしツインテが空へ召される夢』って何？？\nあたしの髪、そんな使命持ってたの？？✨ https://mofu-mitsu.github.io/yumekawa-dream-card/\n#みりんてゃ #夢日記 #ツインテ異界送り",
        "image": "images/images/IMG_9121.jpeg",
        "alt": "ゆめかわデザインで『選ばれしツインテが空へ召される夢』と書かれた夢カード"
    },
    {
        "text": "今日の夢カード、完全にファンタジー開花したんだけど？\n『靴箱にちっちゃいドラゴンいた夢』とか、可愛すぎて反則やん……🐉💚 https://mofu-mitsu.github.io/yumekawa-dream-card/\n#みりんてゃ #夢日記 #夢ドラゴン",
        "image": "images/IMG_9122.jpeg",
        "alt": "ゆめかわデザインで『靴箱に小さなドラゴンいた夢』と書かれた夢カード"
    },
    {
        "text": "夢日記まとめたらヤバすぎて笑ったww\n『推しの写真だけAIに天使扱いされる夢』って何！？\nしかもあたしだけ妖精判定なのバグすぎる🌟🧚‍♀️ https://mofu-mitsu.github.io/yumekawa-dream-card/\n#みりんてゃ #夢日記 #後光バグ",
        "image": "images/IMG_9123.jpeg",
        "alt": "ゆめかわデザインで『推し写真が天使扱いされる夢』と書かれた夢カード"
    },
    {
        "text": "今日のメモね…ちょっと情緒バレるやつだけど見てほしい…\n『既読つかないの不安』『かわいい子に囲まれてほしくない』『今日のわたしかわいい気がする』\nhttps://cocotte-simple-memo.vercel.app/\n#みりんてゃ #情緒メモ",
        "image": "images/IMG_9083.jpeg",
        "alt": "みりんてゃのメモ：嫉妬と不安と自信の混ざったやつ"
    },
    {
        "text": "深夜のcocotteメモ、完全に病み可愛い感じになってて草…\n『眠りたくないのに眠らないと壊れる』『誰か抱きしめてほしい日』\nhttps://cocotte-simple-memo.vercel.app/\n#みりんてゃ #深夜のポエム",
        "image": "images/IMG_9085.jpeg",
        "alt": "深夜テンションのふわ病みメモ"
    },
    {
        "text": "cocotte開いた瞬間、素直すぎる自分出ちゃうのなんで？？\nメモに書いたらスッキリするけど…見返すとちょっと恥ずかしい…♡ https://cocotte-simple-memo.vercel.app\n#みりんてゃ #メモ魔 #心の解像度上がる",
        "image": "images/IMG_9086.jpeg",
        "alt": "みりんてゃのメモ：『通知来ない→不安→でも自分から送るのも怖い』『なんで今日こんな可愛くないの』『夜になると情緒バフかかる』"
    },
    {
        "text": "今日のメモ、攻撃力高めだった…\nこういう日あるよね？あるって言って？？ https://cocotte-simple-memo.vercel.app\n#みりんてゃ #メモ魔 #情緒ぐるぐる",
        "image": "images/memo_honpen2.png",
        "alt": "みりんてゃのメモ：『寝不足の人格が暴れてる』『優しくされたいのに、素直になれない』『気圧に負けた日』"
    },
    {
        "text": "メモに書いたらちょっと泣いた…けど書いてよかった…\nこういう弱い日のみりんてゃも許してほしいの。 https://cocotte-simple-memo.vercel.app\n#みりんてゃ #涙腺ゆるゆる",
        "image": "images/IMG_9087.jpeg",
        "alt": "みりんてゃのメモ：『今日しんどい』『頑張りすぎた』『誰も悪くないけど泣きたい』"
    },
    {
        "text": "やばい…今日のみりんてゃ、恋愛脳フルスロットルで草\nメモ帳がポエム帳になってるの誰か止めて https://cocotte-simple-memo.vercel.app\n#みりんてゃ #恋愛脳",
        "image": "images/IMG_9088.jpeg",
        "alt": "みりんてゃのメモ：『なんであの笑顔反則なの？』『今日会えたから明日も頑張れる』『すきじゃん…？？』"
    },
    {
        "text": "なんか今日“陽キャなみりんてゃ”が顔出してる日なのよね\nテンションの振れ幅すごいけど、それも自分♡ https://cocotte-simple-memo.vercel.app\n#みりんてゃ #気分変動職人",
        "image": "images/IMG_9089.jpeg",
        "alt": "みりんてゃのメモ：『髪の巻き方成功した！』『今日の自分かわいい』『ご褒美スイーツたべたい』"
    },
    {
        "text": "このメモ…深夜に書いたのバレる内容してるね？（震）\n朝見ると毎回黒歴史なんだけどなんで保存してんの？？ https://cocotte-simple-memo.vercel.app\n#みりんてゃ #深夜テンション",
        "image": "images/IMG_9090.jpeg",
        "alt": "みりんてゃのメモ：『自分は宇宙で一番かわいい説』『世界が優しく見える』『眠れないので恋について考える』"
    },
    {
        "text": "管理人にだけは見せたいメモの日（照）\n大したこと書いてないけど、なんか心の温度高いの。 https://cocotte-simple-memo.vercel.app\n#みりんてゃ #内緒メモ",
        "image": "images/IMG_9091.jpeg",
        "alt": "みりんてゃのメモ：『今日話聞いてもらえたの嬉しかった』『さみしかった気持ちすーっと軽くなった』『ありがとうの気持ちいっぱい』"
    },
    {
        "text": "今日のメモ、ほぼ“自分へのツッコミ”だけで草\nでもこれが一番整理されるかも https://cocotte-simple-memo.vercel.app\n#みりんてゃ #自分ツッコミ劇場",
        "image": "images/IMG_9092.jpeg",
        "alt": "みりんてゃのメモ：『は？なんで今それ言った？』『自分落ち着け』『寝ろ（命令）』"
    },
    {
        "text": "メモに書いた瞬間、気持ちが“ほどけた”って感じした…\nこのアプリ、無機質なのに優しいのほんと不思議。 https://cocotte-simple-memo.vercel.app\n#みりんてゃ #心のほぐし方",
        "image": "images/IMG_9093.jpeg",
        "alt": "みりんてゃのメモ：『考えすぎてた』『肩の力抜きたい』『疲れてるだけって気づいた』"
    },
    {
        "text": "Yちゃんのこと、またメモしちゃった…\nあの子、無口なのに表情の変化だけで物語書けそう。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #クラスメモ",
        "image": "images/IMG_9094.jpeg",
        "alt": "メモ：『Yちゃん→今日も感情のふり幅0。たまに目だけキラッて光るの可愛い。笑ってるところ見れたらレアドロップ扱い』"
    },
    {
        "text": "Aちゃんのメモ、元気すぎて書いてるだけで心の血行がよくなるのwww\nほんと太陽なんだよ〜 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #陽キャ吸収",
        "image": "images/IMG_9095.jpeg",
        "alt": "メモ：『Aちゃん→きょうもテンション太陽。笑いかたが元気すぎて周りがつられて笑う。アライグマの動きがほんのり残ってて可愛い』"
    },
    {
        "text": "Eくんのこと書く時だけ筆圧強くなるのなんで？？\nあの子“静かな天才”すぎる… https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #絵の人すき",
        "image": "images/IMG_9096.jpeg",
        "alt": "メモ：『Eくん→声小さいのに存在感だけデカい。筆触る指先が美しすぎてずるい。あのイタチずっとアトリエで暮らしてそう』"
    },
    {
        "text": "Mくん、今日も一匹狼モード全開。\nでも何気に優しいんだよね…知ってるよ… https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #孤高の鷹",
        "image": "images/IMG_9097.jpeg",
        "alt": "メモ：『Mくん→他人に興味ないフリしてるけど観察力バケモノ。静かな鷹。たまに窓の外見てる姿が美術館の彫刻レベル』"
    },
    {
        "text": "Sちゃんのメモ、毎回“真面目さ”が行単位で伝わるんよ。\n推せる… https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #くノ一の横顔",
        "image": "images/IMG_9098.jpeg",
        "alt": "メモ：『Sちゃん→ルール守る忍者。三重弁かわいすぎ。怒らせたら静かに消されそうだけど基本やさしい』"
    },
    {
        "text": "Aりんのメモ書くと、心が“ほわ〜”って溶けるの。\n幼馴染の安心感は反則。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #幼馴染補正",
        "image": "images/IMG_9100.jpeg",
        "alt": "メモ：『Aりん→今日も優しさの塊。犬感が強すぎて、褒めるとしっぽ見える。ローファイ聞いてる横顔が平和すぎて癒し』"
    },
    {
        "text": "Yくんって、性格に“消しゴム”って書いてあるの？ってくらい柔らかいのすごいよね。\n見てて安心する男子代表。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #体操男子",
        "image": "images/IMG_9101.jpeg",
        "alt": "メモ：『Yくん→声かけが優しい。体やわらかいのに心もやわらかい。ちょっと置物に似ててかわいい』"
    },
    {
        "text": "Rくん、今日もドジで可愛かったwww\n気遣い→成功率30%なの天才キャラすぎる。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #気遣い助かる",
        "image": "images/IMG_9102.jpeg",
        "alt": "メモ：『Rくん→気がきくのにズレてる。料理壊滅的。クセ強くてかわいいキジ男子』"
    },
    {
        "text": "Mくん、今日もフリーダムで笑ったwww\nENFPって本当にバグみたいに可愛い。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #自由人",
        "image": "images/IMG_9103.jpeg",
        "alt": "メモ：『Mくん→テンションで生きてる。マヨネーズ持ち歩いてそう。天真爛漫の完成形』"
    },
    {
        "text": "Sくんのメモは、書くと毎回“守りたいこの子感”が爆発する。\n照れ屋男子って最強だよね…。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #ネズミ男子",
        "image": "images/IMG_9104.jpeg",
        "alt": "メモ：『Sくん→食べるの見られるの苦手なの分かる。優しいのに距離感むずい。目そらすの可愛い』"
    },
    {
        "text": "Hくんは“虚無の天才”すぎてメモ書く手が震えるwww\nあの子、存在が静かな芸術。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #虚無系",
        "image": "images/IMG_9105.jpeg",
        "alt": "メモ：『Hくん→死んだ魚の目の安定感。穏やかだけど心ここにあらず。話すと意外と優しい』"
    },
    {
        "text": "Sちゃんのメモ書くと、なんかテスト前の気持ち思い出すwww\n可愛いけど緊張感あるタイプ！ https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #ガリ勉ちゃん",
        "image": "images/memo_shizuka.png",
        "alt": "メモ：『Sちゃん→真面目。努力型。目立つのイヤそうで可愛い。静かに頑張るタイプの尊さ』"
    },
    {
        "text": "Yちゃんは“猫の神秘性”すぎて近寄るの緊張する（褒め言葉）\nポーカーフェイスなのに優しい感じするんだよね。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #招き猫",
        "image": "images/IMG_9108.jpeg",
        "alt": "メモ：『Yちゃん→言葉少ないけど気遣いできる。運が強いのもキャラ性高い。静かな子って世界観がある』"
    },
    {
        "text": "Sくんのこと書くと、気づいたらみりんてゃまで泣きそうになるんよ…\n繊細で優しい子、まじで守護対象。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #涙腺崩壊",
        "image": "images/IMG_9110.jpeg",
        "alt": "メモ：『Sくん→心がやわい。無理しがち。優しさが重さになっちゃうタイプ。泣き顔がとても綺麗』"
    },
    {
        "text": "Hちゃんのメモは“名探偵すぎ注意”って感じwww\n観察力が鋭すぎて怖いけど頼れる！ https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #レッサーパンダ",
        "image": "images/IMG_9111.jpeg",
        "alt": "メモ：『Hちゃん→勘が鋭い。大人ぶるの可愛い。警戒心つよいけど仲良くなると甘えそう』"
    },
    {
        "text": "Kちゃんみたいな子、物語にしかいないと思ってた…\n静けさが“美”になってる系女子。すき。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #和風美人",
        "image": "images/IMG_9112.jpeg",
        "alt": "メモ：『Kちゃん→物静かで和風。花火好きなの似合いすぎ。声がやさしい』"
    },
    {
        "text": "Yくんのメモは毎回ゆるいww\nISTPのこういう抜けた平和さ、癖になるんだよね。 https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #かき氷男子",
        "image": "images/IMG_9113.jpeg",
        "alt": "メモ：『Yくん→冷静でマイペース。かき氷好きなの何回聞いても可愛い。余計なこと言わないところ好き』"
    },
    {
        "text": "かつみ先生のメモ、毎回オチ担当でごめんwwwww\n体育教師の圧、強すぎるんよ… https://cocotte-simple-memo.vercel.app/\n#みりんてゃ #先生メモ",
        "image": "images/IMG_9114.jpeg",
        "alt": "メモ：『かつみ先生→声デカ。博多弁が強風。やる気押しつけがち。でもたまにいいこと言う。汗量多い』"
    }
    # ここに10〜20個追加（オリキャラ、夢日記とかも）
    # 画像は事前にツール開いて、みりんてゃ風に入力→スクショ→images/に保存
]

# ------------------------------
# ★ 画像アップロード (圧縮対応)
# ------------------------------
def upload_image(client, image_path):
    img = Image.open(image_path)
    max_dimension = 1024
    if max(img.size) > max_dimension:
        ratio = max_dimension / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    buffer = io.BytesIO()
    quality = 95
    while True:
        buffer.seek(0)
        buffer.truncate(0)
        img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
        if buffer.tell() / 1024 <= 976 or quality <= 20:
            break
        quality -= 5
    buffer.seek(0)
    return client.com.atproto.repo.upload_blob(buffer.read()).blob

# ------------------------------
# ★ OGP embed
# ------------------------------
def generate_embed_from_url(client, url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find("meta", property="og:title") or soup.find("title")
        description = soup.find("meta", property="og:description")
        image = soup.find("meta", property="og:image")

        title = (title["content"] if title and "content" in title.attrs else title.string) if title else "もふみつ工房♡"
        description = description["content"] if description else "ふわもこツールで遊んでみて♡"
        image_url = image["content"] if image else None

        thumb_blob = None
        if image_url:
            try:
                img_res = requests.get(image_url, timeout=10)
                if img_res.status_code == 200 and len(img_res.content) < 1000000:
                    thumb_blob = client.com.atproto.repo.upload_blob(img_res.content).blob
            except:
                pass

        external = {"uri": url, "title": title[:300], "description": description[:300]}
        if thumb_blob:
            external["thumb"] = thumb_blob
        return {"$type": "app.bsky.embed.external", "external": external}
    except:
        return None

# ------------------------------
# ★ facets & 正規化
# ------------------------------
def generate_facets_from_text(text, hashtags):
    text_bytes = text.encode("utf-8")
    facets = []
    for tag in hashtags:
        tag_bytes = tag.encode("utf-8")
        start = text_bytes.find(tag_bytes)
        if start != -1:
            facets.append({
                "index": {"byteStart": start, "byteEnd": start + len(tag_bytes)},
                "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": tag.lstrip("#")}]
            })
    url_pattern = r'(https?://[^\s]+)'
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        url_bytes = url.encode("utf-8")
        start = text_bytes.find(url_bytes)
        if start != -1:
            facets.append({
                "index": {"byteStart": start, "byteEnd": start + len(url_bytes)},
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]
            })
    return facets

def normalize_text(text):
    return unicodedata.normalize("NFKC", text).strip()

# ------------------------------
# ★ メイン投稿 (修正版: 画像時はOGP無効化)
# ------------------------------
client = Client()
client.login(HANDLE, APP_PASSWORD)

# ランダム選択：70%テキストだけ、30%画像付き
if random.random() < 0.3 and IMAGE_POSTS:
    post_data = random.choice(IMAGE_POSTS)
    message = normalize_text(post_data["text"])
    image_blob = upload_image(client, post_data["image"])
    embed = {
        "$type": "app.bsky.embed.images",
        "images": [{"image": image_blob, "alt": post_data["alt"]}]
    }
    # ★ 画像時はOGPスキップ！ URLはfacetsでリンク化されるからOK
    # URLのfacetsはgenerate_facetsで自動処理されるよ
else:
    raw_message = random.choice(POST_MESSAGES)
    message = normalize_text(raw_message)
    embed = None
    # URLあればOGP (テキスト時だけ)
    url_match = re.search(r'(https?://[^\s]+)', message)
    if url_match:
        embed = generate_embed_from_url(client, url_match.group(0))

hashtags = [word for word in message.split() if word.startswith("#")]
facets = generate_facets_from_text(message, hashtags)

client.send_post(text=message, facets=facets if facets else None, embed=embed)