import pytest
import tempfile
import os
from address_resolver import AddressResolver


class TestAddressResolver:
    """AddressResolverクラスのテストクラス"""
    
    def setup_method(self):
        # テスト用のken_all.csvを作成
        self.test_csv_content = """01101,"060  ","0600000","ホッカイドウ","サッポロシチュウオウク","","北海道","札幌市中央区","",0,0,0,0,0,0
13103,"100  ","1000000","トウキョウト","チヨダク","","東京都","千代田区","",1,0,1,0,0,0
13103,"101  ","1010052","トウキョウト","チヨダク","カンダオガワマチ","東京都","千代田区","神田小川町",0,0,0,0,0,0
13107,"106  ","1060032","トウキョウト","ミナトク","ロッポンギ","東京都","港区","六本木",0,0,0,0,0,0
13107,"107  ","1070052","トウキョウト","ミナトク","アカサカ","東京都","港区","赤坂",0,0,0,0,0,0"""
        
        # 一時ファイルを作成
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
        self.temp_file.write(self.test_csv_content)
        self.temp_file.close()
        
        # AddressResolverインスタンスを作成
        self.resolver = AddressResolver(self.temp_file.name)
    
    def teardown_method(self):
        # 一時ファイルを削除
        os.unlink(self.temp_file.name)
    
    def test_resolve_exact_match_tokyo_roppongi(self):
        """東京都港区六本木の完全一致テスト"""
        zipcode = self.resolver.resolve("東京都港区六本木")
        assert zipcode == "1060032"
    
    def test_resolve_exact_match_chiyoda(self):
        """東京都千代田区神田小川町の完全一致テスト"""
        zipcode = self.resolver.resolve("東京都千代田区神田小川町")
        assert zipcode == "1010052"
    
    def test_resolve_with_building_number(self):
        """番地を含む住所の解決テスト"""
        zipcode = self.resolver.resolve("東京都港区六本木5丁目1-2-3")
        assert zipcode == "1060032"
    
    def test_resolve_with_full_width_numbers(self):
        """全角数字を含む住所の解決テスト"""
        zipcode = self.resolver.resolve("東京都千代田区神田小川町３−２２−１６")
        assert zipcode == "1010052"
    
    def test_resolve_akasaka(self):
        """赤坂の解決テスト"""
        zipcode = self.resolver.resolve("東京都港区赤坂")
        assert zipcode == "1070052"
    
    def test_resolve_not_found(self):
        """見つからない住所のテスト"""
        zipcode = self.resolver.resolve("存在しない住所")
        assert zipcode is None
    
    def test_resolve_empty_address(self):
        """空の住所のテスト"""
        with pytest.raises(ValueError, match="住所が空です"):
            self.resolver.resolve("")
    
    def test_resolve_partial_address(self):
        """不完全な住所のテスト"""
        zipcode = self.resolver.resolve("東京都港区")
        # 市区町村レベルでは町域がないため検索失敗（期待される動作）
        assert zipcode is None
    
    def test_build_index_structure(self):
        """インデックス構造のテスト"""
        # 直接インデックスを確認
        assert "東京都" in self.resolver.index
        assert "港区" in self.resolver.index["東京都"]
        assert "六本木" in self.resolver.index["東京都"]["港区"]
        assert self.resolver.index["東京都"]["港区"]["六本木"] == "1060032"
    
    def test_index_contains_chiyoda(self):
        """千代田区のインデックス確認"""
        assert "千代田区" in self.resolver.index["東京都"]
        assert "神田小川町" in self.resolver.index["東京都"]["千代田区"]
        assert self.resolver.index["東京都"]["千代田区"]["神田小川町"] == "1010052"
    
    def test_invalid_csv_file(self):
        """存在しないCSVファイルのテスト"""
        with pytest.raises(FileNotFoundError):
            AddressResolver("nonexistent.csv")
    
    def test_normalize_and_resolve(self):
        """正規化と解決の統合テスト"""
        # 複雑な住所文字列
        address = "東京都港区六本木５丁目１２−３４ヒルズタワー"
        zipcode = self.resolver.resolve(address)
        assert zipcode == "1060032"
    
    def test_resolve_chome_fallback_to_base_district(self):
        """丁目付き住所が基本町域名にフォールバックするテスト"""
        # テストデータには「六本木」のみ存在、「六本木1丁目」は存在しない
        address = "東京都港区六本木1丁目"
        zipcode = self.resolver.resolve(address)
        assert zipcode == "1060032"  # 「六本木」の郵便番号
    
    def test_resolve_banchi_fallback(self):
        """番地付き住所がフォールバックするテスト"""
        address = "東京都千代田区神田小川町3-22-16"
        zipcode = self.resolver.resolve(address)
        assert zipcode == "1010052"  # 「神田小川町」の郵便番号
    
    def test_district_variants_generation(self):
        """AddressNormalizerのgenerate_district_variantsメソッドの動作確認"""
        # リゾルバーが使用するノーマライザーでテスト
        variants = self.resolver.normalizer.generate_district_variants("梅田1丁目")
        assert "梅田1丁目" in variants
        assert "梅田" in variants
        assert len(variants) >= 2
    
    def test_exact_match_with_district_variants(self):
        """段階的完全一致検索のテスト"""
        # 直接_exact_matchメソッドをテスト
        # 「六本木1丁目」で検索して「六本木」がヒットすることを確認
        result = self.resolver._exact_match("東京都港区六本木1丁目")
        assert result == "1060032"
    
    def test_resolve_sapporo_address_with_kanji_conversion(self):
        """札幌住所の算用数字→漢数字変換テスト"""
        # テストデータに札幌の住所を追加（漢数字版）
        test_csv_content = self.test_csv_content + """
01101,"060  ","0600001","ホッカイドウ","サッポロシチュウオウク","キタ１ジョウニシ","北海道","札幌市中央区","北一条西",0,0,1,0,0,0"""
        
        # 新しいテンポラリファイルを作成
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
        temp_file.write(test_csv_content)
        temp_file.close()
        
        try:
            resolver = AddressResolver(temp_file.name)
            # 算用数字の札幌住所で検索
            result = resolver.resolve("北海道札幌市中央区北1条西1丁目")
            assert result == "0600001"
        finally:
            os.unlink(temp_file.name)
    
    def test_resolve_gun_cho_address(self):
        """郡部住所（郡+町）の解決テスト"""
        # テストデータに郡部住所を追加
        test_csv_content = self.test_csv_content + """
01453,"07115","0711563","ホッカイドウ","カミカワグンヒガシカグラチョウ","ヒガシ３セン","北海道","上川郡東神楽町","東三線",0,0,0,0,0,0"""
        
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
        temp_file.write(test_csv_content)
        temp_file.close()
        
        try:
            resolver = AddressResolver(temp_file.name)
            result = resolver.resolve("北海道上川郡東神楽町東三線20-125")
            assert result == "0711563"
        finally:
            os.unlink(temp_file.name)
    
    def test_resolve_gun_son_address(self):
        """郡部住所（郡+村）の解決テスト"""
        # テストデータに郡部住所（村）を追加
        test_csv_content = self.test_csv_content + """
01304,"06811","0681112","ホッカイドウ","イシカリグンシンシノツムラ","アケボノ","北海道","石狩郡新篠津村","あけぼの",0,0,0,0,0,0"""
        
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
        temp_file.write(test_csv_content)
        temp_file.close()
        
        try:
            resolver = AddressResolver(temp_file.name)
            result = resolver.resolve("北海道石狩郡新篠津村あけぼの")
            assert result == "0681112"
        finally:
            os.unlink(temp_file.name)
    
    def test_generic_fallback_search_okinawa_ishitaira(self):
        """沖縄県北中城村石平の汎用フォールバック検索テスト"""
        # 実際のken_all.csvを使用（「以下に掲載がない場合」エントリが存在）
        resolver = AddressResolver('ken_all.csv')
        
        # 沖縄県中頭郡北中城村石平1951で検索
        result = resolver.resolve("沖縄県中頭郡北中城村石平1951")
        assert result == "9012300"  # 「以下に掲載がない場合」の郵便番号
    
    def test_generic_fallback_search_direct_method(self):
        """汎用フォールバック検索の直接メソッドテスト"""
        resolver = AddressResolver('ken_all.csv')
        
        # 直接_generic_fallback_searchメソッドをテスト
        result = resolver._generic_fallback_search("沖縄県中頭郡北中城村石平1951")
        assert result == "9012300"
    
    def test_generic_fallback_search_nonexistent(self):
        """存在しない市区町村での汎用フォールバック検索テスト"""
        resolver = AddressResolver('ken_all.csv')
        
        # 存在しない市区町村での検索
        result = resolver._generic_fallback_search("存在しない県存在しない市存在しない町")
        assert result is None
    
    def test_resolve_amami_sumiyoucho_with_oaza(self):
        """奄美市住用町大字山間の検索テスト（大字削除機能確認）"""
        resolver = AddressResolver('ken_all.csv')
        
        # 大字を含む住所で検索
        result = resolver.resolve("鹿児島県奄美市住用町大字山間戸玉593-3")
        assert result == "8941304"  # 住用町山間の郵便番号
    
    def test_resolve_oaza_normalization(self):
        """大字正規化機能の統合テスト"""
        resolver = AddressResolver('ken_all.csv')
        
        # 正規化により大字が削除されることを確認
        normalized = resolver.normalizer.normalize("鹿児島県奄美市住用町大字山間戸玉593-3")
        assert "大字" not in normalized
        assert "住用町山間戸玉" in normalized
    
    def test_resolve_sapporo_kitashijo_nishi_range_search(self):
        """札幌市北四条西の丁目範囲検索テスト（現在失敗予定）"""
        resolver = AddressResolver('ken_all.csv')
        
        # 22丁目は20-30丁目範囲（0640824）であるべき
        result = resolver.resolve("北海道札幌市中央区北四条西22丁目1-24")
        assert result == "0640824", f"Expected 0640824 but got {result}"
        
        # 5丁目は1-19丁目範囲（0600004）であるべき
        result = resolver.resolve("北海道札幌市中央区北四条西5丁目")
        assert result == "0600004", f"Expected 0600004 but got {result}"
    
    def test_resolve_sapporo_kitashijo_nishi_boundary_cases(self):
        """札幌市北四条西の境界値テスト"""
        resolver = AddressResolver('ken_all.csv')
        
        # 境界値テスト
        result = resolver.resolve("北海道札幌市中央区北四条西19丁目")  # 1-19範囲の上限
        assert result == "0600004", f"Expected 0600004 for 19丁目 but got {result}"
        
        result = resolver.resolve("北海道札幌市中央区北四条西20丁目")  # 20-30範囲の下限
        assert result == "0640824", f"Expected 0640824 for 20丁目 but got {result}"
        
        result = resolver.resolve("北海道札幌市中央区北四条西30丁目")  # 20-30範囲の上限
        assert result == "0640824", f"Expected 0640824 for 30丁目 but got {result}"
    
    def test_resolve_sapporo_kitashijo_nishi_full_address(self):
        """札幌市北四条西の完全住所での範囲検索テスト"""
        resolver = AddressResolver('ken_all.csv')
        
        # 問題となっている具体的な住所
        result = resolver.resolve("北海道札幌市中央区北四条西２２丁目１−２４")
        assert result == "0640824", f"Expected 0640824 for 北四条西２２丁目１−２４ but got {result}"
        
        # 全角数字での境界値テスト
        result = resolver.resolve("北海道札幌市中央区北四条西１９丁目")
        assert result == "0600004", f"Expected 0600004 for 北四条西１９丁目 but got {result}"
        
        result = resolver.resolve("北海道札幌市中央区北四条西２０丁目")
        assert result == "0640824", f"Expected 0640824 for 北四条西２０丁目 but got {result}"
    
    def test_kanji_to_number_conversion_extended(self):
        """漢数字変換の拡張テスト（1-48対応）"""
        resolver = AddressResolver('ken_all.csv')
        
        # 基本的な1桁の漢数字
        assert resolver._convert_kanji_to_number('一') == 1
        assert resolver._convert_kanji_to_number('九') == 9
        
        # 十の位
        assert resolver._convert_kanji_to_number('十') == 10
        assert resolver._convert_kanji_to_number('十一') == 11
        assert resolver._convert_kanji_to_number('十九') == 19
        assert resolver._convert_kanji_to_number('二十') == 20
        assert resolver._convert_kanji_to_number('三十') == 30
        assert resolver._convert_kanji_to_number('四十') == 40
        
        # 21-48の範囲
        assert resolver._convert_kanji_to_number('二十一') == 21
        assert resolver._convert_kanji_to_number('二十五') == 25
        assert resolver._convert_kanji_to_number('三十一') == 31
        assert resolver._convert_kanji_to_number('三十九') == 39
        assert resolver._convert_kanji_to_number('四十一') == 41
        assert resolver._convert_kanji_to_number('四十八') == 48
        
        # 無効な漢数字
        assert resolver._convert_kanji_to_number('五十') is None  # 50は範囲外
        assert resolver._convert_kanji_to_number('百') is None    # 100は範囲外
        assert resolver._convert_kanji_to_number('') is None     # 空文字
        assert resolver._convert_kanji_to_number('あ') is None   # 漢数字以外
    
    def test_extract_chome_number_extended(self):
        """丁目番号抽出の拡張テスト（1-48対応）"""
        resolver = AddressResolver('ken_all.csv')
        
        # 半角数字
        assert resolver._extract_chome_number('六本木1丁目') == 1
        assert resolver._extract_chome_number('六本木48丁目') == 48
        
        # 全角数字
        assert resolver._extract_chome_number('六本木１丁目') == 1
        assert resolver._extract_chome_number('六本木４８丁目') == 48
        
        # 漢数字（1-48対応）
        assert resolver._extract_chome_number('六本木一丁目') == 1
        assert resolver._extract_chome_number('六本木十丁目') == 10
        assert resolver._extract_chome_number('六本木十一丁目') == 11
        assert resolver._extract_chome_number('六本木二十丁目') == 20
        assert resolver._extract_chome_number('六本木二十一丁目') == 21
        assert resolver._extract_chome_number('六本木三十丁目') == 30
        assert resolver._extract_chome_number('六本木四十丁目') == 40
        assert resolver._extract_chome_number('六本木四十八丁目') == 48
        
        # 丁目がない場合
        assert resolver._extract_chome_number('六本木') is None
    
    def test_niigata_nagaoka_wakigawa_shindenmachi_specific_address(self):
        """新潟県長岡市脇川新田町の特定番地vs一般住所の判定テスト"""
        resolver = AddressResolver('ken_all.csv')
        
        # 南割下２−１は970番地ではないため「その他」（9402461）が正解
        result = resolver.resolve("新潟県長岡市脇川新田町南割下２−１")
        expected = "9402461"  # 脇川新田町（その他）
        assert result == expected, f"期待値: {expected}, 実際: {result}"
        
        # 970番地は特定番地エントリ（9540181）が正解
        result_970 = resolver.resolve("新潟県長岡市脇川新田町970番地")
        expected_970 = "9540181"  # 脇川新田町（９７０番地）
        assert result_970 == expected_970, f"期待値: {expected_970}, 実際: {result_970}"