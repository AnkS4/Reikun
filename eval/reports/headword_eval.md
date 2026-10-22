# Headword evaluation — category report

Gold set: 360 queries (`eval/gold_set.tsv`), 60 per category. Hit@k = share of queries whose expected headword (or an accepted alternative) is in the top k.

generated=2026-10-22 11:37 UTC · version=0.8.0 · commit=8b492f1+dirty · ts=20261022T113716Z · endpoint=http://localhost:16333 · points=218786 · mode=auto · subsets=en_words,en_verbs,en_descriptive,ja_words,ja_hiragana,ja_katakana · rewrite=heuristic · CANONICAL_BOOST=3.0 · PREFETCH_MIN=200 · COMMON_BOOST=1.0 · HEAD_BONUS=1.5

  subset              n          Hit@1    Hit@2    Hit@5
  en_verbs           60   58 (96.7%)   59     60
  en_words           60   56 (93.3%)   59     60
  ja_hiragana        60   58 (96.7%)   60     60
  ja_katakana        60   60 (100.0%)   60     60
  ja_words           60   60 (100.0%)   60     60
  ----------------------------------------------
  en_descriptive     60    9 (15.0%)   13     22
  ----------------------------------------------
  ranking total      300   292 (97.3%)   298     300


| subset | n | Hit@1 | Hit@2 | Hit@5 |
|---|---|---|---|---|
| en_verbs | 60 | 58 (96.7%) | 59 | 60 |
| en_words | 60 | 56 (93.3%) | 59 | 60 |
| ja_hiragana | 60 | 58 (96.7%) | 60 | 60 |
| ja_katakana | 60 | 60 (100.0%) | 60 | 60 |
| ja_words | 60 | 60 (100.0%) | 60 | 60 |
| en_descriptive | 60 | 9 (15.0%) | 13 | 22 |
| **ranking total** | **300** | **292 (97.3%)** | **298** | **300** |

## Misses (expected answer not at rank 1)

| subset | query | expected | rank | top hits |
|---|---|---|---|---|
| en_words | `money` | お金 | 2 | 金, お金, マネー |
| en_words | `time` | 時間 | 2 | 時, 時間, 度 |
| en_words | `table` | テーブル | 2 | 表, テーブル, 卓 |
| en_words | `library` | 図書館 | 3 | 文庫, ライブラリー, 図書館 |
| en_verbs | `to finish` | 終わる | 5 | 仕舞う, 済む, 終える |
| en_verbs | `to turn` | 曲がる/回す/回る | 2 | 成る, 回す, 回る |
| ja_hiragana | `かわ` | 川/かわ | 2 | 側, 川, 皮 |
| ja_hiragana | `ゆき` | 雪/ゆき | 2 | 行き, 雪, 裄 |

<details><summary>Misses — en_descriptive (51)</summary>

