import pytest
from address_normalizer import AddressNormalizer


class TestAddressNormalizer:
    """住所正規化機能のテストクラス"""
    
    def setup_method(self):
        self.normalizer = AddressNormalizer()
    
    def test_normalize_full_width_numbers(self):
        """全角数字を半角数字に変換するテスト"""
        address = "東京都港区六本木５丁目１２番３号"
        expected = "東京都港区六本木5丁目12番3号"
        result = self.normalizer.normalize(address)
        assert expected in result or result.startswith("東京都港区六本木5丁目")
    
    def test_normalize_kanji_numbers(self):
        """漢数字を半角数字に変換するテスト"""
        address = "東京都港区六本木五丁目"
        result = self.normalizer.normalize(address)
        assert "5丁目" in result
    
    def test_remove_building_address(self):
        """番地・建物名を除去するテスト"""
        address = "東京都千代田区神田小川町３−２２−１６"
        result = self.normalizer.normalize(address)
        assert result == "東京都千代田区神田小川町"
    
    def test_remove_building_name(self):
        """建物名を除去するテスト"""
        address = "東京都港区六本木ヒルズ"
        result = self.normalizer.normalize(address)
        assert result == "東京都港区六本木"
    
    def test_normalize_katakana_to_hiragana(self):
        """カタカナをひらがなに変換するテスト（ヶなど）"""
        address = "東京都千代田区大手町１丁目９番２号大手町フィナンシャルシティ"
        result = self.normalizer.normalize(address)
        # 建物名が除去され、番地も除去される
        assert result == "東京都千代田区大手町1丁目"
    
    def test_normalize_multiple_patterns(self):
        """複数のパターンを含む住所の正規化テスト"""
        address = "東京都港区六本木５丁目１−２−３ヒルズタワー"
        result = self.normalizer.normalize(address)
        assert result == "東京都港区六本木5丁目"
    
    def test_parse_address_parts(self):
        """住所を都道府県・市区町村・町域に分割するテスト"""
        address = "東京都港区六本木5丁目"
        prefecture, city, district = self.normalizer.parse_address(address)
        assert prefecture == "東京都"
        assert city == "港区"
        assert district == "六本木5丁目"  # 丁目情報を保持するように変更
    
    def test_parse_address_chiyoda(self):
        """千代田区の住所分割テスト"""
        address = "東京都千代田区神田小川町"
        prefecture, city, district = self.normalizer.parse_address(address)
        assert prefecture == "東京都"
        assert city == "千代田区"
        assert district == "神田小川町"
    
    def test_normalize_empty_address(self):
        """空の住所の処理テスト"""
        address = ""
        with pytest.raises(ValueError, match="住所が空です"):
            self.normalizer.normalize(address)
    
    def test_normalize_whitespace(self):
        """前後の空白を除去するテスト"""
        address = "  東京都港区六本木５丁目  "
        result = self.normalizer.normalize(address)
        assert not result.startswith(" ")
        assert not result.endswith(" ")
        assert "東京都港区六本木5丁目" in result
    
    def test_generate_district_variants_with_chome(self):
        """丁目付き町域名のバリエーション生成テスト"""
        district = "梅田1丁目"
        variants = self.normalizer.generate_district_variants(district)
        assert len(variants) >= 2
        assert "梅田1丁目" in variants
        assert "梅田" in variants
    
    def test_generate_district_variants_with_banchi(self):
        """番地付き町域名のバリエーション生成テスト"""
        district = "神田小川町3-22-16"
        variants = self.normalizer.generate_district_variants(district)
        assert len(variants) >= 2
        assert "神田小川町3-22-16" in variants
        assert "神田小川町" in variants
    
    def test_generate_district_variants_simple(self):
        """シンプルな町域名のバリエーション生成テスト"""
        district = "六本木"
        variants = self.normalizer.generate_district_variants(district)
        assert len(variants) == 1
        assert "六本木" in variants
    
    def test_generate_district_variants_complex(self):
        """複雑な町域名のバリエーション生成テスト"""
        district = "梅田1丁目2-3-4"
        variants = self.normalizer.generate_district_variants(district)
        # 元の住所、丁目除去版、番地除去版が含まれること
        assert "梅田1丁目2-3-4" in variants
        assert "梅田" in variants
        # 重複が除去されていることを確認
        assert len(variants) == len(set(variants))
    
    def test_parse_address_keeps_chome_info(self):
        """parse_addressが丁目情報を保持することのテスト"""
        address = "東京都港区六本木5丁目"
        prefecture, city, district = self.normalizer.parse_address(address)
        assert prefecture == "東京都"
        assert city == "港区"
        assert district == "六本木5丁目"  # 丁目情報が保持される
    
    def test_convert_kanji_jo_numbers(self):
        """漢数字の「条」変換テスト（札幌住所対応）"""
        address = "北海道札幌市中央区北一条西一丁目"
        result = self.normalizer.normalize(address)
        assert "北1条西1丁目" in result
    
    def test_convert_arabic_to_kanji_jo(self):
        """算用数字→漢数字変換テスト（条・丁目）"""
        district = "北1条西1丁目"
        result = self.normalizer._convert_arabic_to_kanji(district)
        assert result == "北一条西一丁目"
    
    def test_generate_district_variants_sapporo(self):
        """札幌住所のバリエーション生成テスト"""
        district = "北1条西1丁目"
        variants = self.normalizer.generate_district_variants(district)
        expected_variants = ["北1条西1丁目", "北一条西一丁目", "北1条西", "北一条西"]
        for expected in expected_variants:
            assert expected in variants
    
    def test_generate_district_variants_sapporo_different_pattern(self):
        """札幌住所の別パターンテスト"""
        district = "南3条東2丁目"
        variants = self.normalizer.generate_district_variants(district)
        assert "南3条東2丁目" in variants
        assert "南三条東二丁目" in variants
        assert "南3条東" in variants
        assert "南三条東" in variants
    
    def test_parse_address_gun_cho_pattern(self):
        """郡部住所（郡+町）の解析テスト"""
        address = "北海道上川郡東神楽町東三線"
        prefecture, city, district = self.normalizer.parse_address(address)
        assert prefecture == "北海道"
        assert city == "上川郡東神楽町"
        assert district == "東三線"
    
    def test_parse_address_gun_son_pattern(self):
        """郡部住所（郡+村）の解析テスト"""
        address = "北海道石狩郡新篠津村あけぼの"
        prefecture, city, district = self.normalizer.parse_address(address)
        assert prefecture == "北海道"
        assert city == "石狩郡新篠津村"
        assert district == "あけぼの"
    
    def test_parse_address_gun_with_banchi(self):
        """郡部住所+番地の解析テスト"""
        address = "北海道上川郡東神楽町東三線20-125"
        normalized = self.normalizer.normalize(address)
        prefecture, city, district = self.normalizer.parse_address(normalized)
        assert prefecture == "北海道"
        assert city == "上川郡東神楽町"
        assert district == "東三線"  # 番地が除去される
    
    def test_remove_oaza_character(self):
        """大字削除の正規化テスト"""
        address = "鹿児島県奄美市住用町大字山間戸玉593-3"
        result = self.normalizer.normalize(address)
        # 大字が削除され、番地も除去される
        assert result == "鹿児島県奄美市住用町山間戸玉"
    
    def test_remove_aza_character(self):
        """字削除の正規化テスト"""
        address = "沖縄県那覇市字小禄1001-1"
        result = self.normalizer.normalize(address)
        # 字が削除され、番地も除去される
        assert result == "沖縄県那覇市小禄"
    
    def test_remove_both_oaza_and_aza(self):
        """大字と字の両方を含む住所の正規化テスト"""
        address = "熊本県熊本市大字字天明町1234-5"
        result = self.normalizer.normalize(address)
        # 大字と字の両方が削除される
        assert result == "熊本県熊本市天明町"
    
    def test_parse_address_complex_city_names(self):
        """地名に町・市が含まれる複雑な市区町村名の分割テスト"""
        normalizer = AddressNormalizer()
        
        # 十日町市（地名に「町」が含まれる市）
        prefecture, city, district = normalizer.parse_address("新潟県十日町市稲荷町3丁目")
        assert prefecture == "新潟県"
        assert city == "十日町市"
        assert district == "稲荷町3丁目"
        
        # 四日市市（地名に「市」が含まれる市）
        prefecture, city, district = normalizer.parse_address("三重県四日市市諏訪町")
        assert prefecture == "三重県"
        assert city == "四日市市"
        assert district == "諏訪町"
        
        # 八千代市（通常のパターン）
        prefecture, city, district = normalizer.parse_address("千葉県八千代市大和田新田")
        assert prefecture == "千葉県"
        assert city == "八千代市"
        assert district == "大和田新田"
        
        # 町田市（地名に「町」が含まれる市）
        prefecture, city, district = normalizer.parse_address("東京都町田市原町田")
        assert prefecture == "東京都"
        assert city == "町田市"
        assert district == "原町田"