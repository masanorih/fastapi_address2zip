# 郵便番号解決が困難な日本住所の対応記録

このドキュメントでは、住所→郵便番号変換システムの開発過程で発生した困難な住所パターンと、それらに対する技術的解決策を記録します。

## 概要

日本の住所体系は非常に複雑で、以下のような特殊なパターンが存在します：

- 特定番地と一般住所の混在
- 多様な丁目範囲表記（波ダッシュ、ハイフン、カンマ区切り）
- 村名+地区名の複合パターン
- 複雑な市区町村名の解析
- 漢数字・全角数字・半角数字の混在

これらの問題に対してTDD（テスト駆動開発）アプローチで段階的に解決してきました。

---

## 問題1: 新潟県長岡市脇川新田町の特定番地判定

### 住所例
- **正解:** `新潟県長岡市脇川新田町南割下２−１` → `9402461`
- **誤判定:** `新潟県長岡市脇川新田町970番地` → `9540181`

### 問題の詳細
ken_all.csvには以下の2つのエントリが存在：
```csv
9540181,"新潟県","長岡市","脇川新田町（９７０番地）"
9402461,"新潟県","長岡市","脇川新田町（その他）"
```

フォールバック検索で前方一致「脇川新田町」を検索すると、特定番地「970番地」が「その他」より優先されてしまう問題。

### 解決策

1. **`_matches_specific_address`メソッドの実装**
   ```python
   def _matches_specific_address(self, input_district: str, specific_entries: list) -> bool:
       # 特定番地情報を抽出（例：「（９７０番地）」→「970」）
       for stored_district, _ in specific_entries:
           match = re.search(r'（([0-9０-９]+)番地）', stored_district)
           if match:
               specific_number = match.group(1)
               # 入力住所に特定番地が含まれるかチェック
               if specific_number in input_district or f"{specific_number}番地" in input_district:
                   return True
       return False
   ```

2. **フォールバック検索での特定番地照合**
   - 前方一致した候補を特定番地エントリと「その他」エントリに分類
   - 特定番地照合を実行し、一致しない場合は「その他」を優先選択

3. **特定番地情報の保持**
   - `_clean_district_name`で特定番地情報「（９７０番地）」を保持
   - `_remove_building_info`で「970番地」パターンを保持

### 結果
- `新潟県長岡市脇川新田町南割下２−１` → `9402461` (正解)
- `新潟県長岡市脇川新田町970番地` → `9540181` (正解)

---

## 問題2: 北海道札幌市の丁目範囲検索

### 住所例
- **正解:** `北海道札幌市中央区北四条西２２丁目１−２４` → `0640824`
- **誤判定:** 元々は `0600004` を返していた

### 問題の詳細
ken_all.csvの札幌住所には丁目範囲情報が含まれる：
```csv
0600004,"北海道","札幌市中央区","北四条西（１〜１９丁目）"
0640824,"北海道","札幌市中央区","北四条西（２０〜３０丁目）"
```

22丁目は20-30丁目の範囲内だが、正しく判定されていなかった。

### 解決策

1. **漢数字変換の拡張（1-48対応）**
   ```python
   def _convert_kanji_to_number(self, kanji_str: str) -> Optional[int]:
       # 「四十八」まで対応した漢数字変換
       if '十' in kanji_str and len(kanji_str) == 3:
           parts = kanji_str.split('十')
           if len(parts) == 2:
               result = kanji_digits[parts[0]] * 10 + kanji_digits[parts[1]]
               return result if result <= 48 else None
   ```

2. **丁目範囲検索の実装**
   ```python
   def _extract_chome_range(self, district: str) -> Optional[tuple[int, int]]:
       # 「（１〜１９丁目）」パターンの抽出
       full_width_match = re.search(r'（([０-９]+)〜([０-９]+)丁目）', district)
       if full_width_match:
           start_str = full_width_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
           end_str = full_width_match.group(2).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
           return (int(start_str), int(end_str))
   ```

3. **丁目範囲情報の保持**
   - `_clean_district_name`で「（１〜１９丁目）」情報を保持

