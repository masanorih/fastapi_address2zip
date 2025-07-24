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
        町域名から特殊な表記を除去して正規化する
        
        Args:
            district (str): 元の町域名
            
        Returns:
            str: 正規化された町域名
        """
        # 括弧内の情報を除去（例：「六本木（次のビルを除く）」→「六本木」）
        district = re.sub(r'（.*?）', '', district)
        district = re.sub(r'\(.*?\)', '', district)
        
        return district.strip()
    
    def _exact_match(self, address: str) -> Optional[str]:
        """
        完全一致検索を実行する（段階的町域名検索を含む）
        
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
            
            # 段階的検索: 元の町域名から順次簡略化して検索
            district_variants = self.normalizer.generate_district_variants(district)
            
            for variant in district_variants:
                if variant in city_districts:
                    return city_districts[variant]
            
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
                
                # Phase 1: 前方一致検索
                for stored_district, zipcode in city_districts.items():
                    if stored_district.startswith(variant):
                        return zipcode
                
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