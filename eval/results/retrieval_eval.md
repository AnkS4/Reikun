# Retrieval evaluation

Gold set: 24 queries (`eval/gold_set.json`), top-k = 5. Hit@k = share of queries with a relevant entry in the top k; MRR = mean reciprocal rank; NDCG = normalized discounted cumulative gain; MAP = mean average precision over all relevant IDs.

| Configuration | Hit@1 | Hit@3 | Hit@5 | MRR | NDCG@5 | MAP | R@5 | avg ms | MRR descriptive | MRR en_phrase | MRR en_word | MRR exact_ja | MRR kana |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vector | 0.29 | 0.46 | 0.50 | 0.365 | 0.389 | 0.350 | 0.48 | 54 | 0.06 | 0.62 | 0.61 | 0.45 | 0.00 |
| text (bm25) | 0.46 | 0.62 | 0.71 | 0.556 | 0.566 | 0.526 | 0.65 | 17 | 0.06 | 0.44 | 0.54 | 1.00 | 1.00 |
| hybrid | 0.62 | 0.71 | 0.75 | 0.668 | 0.682 | 0.654 | 0.75 | 23 | 0.03 | 0.83 | 0.83 | 0.90 | 1.00 |
| **hybrid + rewrite(heuristic)** | 0.67 | 0.79 | 0.83 | 0.724 | 0.737 | 0.703 | 0.81 | 23 | 0.26 | 0.83 | 0.83 | 0.90 | 1.00 |
| vector + rerank(local) | 0.29 | 0.33 | 0.46 | 0.340 | 0.344 | 0.301 | 0.44 | 277 | 0.03 | 0.75 | 0.75 | 0.05 | 0.07 |
| hybrid + rerank(local) | 0.29 | 0.42 | 0.54 | 0.367 | 0.385 | 0.329 | 0.52 | 301 | 0.09 | 0.83 | 0.75 | 0.05 | 0.07 |
| hybrid + rewrite + rerank(local) | 0.29 | 0.46 | 0.54 | 0.373 | 0.390 | 0.335 | 0.52 | 282 | 0.11 | 0.83 | 0.75 | 0.05 | 0.07 |

Best configuration: **hybrid + rewrite(heuristic)** (MRR 0.724).

<details><summary>Misses — vector (12)</summary>

- `電車` → `電車` → got ['車軸', '車窓', '車体']
- `約束` → `約束` → got ['フォト', 'ネス', 'ガソール']
- `たべる` → `たべる` → got ['夜なべ', '頬っぺた', '浮かべる']
- `やくそく` → `やくそく` → got ['試薬', '厄', '全訳']
- `としょかん` → `としょかん` → got ['フォト', 'ネス', 'ガソール']
- `eat` → `eat` → got ['食', '大食い', '飽食']
- `thank you` → `thank you` → got ['圧巻', '絶妙', '慶弔']
- `how do you say hospital in Japanese` → `how do you say hospital in Japanese` → got ['病棟', '病室', '入院']
- `the vehicle that flies in the sky` → `the vehicle that flies in the sky` → got ['夜空', '大空', '空']
- `quiet and peaceful place` → `quiet and peaceful place` → got ['閑静', '静穏', '長閑']
- `what is the word for weather` → `what is the word for weather` → got ['天候', '気象', '晴天続き']
- `something hard to do` → `something hard to do` → got ['難い', '骨が折れる', '簡単']

</details>

<details><summary>Misses — text (bm25) (7)</summary>

- `eat` → `eat` → got ['外食', '食べ方', '大食い']
- `to be late` → `to be late` → got ['夜更かし', '遅咲き', '遅刻']
- `how do you say hospital in Japanese` → `how do you say hospital in Japanese` → got ['広辞苑', '気象庁', '言う']
- `the vehicle that flies in the sky` → `the vehicle that flies in the sky` → got ['空', '夜空', '空を飛ぶ']
- `a promise you make to someone` → `a promise you make to someone` → got ['顔を潰す', '念を押す', '立て替える']
- `quiet and peaceful place` → `quiet and peaceful place` → got ['ひっそり', '静けさ', '安らぎ']
- `something hard to do` → `something hard to do` → got ['凍りつく', 'ハイファイ', '根を詰める']

</details>

<details><summary>Misses — hybrid (6)</summary>

