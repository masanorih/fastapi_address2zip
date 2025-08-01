import re
from typing import Tuple, Optional


class AddressNormalizer:
    """住所文字列の正規化クラス"""
    
    def __init__(self):
        # 全角から半角への変換テーブル
        self.full_to_half_table = str.maketrans(
            '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
            '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        )
        
        # 漢数字から半角数字への変換辞書
        self.kanji_to_num = {
            '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
            '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'
        }
        
        # 半角数字から漢数字への変換辞書（逆変換用）
        self.num_to_kanji = {
            '1': '一', '2': '二', '3': '三', '4': '四', '5': '五',
            '6': '六', '7': '七', '8': '八', '9': '九', '10': '十'
        }
    
    def normalize(self, address: str) -> str:
        """住所文字列を正規化する"""
        if not address or not address.strip():
            raise ValueError("住所が空です")
        
        # 前後の空白を除去
        address = address.strip()
        
        # 全角文字を半角に変換
        address = address.translate(self.full_to_half_table)
        
        # 漢数字を半角数字に変換（丁目の場合）
        address = self._convert_kanji_numbers(address)
        
        # 番地・建物名を除去
        address = self._remove_building_info(address)
        
        # 大字・字を除去（住所精度向上のため）
        address = address.replace('大字', '')
        address = address.replace('字', '')
        
        # カタカナをひらがなに変換（特定の文字のみ）
        address = address.replace('ケ', 'ヶ')
        
        return address.strip()
    
    def _convert_kanji_to_number_simple(self, kanji_str: str) -> Optional[str]:
        """
        漢数字文字列を数字文字列に変換する（1-48対応、AddressResolverと統合）
        
        Args:
            kanji_str (str): 漢数字文字列
            
        Returns:
            Optional[str]: 数字文字列、変換できない場合はNone
        """
        # 基本漢数字辞書
        kanji_digits = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
        
        # 一桁の場合
        if len(kanji_str) == 1 and kanji_str in kanji_digits:
            return str(kanji_digits[kanji_str])
        
        # 「十」の場合
        if kanji_str == '十':
            return '10'
        
        # 「十X」のパターン（11-19）
        if kanji_str.startswith('十') and len(kanji_str) == 2:
            ones = kanji_str[1]
            if ones in kanji_digits:
                return str(10 + kanji_digits[ones])
        
        # 「X十」のパターン（20, 30, 40）
        if kanji_str.endswith('十') and len(kanji_str) == 2:
            tens = kanji_str[0]
            if tens in kanji_digits:
                result = kanji_digits[tens] * 10
                return str(result) if result <= 48 else None
        
        # 「X十Y」のパターン（21-48）
        if '十' in kanji_str and len(kanji_str) == 3:
            parts = kanji_str.split('十')
            if len(parts) == 2 and parts[0] in kanji_digits and parts[1] in kanji_digits:
                result = kanji_digits[parts[0]] * 10 + kanji_digits[parts[1]]
                return str(result) if result <= 48 else None
        
        return None
    
    def _convert_kanji_numbers(self, address: str) -> str:
        """漢数字を半角数字に変換（丁目・条の場合、1-48対応）"""
        # 漢数字+丁目のパターンを検索して変換
        def replace_kanji_chome(match):
            kanji_num = match.group(1)
            converted = self._convert_kanji_to_number_simple(kanji_num)
            if converted is not None:
                return converted + '丁目'
            return match.group(0)
        
        # 漢数字+条のパターンを検索して変換（札幌住所対応）
        def replace_kanji_jo(match):
            kanji_num = match.group(1)
            converted = self._convert_kanji_to_number_simple(kanji_num)
            if converted is not None:
                return converted + '条'
            return match.group(0)
        
        address = re.sub(r'([一二三四五六七八九十]+)丁目', replace_kanji_chome, address)
        address = re.sub(r'([一二三四五六七八九十]+)条', replace_kanji_jo, address)
        return address
    
    def _convert_arabic_to_kanji(self, district: str) -> str:
        """算用数字を漢数字に変換（条・丁目の場合）- 札幌住所対応"""
        # 算用数字+条のパターンを検索して変換
        def replace_arabic_jo(match):
            arabic_num = match.group(1)
            if arabic_num in self.num_to_kanji:
                return self.num_to_kanji[arabic_num] + '条'
            return match.group(0)
        
        # 算用数字+丁目のパターンを検索して変換
        def replace_arabic_chome(match):
            arabic_num = match.group(1)
            if arabic_num in self.num_to_kanji:
                return self.num_to_kanji[arabic_num] + '丁目'
            return match.group(0)
        
        district = re.sub(r'([0-9]+)条', replace_arabic_jo, district)
        district = re.sub(r'([0-9]+)丁目', replace_arabic_chome, district)
        return district
    
    def _remove_building_info(self, address: str) -> str:
        """番地・建物名を除去する（特定番地情報は保持）"""
        # 特定番地パターン（例：「970番地」）は保持
        if re.search(r'[0-9]+番地$', address):
            # 番地で終わる場合は保持
            return address
        
        # 番地パターン（数字-数字-数字形式）を除去
        address = re.sub(r'[0-9]+[-−][0-9]+[-−]*[0-9]*.*$', '', address)
        
        # 番地パターン（数字番数字号形式）を除去（特定番地は除く）
        address = re.sub(r'[0-9]+番[0-9]+号?.*$', '', address)
        
        # 丁目の後の数字情報を除去（丁目1-2-3のような場合）
        address = re.sub(r'([0-9]+丁目)[0-9]+[-−].*$', r'\1', address)
        
        # 一般的な建物名パターンを除去（ひらがな・カタカナ・漢字・英字の建物名）
        # ただし、行政区画名は保持する
        patterns = [
            r'ヒルズ.*$',
            r'タワー.*$',
            r'ビル.*$',
            r'マンション.*$',
            r'アパート.*$',
            r'ハイツ.*$',
            r'コーポ.*$',
            r'プラザ.*$',
            r'センター.*$',
            r'フィナンシャル.*$',
        ]
        
        for pattern in patterns:
            address = re.sub(pattern, '', address)
        
        return address
    
    def parse_address(self, address: str) -> Tuple[str, str, str]:
        """住所文字列を都道府県・市区町村・町域に分割する"""
        # 都道府県パターン
        prefecture_match = re.match(r'(.*?[都道府県])', address)
        if not prefecture_match:
            raise ValueError("都道府県が見つかりません")
        
        prefecture = prefecture_match.group(1)
        remaining = address[len(prefecture):]
        
        # 市区町村パターン（政令指定都市・郡部対応）
        # 1. 「大阪市北区」のような政令指定都市+区のパターン
        city_match = re.match(r'(.*?市.*?区)', remaining)
        if not city_match:
            # 2. 「上川郡東神楽町」のような郡部パターン
            city_match = re.match(r'(.*?郡.*?[町村])', remaining)
        if not city_match:
            # 3. 「○○市」パターン（「十日町市」「四日市市」のような地名に町・市が含まれる場合）
            # 貪欲マッチを使用して最後の「市」まで含める
            city_match = re.match(r'(.*市)', remaining)
        if not city_match:
            # 4. 「○○区」パターン
            city_match = re.match(r'(.*?区)', remaining)
        if not city_match:
            # 5. 「○○町」「○○村」パターン（単独町村）
            city_match = re.match(r'(.*?[町村])', remaining)
        if not city_match:
            # 6. 「○○郡」パターン（郡のみの場合）
            city_match = re.match(r'(.*?郡)', remaining)
        if not city_match:
            raise ValueError("市区町村が見つかりません")
        
        city = city_match.group(1)
        district = remaining[len(city):]
        
        return prefecture, city, district
    
    def generate_district_variants(self, district: str) -> list[str]:
        """
        町域名から段階的に検索可能なバリエーションを生成する（双方向数字変換対応）
        
        Args:
            district (str): 元の町域名
            
        Returns:
            list[str]: 検索優先順位順の町域名リスト
        """
        variants = []
        
        # 1. 元の町域名（そのまま）
        variants.append(district)
        
        # 2. 算用数字→漢数字変換版（札幌住所対応）
        kanji_version = self._convert_arabic_to_kanji(district)
        if kanji_version != district:
            variants.append(kanji_version)
        
        # 3. 丁目情報を除去した町域名
        district_without_chome = re.sub(r'[0-9]+丁目.*$', '', district)
        if district_without_chome != district and district_without_chome.strip():
            variants.append(district_without_chome)
            
            # 3-1. 丁目除去版の漢数字変換も追加
            kanji_without_chome = self._convert_arabic_to_kanji(district_without_chome)
            if kanji_without_chome != district_without_chome:
                variants.append(kanji_without_chome)
        
        # 4. 番地情報を除去した町域名（既に normalize で処理済みだが念のため）
        district_without_banchi = re.sub(r'[0-9]+[-−][0-9]+.*$', '', district)
        if district_without_banchi != district and district_without_banchi.strip():
            variants.append(district_without_banchi)
        
        # 5. 基本町域名を抽出（例：「脇川新田町南割下２−１」→「脇川新田町」）
        # 町・新田町・大字などで区切る
        base_patterns = [
            r'^(.*?町)',    # 町で終わる部分
            r'^(.*?新田町)', # 新田町で終わる部分  
            r'^(.*?大字)',   # 大字で終わる部分
        ]
        
        for pattern in base_patterns:
            match = re.search(pattern, district)
            if match:
                base_district = match.group(1)
                if base_district != district and base_district.strip():
                    variants.append(base_district)
                    break
        
        # 重複を除去しつつ順序を保持
        unique_variants = []
        for variant in variants:
            variant = variant.strip()
            if variant and variant not in unique_variants:
                unique_variants.append(variant)
        
        return unique_variants