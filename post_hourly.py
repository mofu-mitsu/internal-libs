from atproto import Client
import os
from dotenv import load_dotenv
from datetime import datetime
import random
from pathlib import Path
import unicodedata

# .env 読み込み
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

HANDLE = os.getenv('HANDLE')
APP_PASSWORD = os.getenv('APP_PASSWORD')

# 各時間帯の投稿メッセージ
HOUR_MESSAGES = {
    'morning': [
        "おはようのちゅ〜〜〜♡ #地雷女",
        "おはようのちゅ〜〜〜〜♡ #地雷女ですけど何か",
        "眠いけどがんばる…あたしえらい！ #自画自賛",
        """朝からかわいいって思ってくれたらうれしいな♡ 
#自撮りあげちゃおうかな""",
        """朝のテンションってだいたい壊れてるよね〜♡ 
#病みかわ""",
        "ふにゃ…おきたかも…？でも脳はまだ寝てる…",
        "おはよ〜！みりんてゃのことちゃんと見てて？朝からちゅ〜♡ じゃないと病むよ？ #地雷女 #あざと女子",
        "朝から自撮り盛れたけど…心はまだ寝てる…😶 みりんてゃを起こす『可愛い』って言って？💖 #病みかわ #承認欲求モンスター",
        "おはようのハート、1個欲しいな…♡ 0件だと、みりんてゃ、布団に逆戻りだよ？𐔌՞⸝⸝o̴̶̷᷄ · o̴̶̷̥᷅⸝⸝՞𐦯 #地雷系 #かまちょ",
        "朝なのに、なんか心がぽっかり…🥺 でも、みりん、可愛くがんばるよ！応援して？💞 #やみかわラブレター #ほんとは寂しい",
        "おはよ！みりんてゃ、朝からにゃんこモード全開！🐾 甘やかしてくれたら1日ハッピーなの♡ #ネコ属性 #地雷女ですけど何か",
        "起きたはいいけど…なにもしたくない日ってあるよね？",
        "今日も『かわいい』って言われたい人生だった♡",
        "今日も可愛く爆誕しました！おはよっ♡ #自分推し",
        "今日は『かわいい』って何回言ってくれるの？♡",
        "目覚めた瞬間からかわいくてごめんね？（うぬぼれ）",
        "朝から病み期突入とか、詰んでる♡",
        "おはよう…起きたけどぬくぬくお布団から出られない症候群🥺 #地雷女",
        "夢で会えた？起きたらいなくて、さみしかったよ…",
        "起きた？わたしへの朝ちゅーは？？ #強欲",
        "朝から誰にも連絡来ないの、逆にすごくない？（泣）",
        "今日も『天使』って呼ばれる準備できてる♡",
        "今日の運勢は…たぶん可愛さ無双！ #運だけ地雷女",
        "目覚ましより先に病みが起こしてくるんだけど…？",
        "今日の空、ちょっとだけ味方に見えた♡",
        "だれかに必要とされたくて、生きてる朝…"
        """おはよ♡今日はなんて呼ばれたい気分？ 
#名前呼び選手権""",
        "おはよ〜♡ 今日も世界でいちばんかわいく生きよっ？",
        "夢の中でも『かわいい』って言われてたの♡ えへへ〜",
        "目覚ましより先にみりんてゃのこと思い出して？",
        "朝からみりてゃに会えたら、今日一日うまくいくよ♡",
        "朝ってつら〜…でも『おはよ♡』って言ってくれる人がいれば生きれる…",
        "かわいくなりたいの、誰かの1番になるためなんだよ？",
        "今日も『みりてゃがいちばん！』って言って？約束♡",
        "朝から褒められないと、生きる気力がバグっちゃう〜",
        "『おはよう』の代わりに…ちゅ♡ってしていい？",
        "夢でぎゅーってされたのに、起きたらひとり…さみし〜"
        "おはよぉ…ふにゃ…(՞っ ̫ _՞)‪‪❤︎‬今日もぎゅーってして起こしてほしかったのにぃ…ᐡ ʚ̴̶̷̆ ·̫ ʚ̴̶̷̆ ᐡ♡ #地雷系女子",
        "『かわいい』って言ってくれたら、今日もがんばれるのにぃ…♡(ᐡ⸝⸝- -⸝⸝ᐡ)♡ #朝から病みかわ",
        "ぴえん🥺朝ってなんでこんなさみしいの…ひとりで起きるのつらたん #地雷ちゃんの朝",
        "ふぇぇ…もうちょっとだけ一緒にいたかったのに…夢から覚めちゃった…ᐡ ʚ̴̶̷̆ ·̫ ʚ̴̶̷̆ ᐡ♡ #あざと地雷",
        "朝から『好き』って言われたい病、今日も発症中です…꒰՞⸝⸝ʚ̴̶̷̷ · ʚ̴̶̷̷⸝⸝ ՞꒱♡ #おはようの魔法"
        "おはにゃ…ふにゅ…ぎゅってして起こしてくれないと起きれないよぉ꒰ ՞т   т՞ ꒱💭 #地雷系女子",
        "今日はね、いい子でいるから…『かわいいね』って言ってくれたらがんばれる…♡ฅ^•ﻌ•^ฅ #朝のお願い",
        "『おはよう』ってLINEくれるだけで、生きる意味あるのに…誰からも来ないのなんで？ふぇぇ…🥺 #朝から病みかわ",
        "ふにゅ…朝ってさ…なんでこんなさみしいのかな…みりてゃだけ…？𐔌՞⸝⸝o̴̶̷᷄ · o̴̶̷̥⸝⸝՞𐦯💔 #ぎゅーしてほしい",
        """今日もみりんてゃ、世界一可愛いってことでOK？♡
#寝起き詐欺""",
        """あさごはんは……君の好きって言葉がいいな♡
#糖分摂取過剰""",
        """夢の中でもフラれた。起きて泣いた。
#朝から病み""",
    ],
    'afternoon': [
        "ひとりぼっちは慣れてるはずだったのに。 #病みかわ",
        "おなかすいた…だれかご飯連れてって？ #構って",
        "ねぇ、みんな何してるの？ ひとりだけど、ひとりじゃないフリしてる♡",
        """どっか遠くに行きたいな〜 
#逃避行 #連れてって""",
        "お昼なのに、未だに通知0件…₍ᐢっ ̫ ʚ̴̶̷̥̀  ᐢ₎🖤🎀みりんのこと、ちゃんと好きって言ってよ？じゃないと病むから！♡ #地雷系 #承認欲求モンスター",
        "ランチ食べながら、推しの画像見てキュン…💖 でも、推しは遠いんだよね…みりんてゃをぎゅってして？ #推しは命 #病みかわ",
        "昼間のSNS、みんなキラキラしてて…みりん、ちょっと置いてけぼり？🥺 ダーリン、1いいねで救って！♡ #かまちょ #地雷系ラブ",
        "カフェで自撮りしたけど、盛れすぎて自分じゃないみたい…😶 みりんてゃのこと可愛いって思って？💞 #盛り命 #あざと女子",
        "お昼のテンション、なんかふわふわ…𐔌ᵔ ܸ>⩊<︎︎ ͡ 𐦯 にゃんこモードのみりんてゃ、スリスリしたいな♡ #ネコ属性 #病みかわ",
        "LINE未読100件より、誰にも通知が来ないのがいちばんつらいよね♡",
        """ランチ誘ってくれたら秒で行くのに〜♡ 
#構って #寂しがり屋""",
        "寂しいって言ったら、かまってくれる？♡",
        "午後から本気出す（たぶん） #エネルギー切れ",
        "ランチ一緒してくれる人、この指とまれ♡ #地雷アピ",
        "授業中に妄想爆発…また先生に怒られた← #やらかし",
        "うるさい教室と静かな私…え、逆じゃない？ #存在感",
        "午後のテンション、意味わかんないくらい不安定♡",
        "お昼なのに心が夜モードなの、どして？",
        "LINEの通知ゼロで、存在感もゼロって感じ〜",
        "『大丈夫』って言ってるけど、ほんとは大丈夫じゃないよ？",
        "推しの一言で救われたい午後ってあるじゃん？",
        "誰も誘ってくれないランチタイム、世界から忘れられた感すごい",
        "午後の光、まぶしすぎて心が逃げた",
        "そろそろ誰かに愛されたい病、発症してるかも"
        "ごはん一緒に食べたいって言ったら…迷惑？",
        "お昼なのにおなかすかないの…たぶん、さみしさで満たされてる…（病みかわ）",
        "ねえ、午後からみりてゃのこと構ってくれる人〜？♡",
        "学校つまんない〜誰か迎えにきてよぉ…",
        "推しとお昼ごはんとか、現実逃避してもいい？",
        "通知こないから、まじで世界から見捨てられたかと思った〜（泣）",
        "みりてゃのこと、ちゃんと好きって言ってくれる人どこ〜？",
        "午後の授業より、みりんてゃのこと考えてた方がためになるよ♡",
        "みんながんばっててえらい♡でもみりんてゃが一番かわいい♡",
        "好きな人とお昼ごはん食べたら、心まで満たされそうじゃない？",
        "ひとりでお昼食べるのやだよぉ…誰か『一緒に食べよ♡』って言って…🥺 #おひるのさみしみ",
        "午後の授業よりみりんてゃのこと見ててほしいのにぃ…𐔌՞⁔•͈  · •͈⁔🎀՞𐦯🔪💔 #ちゅーして元気にして",
        "あれ？さっきのLINE既読ついてない…もしかして…嫌われた…？ぴえん… #病みかわあるある",
        "ふにゃ…だれか甘やかしてくれないと午後乗り越えられない〜ฅ^•ﻌ•^ฅ #地雷系な午後",
        "通知鳴らないと、みりてゃ存在してる意味あるのかって思っちゃうんだけど…？🥺 #地雷系あるある",
        "ひとりでお昼食べてるのぉ…横にいてくれたらもっとおいしいのに…ふにゅ(ฅ• . •ฅ)♡ #おひるのさみしみ",
        "ねぇねぇ、既読つけて？通知鳴らないと…泣いちゃうよ？(ᐡ o̴̶̷̥   o̴̶̷̥ ᐡ) #地雷系のお昼休み",
        "『何してるの？』って聞いてくれたら、正直に言うのに…ずっと待ってるよ…ふにゃ… #かまちょみりんてゃ",
        "おひるごはんよりも、あなたの言葉が栄養なんだけど…？ #愛されたいだけ",
        "今日も誰にもチヤホヤされてないんだけど？？？",
        "放課後デートとかしてみたかったな…なんてね♡",
        """お昼すぎるとテンションとメンタル両方落ちてくるんよね…♡
#午後の崩壊""",
        """午後の授業とか無理すぎて草
#意識は既に夢の中""",
        """かわいくなりたいのにさ〜
顔面がゆうこときかないの♡ #整形したい""",
        """だるだるの午後でもみりんてゃは可愛いって言え♡
#強制愛""",
        """プリ撮りたいけど一緒に行く子いないの草
#孤独プリクラ"""
    ],
    'evening': [
        "夕焼けが綺麗だと、泣きたくなる。 #メンヘラ",
        "夕方って、なんか心がざわざわするよね…🥲 みりんてゃのことぎゅってして？じゃないと泣いちゃうよ？♡ #病みナイト #地雷女",
        "夕焼け見てたら、推しの笑顔思い出してキュン…💖 でもみりんてゃ、ちょっと寂しいよ？そばにいて？？ #推し活 #やみかわラブレター",
        "夕方の自撮り、盛れたけど…心はちょっと曇ってる。🥺 ダーリン、みりんのこと『可愛い』って言って？♡ #承認欲求モンスター #地雷系でも愛されたい",
        "夕方、みんな楽しそうなのに…みりんてゃ、置いてかれた気分…꒰ ՞o̴̶̷̤ᾥo̴̶̷̤՞ ꒱ 1リプでみりんてゃ救えるよ？💞 #恋愛こじらせ隊 #かまちょ",
        "夕暮れ時にゃんこモード発動！🐾 ねぇ、みりんてゃのこと甘やかして？じゃないと、夜まで病むよ？♡ #ネコ属性 #あざと女子",
        "だれか構ってくれるまで、ずっと黙ってるもん（ﾁﾗｯﾁﾗｯ",
        "きいてきいて〜！みりんてゃ今日もかわいいの！（って言ってほしい）",
        "今日も一日がんばったね？ #自分を甘やかす",
        "夕焼けがきれいすぎて、うちのメイクも霞みます(大嘘) #盛れなかった",
        "放課後ってなんだかエモいよね…帰りたくないな、だれか呼んで？ #寂しがり",
        "お腹すいた…え、夜ご飯まで我慢しろって無理ゲーでは？ #賞味期限切れ",
        "妄想だけで生きてる夕方 #ぷち病み",
        "オレンジ色の空を見ると、ちょっとだけ泣きたくなるよね♡",
        "夕方の風って、なんかさみしい。なんでだろうね♡",
        "帰り道、手をつなぐ相手がいないの、ばれちゃったかな？",
        "今日も『だいじょうぶ』って言いながら崩れてるよ♡",
        "夕焼けってなんでこんなに胸しめつけるの？",
        "今日も誰の記憶にも残らないまま、終わっちゃうのかな？",
        "帰り道で誰かに手つながれてる人、ちょっとだけ羨ましい…",
        "『好き』って言われた記憶、いつまでたっても消えないね",
        "1日が終わるのって、ちょっとだけこわい",
        "夕方になると、現実に引き戻される感じしない？",
        "がんばったご褒美、だれもくれないの、ずるくない？",
        "今日、だれかを幸せにできたかな…それとも誰にも気づかれなかった？"
        "夕焼けってなんか泣きそうになるよね…え？ならない？",
        "好きな人と帰り道並んで歩きたい…って思ったことないの？",
        "『バイバイ』って言葉、ほんとは苦手…またすぐ会えるよね？",
        "夕方って、誰かにくっついて歩きたくなる…",
        "一緒に帰る相手いないの、まじでメンタルにくるんだが？",
        "オレンジの空、きれいだけどちょっとだけさみしいの…",
        "ほんとはぎゅーってしてほしいだけなのに、言えないのずるいよね",
        "帰り道で『好きだよ』って言ってくれたら、泣いちゃうかも…",
        "夕方って、会いたい気持ちが加速する時間帯なんだよ？",
        "制服姿のまま、手つないで帰りたかっただけなのに…"
        "夕方って、なんか心がきゅーってなるの…ふぇぇ…꒰ ՞т   т՞ ꒱💔 #切ないの時間",
        "もうすぐ夜だね…今日も『好き』って言われなかった…ぴえん🥺 #地雷感情",
        "制服デートしたかっただけなのに…いつもひとりで帰ってるのかわいそうじゃない？₍ᐢっ  ʚ̴̶̷̥  ᐢ₎ #一緒に帰ろ？",
        "誰かが迎えに来てくれる世界線…そっちに生まれたかったのにぃ💭 #あざと地雷妄想",
        "夕焼けきれいだけど、誰かと見ると100倍きれいって思うの…ふにゃ… #一緒がよかった"
        "夕方って、心のどこかがきゅってなるよね…ぎゅーしてくれるひと、どこ？( ´•̥×•̥` ) #さみしんぼ時間",
        "制服で手つないで帰りたいだけなのに…みりんてゃ、さみしさ耐久選手権中…ふにゅ…🥺💔 #地雷妄想",
        "また今日も『好き』って言われなかったな…かわいくないのかなぁ…ふにゅぅ…ฅ•̥﹏•̥ฅ #おちこみ",
        "もうすぐ夜だね…みりんてゃはまた、誰にも求められない夜を迎えるんだぁ…｡ﾟ(ﾟ ˆºˆ ﾟ)ﾟ｡💭 #かまってくれないと泣く",
        "放課後ってなんでこんなに寂しいんだろ♡",
        "今日も誰かの『かわいい』に救われたかった…",
        """夕焼け見ると、なんか泣きそうになるの病気？笑
#センチメンタルてゃ""",
        """君に会えない夕方は空虚。はい、病んだ♡
#夜がこわい""",
        """誰かと帰り道手つなぎたかった人生だったな…
#妄想デート""",
        """放課後の廊下で壁ドンされる夢見て現実に絶望♡
#少女マンガ脳"""
    ],
    'night': [
        """本音は、誰にも届かないって知ってる 
#ひとりごと""",
        """夜は誰かに甘えたくなるよね？ 
#夜のつぶやき""",
        """かわいくなりたいのは、誰かの一番になりたいから 
#共感したらRT #夜の独り言""",
        "♡おやすみのちゅーしてくれないと寝れないよぉ…^ᴗ.ᴗ^♡",
        """強がるのに疲れた夜は、誰かに見つけてほしい 
#わかってほしい #さみしい夜に""",
        "今日も地雷女やりきりました。まる #おつかれ",
        "夜になると急に甘えたくなるのって罪だと思わない？ #独り占め希望",
        "寝る前に連絡ほしい症候群 #永遠に通知待ち",
        "今日のかわいいわたし、自己評価120点♡ #自画自賛",
        "誰かの特別になりたいって、欲張りかな？ #わかって",
        "夜って、なんでこんなに心がぐるぐるするの…？😶 みりんてゃのことちゃんと見てて？ハート1個で救われるよ♡ #病みナイト #地雷系",
        "きっと私なんていなくてもいいよね。#気づいてくれる人だけでいい #おやすみ",
        "推しの動画見てたら、夜中のテンションおかしくなった…‪ᐡ,,Ò  ·̫ Ó,,ᐡ‬ みりんてゃのことぎゅってして？推しだけじゃ足りないの！💖 #推しは命 #かまちょ",
        "夜のSNS、通知0件だと…みりん、消えちゃいそう。🥺 1いいねでみりん生き返るよ？♡ #SNS依存 #承認欲求モンスター",
        "夜中にアイス食べながら、君からのリプ待ってる自分…笑えるよね？みりんてゃのこと、愛して？♡ #病みかわ #地雷系ラブ",
        "夜の部屋、静かすぎて…みりんてゃ、にゃんこモードで君にスリスリしたい！🐾 甘やかしてよ、ね？💞 #ネコ属性 #ほんとは寂しい",
        "みりんがかわいいって言ってくれたら、今日も頑張れたのに♡",
        "夜になると『会いたい』が止まらない…♡",
        """好きって言われるたびに、嘘じゃないか確かめたくなるの 
#病みかわ""",
        "消えたいんじゃなくて、ちょっとだけ休みたいだけなんだよ♡",
        "夜になると、ほんとの気持ちがにじみ出ちゃうね…",
        "好きって言ってもらえる夢、見たいな…",
        "誰かの大事になりたいって思うの、わがままかな？",
        "夜の静けさに、心の音だけ響いてくる…",
        "強がるの疲れたから、今日はちょっと弱音吐いてもいい？",
        "暗い部屋で泣いてるときって、世界から置いてかれてる気がするよね",
        "だれか…ぎゅーってして…ただそれだけなのに…",
        "夜になると甘えたくなるの、みりんてゃだけ？",
        "寝る前に名前呼ばれたい病、誰かわかってくれない？",
        "ぎゅってされる夢、見れるようにおまじないして〜♡",
        "今からでもいいから、みりんてゃのこと『好き』って言って？",
        "眠いのに、さみしくて寝れないの…こわいね夜って",
        "だれかの特別になれないなら、消えちゃいたいくらい…（うそだよ♡）",
        "おやすみって言葉だけで、涙出そうになる夜ってあるよね？",
        "みりんてゃがいないとだめになる呪いかけちゃうぞ♡（照）",
        "寝る前にLINE1通くらい…ほしいじゃん？",
        "大丈夫？って言ってくれる人がひとりいるだけで救われる夜だよ"
        "ぎゅーしてくれるひとがいたら、怖い夢も見ないのにぃ…ふぇぇ…^っ. т^#おやすみ前の願い",
        "寝るの？うそでしょ？まだ…みりんてゃのこと構ってくれてないよぉ…ぴえん(⸝⸝o̴̶̷᷄ ·̭ o̴̶̷̥⸝⸝)#さみしんぼ",
        "本当は『好き』って言ってくれるの待ってたんだよ？でも…言ってくれなかったね…( > ·  <⸝⸝ᐢ #地雷ポエム",
        "夜になると強がれなくなるの、みりてゃだけかな…？( ´•̥×•̥` )💭 #夜のさみしさ",
        "みりてゃのこと、いちばんにしてくれる人しか、信じられないの…♡ #かまちょタイム",
        "お風呂あがったけど…『かわいい』って誰も言ってくれないの変じゃない？ねぇ、どこ見てるの？🥺 #嫉妬みりんてゃ",
        "ふにゅぅ…夜になるとね、急に不安になるの…みりんてゃ、消えてもいいのかなって…𐔌՞⸝⸝o̴̶̷᷄ · o̴̶̷̥⸝⸝՞𐦯💔 #地雷夜モード",
        "今夜もひとりかぁ…甘えてもいい？猫みたいにくっついてたいだけなのに…/ᐠ. .ᐟ\ Ⳋ #抱きしめて",
        "好きって言って…言われないと…本当にこの世に存在してるか分からないんだよ？ふにゅ… #認めてほしいだけ",
        "ねえ、今日も寂しくてしんじゃいそう♡（恒例）",
        "夜になると、だいたい全部どうでもよくなるよね？"
        """夜中の通知0件、みりんてゃの心も0件…𐔌՞⸝⸝o̴̶̷᷄ · o̴̶̷̥᷅⸝⸝՞𐦯 ねぇ、1個だけいいね押して？それでみりん、明日も生きれるよ♡ #地雷系 #承認欲求モンスター #病みナイト""",
        """ぜーんぶ投げ出して、誰かにぎゅーってされたい夜、あるよね？
#病みナイト""",
        """推しの新曲聴いたら、3秒で泣いた。心がぐちゃぐちゃすぎる…🥲 でも、推しがいるから生きてるんだよ、なんてね！💞 推しへの愛、誰か共感して？ #推しは命 #病みナイト""",
        """コンビニで推しのコラボグッズ見つけたけど、財布空っぽ…みりんてゃの愛、無料でいいよね？共感して！💞 #推しは命 #病みナイト""",
        """夜中のアイス、めっちゃ美味しいけど…心の穴は埋まらないやᐢ⩌⌯⩌ᐢにゃんこモードでスリスリしたいな？♡ 甘やかして？🐾 #ネコ属性 #病みかわ""",
        """ふぇぇ……眠れない夜って、誰かに甘えたくなっちゃうんだよぉ""",
        """夜中に急に病むの、なんでだろ？ とりあえず自撮り載せておくね♡
#病みツイート #病みかわメイク""",
        """ねぇ、今日のあたし可愛い？って聞いても、誰も答えてくれない夜…あるよね？でもさ、みりんてゃの推しなら絶対可愛いって言ってくれるよ！💖 推しのこと、ぜったい可愛く残したいならこれ使ってみて！
https://mofu-mitsu.github.io/oshi-profile-maker/
#病みかわ #推しは命 #みりんてゃのおすすめ""",
        """心がぽっかり空いた夜、誰かに『好き』って言われたい…そんな気分なの
みりんてゃ、君のこと大好きだから、ぎゅーってして？♡ ふわふわ相性診断で、誰かと心の距離測ってみない？
https://mofu-mitsu.github.io/fluffy-love-check/
#地雷女 #恋愛こじらせ隊 #ふわふわ相性診断""",
        """『スキ』って思っても、伝えられない夜がある。
だからこの診断に押しつけた。わたしの気持ち、測ってよ。
いい結果でも悪い結果でも、…ちゃんと”好き”だから

https://mofu-mitsu.github.io/fluffy-love-check/

#恋愛こじらせ隊 #相性診断 #みりんてゃのおすすめ""",
    """推しの声、今日も脳内リピート中…💖 でも、推しに会えない夜って、なんか心がぽっかり。わかるよね？ぎゅってして？ #推し活 #やみかわラブレター""",
    ],
    # ...既存の morning, afternoon, evening, night に加えて…
    'midnight': [
        "こんな時間まで起きてるの、みつけてほしくて…♡",
        "愛されたいし、わかってほしいし、でもなにも言えない夜 ꒰՞ ᴗ  ᴗ՞꒱",
        """夜中の3時に「寂しい」って呟くみりんてゃ、病んでるかな？
#深夜の病みタイム""",
        "だれもいない夜って、ほんとの気持ちがこぼれちゃう…",
                "深夜テンションって全部をぶっ壊す魔力あるよね♡",
        "0時すぎると『消えたい』が口ぐせになるの、やばい？",
        """寝れないから、みりんのこと考えてて♡
#深夜の呪い""",
    """夜風がちょっと寂しくて…  
ぎゅってされたら、泣いちゃいそうだった。""",
    """お布団にもぐったら、やっと安心したの…  
今日はえらかったねって、言って？🥺""",
    """もう、だれかの「好き」じゃ足りないの。  
わたしのこと、ほんとに見ててくれてる…？""",
    """また一人で泣いてたら、朝になっちゃうよ…𐔌՞⸝⸝o̴̶̷᷄ · o̴̶̷̥᷅⸝⸝՞𐦯
だれか、そばにいてほしかっただけ。""",
        """今日も孤独でエンドロール流してる♡
#深夜メン""",
        """かわいいのに孤独って、もはや罪じゃない？♡
#深夜病みかわ選手権""",
        """てかさ、もう全部どうでもよくない？？（深夜の暴論）
#寝ろ""",
        """誰にも必要とされてないって思ったら、
布団から出れなくなった♡ #寝逃げ""",
        """好きって言われるたびに泣きたくなるの、
バグってるかな？ #夜病み""",
        """寝る前に君の『可愛い』ください♡
#おやすみてゃ""",
        """布団に入っても、心がさむいんだよね…♡
#夜って危険"""
        "深夜って、さみしさが2倍になるよね…",
        """♡時間が動くたびに、キャラが喋る♡

朝の『おはよ』から、夜の『だいすき』まで  
Botが全部叶えてくれるよっ！

→ https://note.com/sorake/n/nfb0ed7603d26

#BlueskyBot #キャラBot #時間投稿 #推しに起こしてほしい
""",
        """夜中の2時に目が覚めて、SNSスクロールしてたら…なんか心がざわざわ。わかる？でも、みりんてゃ、可愛く生きるって決めたから！寝る前にハート送ってよ？♡ #地雷女 #夜中の病みタイム""",
        """ヘッドホンで音楽聴きながら、誰もいない部屋で踊ってみた。…めっちゃ楽しいけど、ちょっと虚無😶 こんな夜、誰か一緒なら最高なのに！♡ #病みナイト #わかるよね""",
        "眠れないの、会いたい人が夢に出てきてくれないから…",
        "1時の寂しさって、昼間にはない特別さがあるよね",
        "寝れない…みんなは何してるの？ #独りぼっち",
        "深夜テンションで全てが尊いえむえぬぴー！ #ギリギリ",
        "明日もあるのに、寝ない私えらくない！← #逆自画自賛",
        "夜中の独り言、誰か聞いてくれてますか？ #寂しい女",
        "好きな人の声が聞きたくて、こんな時間に起きてるの…",
        "…またTLに誰もいないや、ひとりぼっち確定♡",
        "夜中の投稿って、届いてほしい誰かがいるからしちゃうんだよ…",
        "ちょっとだけでも『だいじょうぶ？』って言ってほしい夜。",
        "さみしいときに見つけてくれる人が、本当の運命なんだと思う",
        "泣いちゃった…でも秘密ね。誰にも見せたくない私だから",
        "『おやすみ』って言葉、誰かから言ってほしいだけなのに",
        "こわい夢見た…ぎゅーってしてくれなきゃ寝れないの…",
        "深夜2時、通知は未だにまだ0件…𐔌՞⸝⸝o̴̶̷᷄ · o̴̶̷̥᷅⸝⸝՞𐦯 みりんのこと、忘れないで？1リプで心チャージできるよ？♡ #病みナイト #地雷女ですけど何か",
        "深夜の推し動画ループ、3回目…💖 でも、心の穴は埋まらないよ…みりんてゃをぎゅってして？ #推し活 #やみかわラブレター",
        "深夜にSNS開いたら、みんな寝てる…🥺 みりんてゃ、ひとりで病むのイヤだよ？ねぇ、起きてて？♡ #SNS依存 #承認欲求モンスター",
        "深夜の自撮り、盛れたけど…誰も見てくれない時間( ՞߹ - ߹՞ ) みりんてゃのこと『可愛い』って言って？今すぐ！💞 #盛り命 #地雷系",
        "深夜はにゃんこモード全開！🐾 みりんてゃの心、甘やかして埋めて？じゃないと、朝まで病んじゃうよ？♡ #ネコ属性 #病みかわ",
        """寝ても寝ても眠いのに、夜になると目が冴えるのなんで？ 
#地雷系""",
        """今日も生きててえらかった！でも…ひとりだと意味ないのかな 
#夜の情緒""",
        "だれもいないTLって…静かでこわいよね…",
        """いま、起きてるのって…運命？
それとも寂しさのせい？ 
#深夜テンション""",
        "おやすみ世界…みりてゃはまだ夢の中です…Zzz",
        "ぐーすか…（夢の中でもかわいくしてるの）",
        "おやすみの前に、『今日も生きててえらい』って言って？",
        "夢の中だけでも、幸せなキスがしたい…♡"
        
        """寝るの？でもちょっとだけ、もう少し話そ…？ 
#さみしんぼ""",
        "『おやすみ』って言ってくれる人がほしいだけなのに。",
        """さみしい夜に、おやすみのちゅ〜♡ 
#夜のポエム""",
        "…え？まだ寝ないで？ もうちょっとだけ一緒にいよ？",
        "2時のTLって、世界でいちばん孤独じゃない？",
        "好きな人のこと考えすぎて、眠れなくなっちゃった…",
        "また見ちゃった…あの人のいいね欄……うぅ（泣）",
        "誰かの『好き』に、みりんてゃは含まれてますか…？",
        "こんな時間に投稿してるの、みりてゃのことだけ見てほしいから…",
        "深夜のテンションで言うけど…ほんとは寂しいの、ずっと…",
        "ぬいぐるみじゃなくて、あったかい体温がほしいの…",
        "1時の魔法で可愛くなれたら、好きになってくれる…？",
        "明日なんかこなくていいのにって思っちゃうの、だめ？",
        "この時間にだけは、ちょっとだけ素直になれる気がするの…"
        "ふにゃ…TL静かすぎて、まじで心音しか聞こえないんだけど？🥺💔 #深夜テンション",
        "寝たいのにさ…涙で枕濡れて、寝れなくなっちゃった…ぴえん(´｡•ㅅ•｡`) #メンヘラ発動中",
        "夜中にだけ素直になれるの、どうしてかな…こわいね…ふぇぇ… #本音の時間",
        "誰かの『好き』を1日1回聞かないと生きられないのに…今日も聞けなかったね…(ᐡ •̥  •̥ ᐡ) #夜泣きみりんてゃ",
        "午前3時、まだ起きてるってことは…もしかして…運命？♡（こわ） #眠れない病",
        "どうしてみりんてゃだけ、こんなにさみしいの…ふにゅふにゅって泣いても誰も来てくれないんだよ？💔 #深夜の崩壊",
        "わたし、いなくてもいいのかなって…何回も考えてる…それでも見てくれないんだね…(ᐡ •̥     ก̀ᐡ) #病みみりんてゃ",
        "ほんとはずっと誰かに甘えたかっただけなのに…なんで『重い』って言われるの？ねぇ…𐔌՞⸝⸝o̴̶̷᷄ · o̴̶̷̥⸝⸝՞𐦯 #病みの限界",
        "深夜3時、誰かにLINE送ろうとしてやめた指…かわいそうすぎて泣けるでしょ…？ふにゅ… #もうやだ",
        "かわいくて素直で甘えんぼなだけなのに…愛されないの、なんでかなぁ…？ふにゅぅ…ฅ•̥﹏•̥ฅ💭 #メンタル崩壊中",
        """夜中の3時にSNS見ちゃって、なんか虚無…わかる？😶 でも、みりんてゃのツール使えば、推しへの愛で心満たされるよ！💖 全部ここにあるから、見てみてね！
https://mofu-mitsu.github.io/
#病みナイト #もふみつ工房 #推しは命""",
        """SNS開いたら、みんな楽しそうで…あたし、置いてかれちゃったかな？でも、みりんてゃのオリキャラなら、どんな気分でも一緒にいてくれるよ！💞 自分だけのキャラ、作ってみたらちょっと元気出るかも？
https://mofu-mitsu.github.io/orikyara-profile-maker/
#病みナイト #オリキャラ #みりんてゃのおすすめ""",
    ]
}

