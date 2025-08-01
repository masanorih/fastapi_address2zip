import csv
import re
from typing import Dict, Optional
from address_normalizer import AddressNormalizer


class AddressResolver:
    """住所から郵便番号を解決するクラス"""
    
    def __init__(self, csv_path: str):
        """
        Args:
            csv_path (str): ken_all.csvファイルのパス
        """
        self.normalizer = AddressNormalizer()
        self.index = self._build_index(csv_path)
    
    def resolve(self, address: str) -> Optional[str]:
        """
        住所文字列から郵便番号を取得する
        
        Args:
            address (str): 住所文字列
            
        Returns:
            Optional[str]: 7桁郵便番号、見つからない場合はNone
        """
        if not address or not address.strip():
            raise ValueError("住所が空です")
        
        # 住所を正規化
        normalized = self.normalizer.normalize(address)
        
        # Phase 1: 完全一致検索
        zipcode = self._exact_match(normalized)
        if zipcode:
            return zipcode
        
        # Phase 2: フォールバック検索
        zipcode = self._fallback_search(normalized)
        if zipcode:
            return zipcode
        
        # Phase 3: 汎用フォールバック検索（「以下に掲載がない場合」等）
        return self._generic_fallback_search(normalized)
    
    def _build_index(self, csv_path: str) -> Dict:
        """
        ken_all.csvから階層辞書インデックスを構築する
        
        Args:
            csv_path (str): CSVファイルのパス
            
        Returns:
            Dict: 階層化された住所インデックス
        """
        index = {}
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 9:
                        continue
                    
                    zipcode = row[2]  # 郵便番号（7桁）
                    prefecture = row[6]  # 都道府県名（漢字）
                    city = row[7]  # 市区町村名（漢字）
                    district = row[8]  # 町域名（漢字）
                    
                    # 空の町域は除外
                    if not district or district.strip() == "":
                        continue
                    
                    # 括弧付きの特殊な町域名を処理
                    district = self._clean_district_name(district)
                    
                    # 階層辞書を構築
                    if prefecture not in index:
                        index[prefecture] = {}
                    if city not in index[prefecture]:
                        index[prefecture][city] = {}
                    
                    # 既存の郵便番号がある場合は最初のものを保持
                    if district not in index[prefecture][city]:
                        index[prefecture][city][district] = zipcode
        
        except FileNotFoundError:
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
        except UnicodeDecodeError as e:
            raise ValueError("CSVファイルの文字エンコーディングが正しくありません（Shift_JISが必要）") from e
        
        return index
    
    def _clean_district_name(self, district: str) -> str:
        """
        町域名から特殊な表記を除去して正規化する（丁目範囲情報は保持）
        
        Args:
            district (str): 元の町域名
            
        Returns:
            str: 正規化された町域名
        """
        # 丁目範囲情報は保持（例：「北四条西（１〜１９丁目）」はそのまま保持）
        # 建物名等の不要な括弧情報のみ除去
        
        # 丁目範囲パターンをチェック
        chome_range_pattern = r'（[０-９一二三四五六七八九十\d]+〜[０-９一二三四五六七八九十\d]+丁目）'
        has_chome_range = re.search(chome_range_pattern, district)
        
        if has_chome_range:
            # 丁目範囲情報がある場合は保持
            return district.strip()
        else:
            # 特定番地情報や「その他」情報は保持
            specific_address_pattern = r'（[０-９\d]+番地）'
            others_pattern = r'（その他）'
            
            if (re.search(specific_address_pattern, district) or 
                re.search(others_pattern, district)):
                # 特定番地情報や「その他」情報がある場合は保持
                return district.strip()
            else:
                # その他の括弧内情報のみ除去
                district = re.sub(r'（.*?）', '', district)
                district = re.sub(r'\(.*?\)', '', district)
                return district.strip()
    
    def _convert_kanji_to_number(self, kanji_str: str) -> Optional[int]:
        """
        漢数字文字列を数字に変換する（1-48対応）
        
        Args:
            kanji_str (str): 漢数字文字列（例：「二十三」）
            
        Returns:
            Optional[int]: 数字、変換できない場合はNone
        """
        # 基本漢数字辞書
        kanji_digits = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
        
        # 一桁の場合
        if len(kanji_str) == 1 and kanji_str in kanji_digits:
            return kanji_digits[kanji_str]
        
        # 「十」の場合
        if kanji_str == '十':
            return 10
        
        # 「十X」のパターン（11-19）
        if kanji_str.startswith('十') and len(kanji_str) == 2:
            ones = kanji_str[1]
            if ones in kanji_digits:
                return 10 + kanji_digits[ones]
        
        # 「X十」のパターン（20, 30, 40）
        if kanji_str.endswith('十') and len(kanji_str) == 2:
            tens = kanji_str[0]
            if tens in kanji_digits:
                result = kanji_digits[tens] * 10
                # 48までに制限
                return result if result <= 48 else None
        
        # 「X十Y」のパターン（21-48）
        if '十' in kanji_str and len(kanji_str) == 3:
            parts = kanji_str.split('十')
            if len(parts) == 2 and parts[0] in kanji_digits and parts[1] in kanji_digits:
                result = kanji_digits[parts[0]] * 10 + kanji_digits[parts[1]]
                # 48までに制限
                return result if result <= 48 else None
        
        return None
    
    def _extract_chome_number(self, district: str) -> Optional[int]:
        """
        町域名から丁目番号を抽出する
        
        Args:
            district (str): 町域名（例：「北四条西22丁目」）
            
        Returns:
            Optional[int]: 丁目番号、見つからない場合はNone
        """
        # 半角数字+丁目のパターン
        match = re.search(r'(\d+)丁目', district)
        if match:
            return int(match.group(1))
        
        # 全角数字+丁目のパターン
        full_width_match = re.search(r'([０-９]+)丁目', district)
        if full_width_match:
            # 全角数字を半角に変換
            full_width_num = full_width_match.group(1)
            half_width_num = full_width_num.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            return int(half_width_num)
        
        # 漢数字+丁目のパターン
        kanji_match = re.search(r'([一二三四五六七八九十]+)丁目', district)
        if kanji_match:
            kanji_num = kanji_match.group(1)
            return self._convert_kanji_to_number(kanji_num)
        
        return None
    
    def _extract_chome_range(self, district: str) -> Optional[tuple[int, int]]:
        """
        町域名から丁目範囲を抽出する
        
        Args:
            district (str): 町域名（例：「北四条西（１〜１９丁目）」）
            
        Returns:
            Optional[tuple[int, int]]: (開始丁目, 終了丁目)、見つからない場合はNone
        """
        # 全角数字の範囲パターン
        full_width_match = re.search(r'（([０-９]+)〜([０-９]+)丁目）', district)
        if full_width_match:
            start_str = full_width_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            end_str = full_width_match.group(2).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            return (int(start_str), int(end_str))
        
        # 半角数字の範囲パターン
        half_width_match = re.search(r'（(\d+)〜(\d+)丁目）', district)
        if half_width_match:
            return (int(half_width_match.group(1)), int(half_width_match.group(2)))
        
        # 漢数字の範囲パターン（1-48対応）
        kanji_match = re.search(r'（([一二三四五六七八九十]+)〜([一二三四五六七八九十]+)丁目）', district)
        if kanji_match:
            start_kanji = kanji_match.group(1)
            end_kanji = kanji_match.group(2)
            start_num = self._convert_kanji_to_number(start_kanji)
            end_num = self._convert_kanji_to_number(end_kanji)
            if start_num is not None and end_num is not None:
                return (start_num, end_num)
        
        return None
    
    def _is_chome_in_range(self, chome_num: int, range_district: str) -> bool:
        """
        指定した丁目番号が範囲内にあるかチェックする
        
        Args:
            chome_num (int): 丁目番号
            range_district (str): 範囲情報を含む町域名
            
        Returns:
            bool: 範囲内の場合True
        """
        chome_range = self._extract_chome_range(range_district)
        if chome_range:
            start, end = chome_range
            return start <= chome_num <= end
        return False
    
    def _matches_specific_address(self, input_district: str, specific_entries: list) -> bool:
        """
        入力住所が特定番地エントリと一致するかチェックする
        
        Args:
            input_district (str): 入力住所の町域部分
            specific_entries (list): 特定番地エントリのリスト [(stored_district, zipcode), ...]
            
        Returns:
            bool: 特定番地にマッチする場合True
        """
        for stored_district, _ in specific_entries:
            # 特定番地情報を抽出（例：「（９７０番地）」→「970」）
            match = re.search(r'（([0-9０-９]+)番地）', stored_district)
            if match:
                specific_number = match.group(1)
                # 全角数字を半角に変換
                specific_number_half = specific_number.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
                
                # 入力住所に特定番地が含まれるかチェック
                if specific_number in input_district or specific_number_half in input_district:
                    return True
                    
                # 番地パターンでの一致もチェック
                if f"{specific_number}番地" in input_district or f"{specific_number_half}番地" in input_district:
                    return True
        
        return False
    
    def _exact_match(self, address: str) -> Optional[str]:
        """
        完全一致検索を実行する（段階的町域名検索 + 丁目範囲検索を含む）
        
        Args:
            address (str): 正規化された住所
            
        Returns:
            Optional[str]: 郵便番号、見つからない場合はNone
        """
        try:
            prefecture, city, district = self.normalizer.parse_address(address)
            
            # 都道府県と市区町村の存在確認
            if prefecture not in self.index or city not in self.index[prefecture]:
                return None
            
            city_districts = self.index[prefecture][city]
            
            # Phase 1: 従来の段階的検索（完全一致優先）
            district_variants = self.normalizer.generate_district_variants(district)
            
            for variant in district_variants:
                if variant in city_districts:
                    return city_districts[variant]
            
            # Phase 2: 丁目範囲検索（フォールバック失敗時）
            input_chome_num = self._extract_chome_number(district)
            if input_chome_num is not None:
                # 基本町域名（丁目を除いた部分）を抽出
                base_district = re.sub(r'[0-9０-９一二三四五六七八九十]+丁目.*$', '', district).strip()
                
                # 基本町域名が一致する範囲エントリを最優先検索
                for stored_district, zipcode in city_districts.items():
                    if self._is_chome_in_range(input_chome_num, stored_district):
                        # 基本町域名が一致するかチェック（数字表記揺れを考慮）
                        stored_base = re.sub(r'（.*?）.*$', '', stored_district).strip()
                        # 数字⇔漢数字の正規化を考慮した比較
                        normalized_stored_base = self.normalizer._convert_kanji_numbers(stored_base)
                        normalized_input_base = self.normalizer._convert_kanji_numbers(base_district)
                        if normalized_input_base == normalized_stored_base:
                            return zipcode
            
            return None
            
        except (KeyError, ValueError):
            return None
    
    def _fallback_search(self, address: str) -> Optional[str]:
        """
        フォールバック検索を実行する（段階的町域名検索を含む）
        
        Args:
            address (str): 正規化された住所
            
        Returns:
            Optional[str]: 郵便番号、見つからない場合はNone
        """
        try:
            prefecture, city, district = self.normalizer.parse_address(address)
            
            # 都道府県と市区町村が存在することを確認
            if prefecture not in self.index:
                return None
            if city not in self.index[prefecture]:
                return None
            
            city_districts = self.index[prefecture][city]
            district_variants = self.normalizer.generate_district_variants(district)
            
            # 各町域バリエーションに対してフォールバック検索を実行
            for variant in district_variants:
                
                # Phase 1: 前方一致検索（特定番地照合付き）
                matching_candidates = []
                for stored_district, zipcode in city_districts.items():
                    if stored_district.startswith(variant):
                        matching_candidates.append((stored_district, zipcode))
                
                # 前方一致が見つかった場合、特定番地照合を実行
                if matching_candidates:
                    # 特定番地エントリと「その他」エントリに分類
                    specific_entries = []  # 特定番地エントリ（例：「（９７０番地）」）
                    others_entries = []    # 「その他」エントリ
                    
                    for stored_district, zipcode in matching_candidates:
                        if '（' in stored_district and '番地）' in stored_district:
                            specific_entries.append((stored_district, zipcode))
                        elif '（その他）' in stored_district:
                            others_entries.append((stored_district, zipcode))
                    
                    # 特定番地照合を実行
                    if specific_entries and district:
                        # 入力住所から番地情報を抽出
                        if self._matches_specific_address(district, specific_entries):
                            # 特定番地にマッチした場合は特定番地エントリを返す
                            return specific_entries[0][1]
                        elif others_entries:
                            # 特定番地にマッチしない場合は「その他」を優先
                            return others_entries[0][1]
                    
                    # 特定番地エントリがない場合は最初の候補を返す
                    return matching_candidates[0][1]
                
                # Phase 2: 部分文字列検索
                for stored_district, zipcode in city_districts.items():
                    if variant in stored_district:
                        return zipcode
                
                # Phase 3: 逆方向検索（入力の方が長い場合）
                for stored_district, zipcode in city_districts.items():
                    if variant.startswith(stored_district):
                        return zipcode
            
        except ValueError:
            pass
        
        return None
    
    def _generic_fallback_search(self, address: str) -> Optional[str]:
        """
        汎用フォールバック検索を実行する（「以下に掲載がない場合」等の汎用エントリを検索）
        
        Args:
            address (str): 正規化された住所
            
        Returns:
            Optional[str]: 郵便番号、見つからない場合はNone
        """
        try:
            prefecture, city, district = self.normalizer.parse_address(address)
            
            # 都道府県と市区町村が存在することを確認
            if prefecture not in self.index:
                return None
            if city not in self.index[prefecture]:
                return None
            
            city_districts = self.index[prefecture][city]
            
            # 汎用エントリのパターンを優先順位順で検索
            generic_patterns = [
                "以下に掲載がない場合",
                "その他",
                "該当地域なし"
            ]
            
            for pattern in generic_patterns:
                if pattern in city_districts:
                    return city_districts[pattern]
            
            return None
            
        except ValueError:
            return None