| query | expected | rank | top hits |
|---|---|---|---|
| `the vehicle that flies in the sky` | 飛行機/航空機 | 4 | 飛行体, 空飛ぶ, 飛雲 |
| `a place where you borrow books` | 図書館 | — | 二酉, 本代, 帯出 |
| `something that is hard to do` | 難しい/大変 | — | し難い, 致しかねる, がりがり |
| `a person who teaches students` | 先生/教師 | — | 教生, 教育実習生, 劣機 |
| `the season after winter` | 春 | — | 冬季, 冬月, 冬 |
| `a small pet that meows` | 猫 | — | 小動物, 愛玩, 小獣 |
| `the opposite of hot` | 寒い/冷たい | — | 熱っちぃ, 対面, 非熱 |
| `a place where you buy food` | スーパー/スーパーマーケット/コンビニ | — | のれん街, イートイン脱税, 食店 |
| `when you arrive late to work or school` | 遅刻/遅れる | — | 遅早時間, 重役出勤, 後発 |
| `a document that proves your identity` | 身分証明書/身分証/ＩＤ | 3 | 本人確認書類, 身の証を立てる, 身分証明書 |
| `the meal you eat in the morning` | 朝食/朝ご飯/朝飯 | — | 朝, 朝腹, 中飯 |
| `a promise you make to someone` | 約束 | — | 棄約, 言質を取る, 約束に背く |
| `a word for feeling very tired` | 疲れる/疲れた | — | 疲れ, 退屈, 眠たい |
| `the place where trains stop` | 駅 | — | 通過駅, 普通列車, 駅に止まる |
| `a word meaning very delicious` | 美味しい/旨い | 4 | ご馳走様でした, ご馳走様, 有難うございました |
| `someone who studies at a school` | 学生/生徒 | — | アカデミック, 上げる, アカデミシャン |
| `a pet animal that barks` | 犬 | — | 狗吠, 愛玩動物, 皮剥ぎ |
| `the opposite of big` | 小さい | — | でかい, 対面, 大型 |
| `a word for a feeling of loneliness` | 寂しい/孤独 | 2 | 寂寥感, 孤独, 孤立 |
| `the coldest season of the year` | 冬 | — | 厳寒の候, 寒, 向寒 |
| `a vehicle with four wheels you drive` | 車/自動車 | — | 四輪駆動車, 四駆, ４ＷＤ |
| `a place where sick people go for treatment` | 病院/クリニック | — | 処置室, シックハウス, 医療施設 |
| `a word for someone you love romantically` | 恋人/パートナー | — | ロマンチック, 恋, ロマンス |
| `a word for being extremely happy` | 嬉しい/ハッピー | 2 | 極端, ハッピー, 笑顔 |
| `a word for something very expensive` | 高い/高価 | — | 上げる, 安上がり, 割安 |
| `a word for something cheap` | 安い/安価/格安 | 3 | 安上がり, 小手先, 安価 |
| `a person who cooks food professionally` | 料理人/シェフ/コック | 4 | 料理研究家, 膳部, 賄い方 |
| `a small yellow fruit that is sour` | レモン | — | 珍果, 黄飯, 単果 |
| `the day before today` | 昨日 | — | 一昨日, 今日という今日, 前々日 |
| `the day after today` | 明日 | — | よりによって今日, 今日という今日, 一昨日 |
| `a place built for people to swim` | プール | — | スイミングクラブ, 水練, 竜穴 |
| `a word for feeling nervous or anxious` | 不安/心配/緊張 | — | ナーバス, 気がもめる, ハラハラ |
| `a casual way to say goodbye` | じゃあね/バイバイ/またね | 3 | おさらば, 別れを告げる, バイバイ |
| `a polite way to say goodbye` | さようなら/さよなら | — | 別れを告げる, おさらば, バイバイ |
| `people who are close to you but not family` | 友達/友人 | — | 家族達, 近親憎悪, 親戚知己 |
| `the small metal object that unlocks a door` | 鍵/キー | — | ドアロック, 開ける, 開扉 |
| `a feeling of wanting to eat something` | 空腹/空腹感/お腹が空く/お腹が空いた | — | 食欲, 気がする, アペタイト |
| `a word for something that is boring` | つまらない/退屈 | 5 | 中刳り, 飽かず, おもんねー |
| `a word for something that is interesting` | 面白い/興味深い | — | 面黒い, おもろい, 希望者 |
| `the place where airplanes take off` | 空港/飛行場 | — | 格納庫, 射爆場, エアクラフト |
| `the feeling or sensation of sleepiness` | 眠気/眠い/眠たい | 2 | お眠, 眠気, 不眠症 |
| `a formal word for a workplace` | 職場 | — | 正式名, 要式, 職住 |
| `a word for congratulations` | おめでとう/おめでとうございます | — | 寿, 喜び, 祝い |
| `a place where you take a bath` | 浴室/お風呂/浴場 | 2 | バス, お風呂, 湯上がり |
| `the place where you cook food` | 台所/キッチン | — | 煮炊き, クッキング, 自炊 |
| `a person who flies an airplane` | パイロット/機長 | — | 空の便, 専用機, 飛来 |
| `a warm blanket for a bed` | 毛布/ぶ毯 | 4 | 薄掛け, ベッドスロー, ケット |
| `a baby dog` | 子犬 | 3 | 新生児, 飼い犬, 子犬 |
| `the person who delivers letters` | 郵便配達員/郵便配達 | — | 文箱, 尊書, 寄信 |
| `the room where you sleep` | 寝室/ベッドルーム | — | 寝部屋, 寝場所, 雑魚寝 |
| `a person who cuts hair` | 美容師/理髪師 | — | 頭を刈る, 理髪, 坊主 |

</details>