### 結果
- `北海道札幌市中央区北四条西２２丁目１−２４` → `0640824` (正解)
- `北海道札幌市中央区北四条西５丁目` → `0600004` (正解)

---

## 問題3: 北海道苫小牧市あけぼの町の多様な丁目範囲表記

### 住所例
- **正解:** `北海道苫小牧市あけぼの町４丁目１` → `0530056`
- **誤判定:** 元々は `0591366` を返していた

### 問題の詳細
ken_all.csvには多様な丁目範囲表記が存在：
```csv
0591366,"北海道","苫小牧市","あけぼの町（１、２丁目）"  # カンマ区切り
0530056,"北海道","苫小牧市","あけぼの町（３−５丁目）"    # ハイフン区切り
```

既存の`_extract_chome_range`は波ダッシュ「〜」のみ対応しており、カンマやハイフンに未対応。

### 解決策

1. **`_extract_chome_range`の拡張**
   ```python
   # ハイフン区切りの範囲パターン（例：「（３−５丁目）」）
   hyphen_match = re.search(r'（([０-９\d]+)−([０-９\d]+)丁目）', district)
   if hyphen_match:
       start_str = hyphen_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
       end_str = hyphen_match.group(2).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
       return (int(start_str), int(end_str))
   
   # カンマ区切りの個別列挙パターン（例：「（１、２丁目）」）
   comma_match = re.search(r'（([０-９\d]+)、([０-９\d]+)丁目）', district)
   if comma_match:
       first_str = comma_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
       second_str = comma_match.group(2).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
       # 個別列挙の場合は最小値と最大値を範囲として扱う
       first_num = int(first_str)
       second_num = int(second_str)
       return (min(first_num, second_num), max(first_num, second_num))
   ```

2. **丁目範囲パターンの包括対応**
   ```python
   chome_range_patterns = [
       r'（[０-９一二三四五六七八九十\d]+〜[０-９一二三四五六七八九十\d]+丁目）',  # 波ダッシュ
       r'（[０-９\d]+−[０-９\d]+丁目）',  # ハイフン
       r'（[０-９\d]+、[０-９\d]+丁目）'   # カンマ
   ]
   has_chome_range = any(re.search(pattern, district) for pattern in chome_range_patterns)
   ```

### 結果
- `北海道苫小牧市あけぼの町４丁目１` → `0530056` (正解)
- `北海道苫小牧市あけぼの町１丁目` → `0591366` (正解)

---

## 問題4: 北海道稚内市声問村の村名+地区名照合

### 住所例
- **正解:** `北海道稚内市声問村恵北` → `0986645`
- **誤判定:** 元々は `0986565` を返していた

### 問題の詳細
ken_all.csvには多数の村名地区エントリが存在：
```csv
0986565,"北海道","稚内市","声問村（曙）"
0986645,"北海道","稚内市","声問村（恵北）"
0986642,"北海道","稚内市","声問村（声問）"
```

入力住所「声問村恵北」と辞書の「声問村（恵北）」の照合ができず、前方一致で最初の「声問村（曙）」が返されていた。

### 解決策

1. **`_matches_village_district`メソッドの実装**
   ```python
   def _matches_village_district(self, input_district: str, village_entries: list) -> Optional[str]:
       # 村名+地区名パターンをチェック（例：「声問村恵北」→「声問村」+「恵北」）
       village_match = re.match(r'(.+村)(.+)', input_district)
       if not village_match:
           return None
           
       village_name = village_match.group(1)  # 「声問村」
       district_name = village_match.group(2)  # 「恵北」
       
       for stored_district, zipcode in village_entries:
           # 辞書の村名（地区名）パターンをチェック（例：「声問村（恵北）」）
           stored_match = re.match(r'(.+村)（(.+)）', stored_district)
           if stored_match:
               stored_village = stored_match.group(1)  # 「声問村」
               stored_district_name = stored_match.group(2)  # 「恵北」
               
               # 村名と地区名の両方が一致するかチェック
               if (village_name == stored_village and 
                   district_name == stored_district_name):
                   return zipcode
       return None
   ```

2. **村名地区情報の保持**
   ```python
   village_district_pattern = r'(.+村)（(.+)）'
   if re.search(village_district_pattern, district):
       return district.strip()  # 「声問村（恵北）」を保持
   ```