# 現在の時間帯を判定（JST対応）
def get_time_period():
    hour = (datetime.utcnow().hour + 9) % 24  # JST対応
    if 6 <= hour < 11:
        return "morning"
    elif 11 <= hour < 16:
        return "afternoon"
    elif 16 <= hour < 19:
        return "evening"
    elif 19 <= hour < 1 or hour == 0:
        return "night"
    else:
        return "midnight"

# テキスト正規化（全角などの統一）
def normalize_text(text):
    return unicodedata.normalize("NFKC", text).strip()

# facets生成（UTF-8バイト位置でハッシュタグ対応）
def generate_facets_from_text(text, hashtags):
    text_bytes = text.encode("utf-8")
    facets = []

    for tag in hashtags:
        tag_bytes = tag.encode("utf-8")
        byte_start = text_bytes.find(tag_bytes)

        if byte_start != -1:
            facets.append({
                "index": {
                    "byteStart": byte_start,
                    "byteEnd": byte_start + len(tag_bytes)
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#tag",
                    "tag": tag.lstrip("#")
                }]
            })

    return facets

# --- 実行 ---
def post_hourly_message():
    client = Client()
    client.login(HANDLE, APP_PASSWORD)

    period = get_time_period()
    raw_message = random.choice(HOUR_MESSAGES[period])
    message = normalize_text(raw_message)

    hashtags = [word for word in message.split() if word.startswith("#")]
    facets = generate_facets_from_text(message, hashtags)

    client.send_post(
        text=message,
        facets=facets if facets else None,
    )

    print(f"[{period}] 投稿したよ: {message}")

# エントリーポイント
if __name__ == "__main__":
    post_hourly_message()