- `eat` → `eat` → got ['外食', '大食い', '食']
- `how do you say hospital in Japanese` → `how do you say hospital in Japanese` → got ['病棟', '広辞苑', '病室']
- `the vehicle that flies in the sky` → `the vehicle that flies in the sky` → got ['夜空', '空', '大空']
- `quiet and peaceful place` → `quiet and peaceful place` → got ['閑静', 'ひっそり', '静けさ']
- `what is the word for weather` → `what is the word for weather` → got ['天候', '重苦しい', '気象']
- `something hard to do` → `something hard to do` → got ['難い', '凍りつく', '根を詰める']

</details>

<details><summary>Misses — hybrid + rewrite(heuristic) (4)</summary>

- `eat` → `eat` → got ['外食', '大食い', '食']
- `the vehicle that flies in the sky` → `the vehicle that flies in the sky` → got ['夜空', '空', '大空']
- `quiet and peaceful place` → `quiet and peaceful place` → got ['閑静', 'ひっそり', '静けさ']
- `something hard to do` → `something hard to do` → got ['凍りつく', '難い', '根を詰める']

</details>

<details><summary>Misses — vector + rerank(local) (13)</summary>

- `空` → `空` → got ['空想', '空母', '空気']
- `図書館` → `図書館` → got ['覚書', '書簡', '翻訳書']
- `電車` → `電車` → got ['単車', '降車', '急停車']
- `約束` → `約束` → got ['満杯', '嗚呼嗚呼', '老若']
- `やくそく` → `やくそく` → got ['やって来る', '輝く', '兎や角']
- `としょかん` → `としょかん` → got ['満杯', '黒煙', '碁盤']
- `eat` → `eat` → got ['完食', '飽食', '飲食']
- `thank you` → `thank you` → got ['読了', '慶弔', '寿']
- `how do you say hospital in Japanese` → `how do you say hospital in Japanese` → got ['通院', '退院', '医療制度']
- `the vehicle that flies in the sky` → `the vehicle that flies in the sky` → got ['空', '空を飛ぶ', '頭上']
- `quiet and peaceful place` → `quiet and peaceful place` → got ['閑静', '静けさ', '長閑']
- `what is the word for weather` → `what is the word for weather` → got ['晴天', '晴れ間', '気象']
- `something hard to do` → `something hard to do` → got ['し難い', '骨が折れる', '励む']

</details>

<details><summary>Misses — hybrid + rerank(local) (11)</summary>

- `空` → `空` → got ['空母', '空気', '空所']
- `図書館` → `図書館` → got ['覚書', '書簡', '翻訳書']
- `電車` → `電車` → got ['単車', '降車', '急停車']
- `約束` → `約束` → got ['満杯', '嗚呼嗚呼', '老若']
- `やくそく` → `やくそく` → got ['やって来る', '輝く', '兎や角']
- `としょかん` → `としょかん` → got ['満杯', '黒煙', '碁盤']
- `eat` → `eat` → got ['飽食', '飲食', '間食']
- `the vehicle that flies in the sky` → `the vehicle that flies in the sky` → got ['鷲', '空', '空を飛ぶ']
- `quiet and peaceful place` → `quiet and peaceful place` → got ['閑静', 'ひっそり', '静けさ']
- `what is the word for weather` → `what is the word for weather` → got ['晴天', '晴れ間', '快晴']
- `something hard to do` → `something hard to do` → got ['骨が折れる', '得難い', '尻をたたく']

</details>

<details><summary>Misses — hybrid + rewrite + rerank(local) (11)</summary>

- `空` → `空` → got ['空母', '空気', '空所']
- `図書館` → `図書館` → got ['覚書', '書簡', '翻訳書']
- `電車` → `電車` → got ['単車', '降車', '急停車']
- `約束` → `約束` → got ['満杯', '嗚呼嗚呼', '老若']
- `やくそく` → `やくそく` → got ['やって来る', '輝く', '兎や角']
- `としょかん` → `としょかん` → got ['満杯', '黒煙', '碁盤']
- `eat` → `eat` → got ['飽食', '飲食', '大食い']
- `the vehicle that flies in the sky` → `the vehicle that flies in the sky` → got ['鷲', '空', '空を飛ぶ']
- `quiet and peaceful place` → `quiet and peaceful place` → got ['閑静', 'ひっそり', '静けさ']
- `what is the word for weather` → `weather` → got ['晴天', '快晴', '晴れ間']
- `something hard to do` → `something hard to do` → got ['骨が折れる', '得難い', '尻をたたく']

</details>