3. **基本村名の抽出**
   ```python
   base_patterns = [
       r'^(.*?町)',    # 町で終わる部分
       r'^(.*?新田町)', # 新田町で終わる部分
       r'^(.*?村)',    # 村で終わる部分（新規追加）
       r'^(.*?大字)',   # 大字で終わる部分
   ]
   ```

### 結果
- `北海道稚内市声問村恵北` → `0986645` (正解)
- `北海道稚内市声問村曙` → `0986565` (正解)

---

## 問題5: 新潟県十日町市の複雑な市名解析

### 住所例
- **正解:** `新潟県十日町市稲荷町３丁目０−０` → `9480006`
- **問題:** 「十日町市」の「町」で市名解析が終了してしまう

### 問題の詳細
`parse_address`メソッドの市区町村パターンマッチングで、「十日町市」を解析する際に最初の「町」で停止し、「十日町」+「市稲荷町」として誤認識される問題。

### 解決策

**貪欲マッチの採用**
```python
# 3. 「○○市」パターン（「十日町市」「四日市市」のような地名に町・市が含まれる場合）
# 貪欲マッチを使用して最後の「市」まで含める
city_match = re.match(r'(.*市)', remaining)
```

非貪欲マッチ `r'(.*?市)'` から貪欲マッチ `r'(.*市)'` に変更することで、「十日町市」全体を正しく市名として認識。

### 結果
- `新潟県十日町市稲荷町３丁目０−０` → `9480006` (正解)

---

## 技術的アプローチ

### TDD（テスト駆動開発）の採用

すべての問題解決において以下のTDDサイクルを採用：

1. **失敗テストの作成** - 期待する結果と実際の結果が異なることを確認
2. **最小限の実装** - テストをパスさせる最小限のコードを実装
3. **既存テストの確認** - 新しい変更が既存機能を破綻させないことを確認
4. **リファクタリング** - コードの品質を向上

### 階層的検索戦略

住所解決は以下の階層で実行：

1. **Phase 1: 完全一致検索** - `_exact_match()`
   - district_variantsとの完全一致
   - 丁目範囲検索

2. **Phase 2: フォールバック検索** - `_fallback_search()`
   - 前方一致検索（特定番地照合、村名地区照合付き）
   - 部分文字列検索
   - 逆方向検索

3. **Phase 3: 汎用フォールバック検索** - `_generic_fallback_search()`
   - 「以下に掲載がない場合」等の汎用エントリ検索

### 正規化とバリエーション生成

複雑な住所表記に対応するため、以下の正規化を実行：

- **数字変換**: 全角→半角、漢数字→算用数字、算用数字→漢数字（札幌住所対応）
- **建物名除去**: 番地・建物名の除去（特定番地は保持）
- **バリエーション生成**: 基本町域名、丁目除去版、番地除去版の生成

---

## 対応完了した困難住所一覧

| 住所例 | 正解郵便番号 | 問題パターン | 解決手法 |
|--------|-------------|-------------|---------|
| 新潟県長岡市脇川新田町南割下２−１ | 9402461 | 特定番地vs一般住所 | 特定番地照合 |
| 新潟県長岡市脇川新田町970番地 | 9540181 | 特定番地vs一般住所 | 特定番地照合 |
| 北海道札幌市中央区北四条西２２丁目１−２４ | 0640824 | 丁目範囲検索 | 範囲照合 |
| 北海道苫小牧市あけぼの町４丁目１ | 0530056 | 多様な丁目範囲表記 | パターン拡張 |
| 北海道稚内市声問村恵北 | 0986645 | 村名+地区名照合 | 村名地区照合 |
| 新潟県十日町市稲荷町３丁目０−０ | 9480006 | 複雑な市名解析 | 貪欲マッチ |

---

## まとめ

日本の住所体系の複雑さに対して、段階的なアプローチで問題を解決してきました。各問題は独立した技術的課題として捉え、TDDアプローチにより既存機能を破綻させることなく新機能を追加しています。

これらの改善により、特殊な住所パターンにも対応した高精度な郵便番号解決システムを構築することができました。