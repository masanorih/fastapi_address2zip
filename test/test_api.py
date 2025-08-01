import pytest
from fastapi.testclient import TestClient
from main import app
from .conftest import requires_ken_all_csv

client = TestClient(app)


@requires_ken_all_csv
def test_address_to_zipcode_success():
    """住所から郵便番号取得のテスト - 成功ケース"""
    response = client.post("/address2zipcode", json={
        "address": "東京都港区六本木５丁目"
    })
    assert response.status_code == 200
    data = response.json()
    assert "zipcode" in data
    assert data["zipcode"] == "1060032"


@requires_ken_all_csv
def test_address_to_zipcode_chiyoda():
    """東京都千代田区のテスト"""
    response = client.post("/address2zipcode", json={
        "address": "東京都千代田区神田小川町３−２２−１６"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["zipcode"] == "1010052"


@requires_ken_all_csv
def test_address_to_zipcode_invalid_address():
    """無効な住所のテスト"""
    response = client.post("/address2zipcode", json={
        "address": "存在しない住所"
    })
    # 都道府県が抽出できない場合は500エラーになる
    assert response.status_code == 500


def test_address_to_zipcode_empty_address():
    """空の住所のテスト"""
    response = client.post("/address2zipcode", json={
        "address": ""
    })
    # Pydanticのバリデーションエラーで422が返される
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_address_to_zipcode_missing_field():
    """addressフィールドが欠けているテスト"""
    response = client.post("/address2zipcode", json={})
    assert response.status_code == 422


def test_health_check():
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint():
    """root endpointのテスト - HTMLページが返されることを確認"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    
    # HTMLの基本構造が含まれていることを確認
    html_content = response.text
    assert "<!DOCTYPE html>" in html_content
    assert "住所→郵便番号変換API" in html_content
    assert "address2zipcode" in html_content
    assert "form" in html_content.lower()


def test_root_endpoint_contains_sample_addresses():
    """root endpointに含まれるサンプル住所の確認"""
    response = client.get("/")
    assert response.status_code == 200
    
    html_content = response.text
    # サンプル住所が含まれていることを確認
    assert "東京都港区六本木5丁目" in html_content
    assert "東京都千代田区神田小川町" in html_content
    assert "東京都港区赤坂" in html_content
    assert "北海道上川郡東神楽町東三線20-125" in html_content


@requires_ken_all_csv
def test_address_to_zipcode_osaka_umeda_with_chome():
    """大阪府大阪市北区梅田1丁目のテスト - 丁目除去フォールバック"""
    response = client.post("/address2zipcode", json={
        "address": "大阪府大阪市北区梅田1丁目"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["zipcode"] == "5300001"  # 梅田の郵便番号
    assert data["original_address"] == "大阪府大阪市北区梅田1丁目"


@requires_ken_all_csv
def test_address_to_zipcode_chome_fallback_various():
    """様々な丁目付き住所のフォールバックテスト"""
    test_cases = [
        ("東京都港区六本木1丁目", "1060032"),
        ("東京都港区赤坂2丁目", "1070052"),
    ]
    
    for address, expected_zipcode in test_cases:
        response = client.post("/address2zipcode", json={
            "address": address
        })
        assert response.status_code == 200
        data = response.json()
        assert data["zipcode"] == expected_zipcode


@requires_ken_all_csv
def test_address_to_zipcode_sapporo_kita1jo_nishi1chome():
    """札幌住所「北1条西1丁目」のテスト - 算用数字→漢数字変換"""
    response = client.post("/address2zipcode", json={
        "address": "北海道札幌市中央区北1条西1丁目"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["zipcode"] == "0600001"  # 北一条西の郵便番号
    assert data["original_address"] == "北海道札幌市中央区北1条西1丁目"


@requires_ken_all_csv
def test_address_to_zipcode_sapporo_various_patterns():
    """札幌住所の様々なパターンテスト"""
    # 実際のken_all.csvに存在する札幌の住所パターン
    test_cases = [
        ("北海道札幌市中央区北1条西", "0600001"),  # 北一条西
        ("北海道札幌市中央区北2条西", "0600002"),  # 北二条西
        ("北海道札幌市中央区大通西", "0600042"),  # 大通西
    ]
    
    for address, expected_zipcode in test_cases:
        response = client.post("/address2zipcode", json={
            "address": address
        })
        assert response.status_code == 200
        data = response.json()
        assert data["zipcode"] == expected_zipcode


@requires_ken_all_csv
def test_address_to_zipcode_gun_cho_address():
    """郡部住所（郡+町）のAPIテスト"""
    response = client.post("/address2zipcode", json={
        "address": "北海道上川郡東神楽町東三線20-125"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["zipcode"] == "0711563"  # 東三線の郵便番号
    assert data["original_address"] == "北海道上川郡東神楽町東三線20-125"


@requires_ken_all_csv
def test_address_to_zipcode_gun_son_address():
    """郡部住所（郡+村）のAPIテスト"""
    response = client.post("/address2zipcode", json={
        "address": "北海道石狩郡新篠津村あけぼの"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["zipcode"] == "0681112"  # あけぼのの郵便番号
    assert data["original_address"] == "北海道石狩郡新篠津村あけぼの"


@requires_ken_all_csv
def test_address_to_zipcode_generic_fallback_okinawa():
    """沖縄県北中城村石平の汎用フォールバック検索APIテスト"""
    response = client.post("/address2zipcode", json={
        "address": "沖縄県中頭郡北中城村石平1951"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["zipcode"] == "9012300"  # 「以下に掲載がない場合」の郵便番号
    assert data["original_address"] == "沖縄県中頭郡北中城村石平1951"


@requires_ken_all_csv
def test_address_to_zipcode_amami_oaza_removal():
    """奄美市住用町大字山間の大字削除機能APIテスト"""
    response = client.post("/address2zipcode", json={
        "address": "鹿児島県奄美市住用町大字山間戸玉593-3"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["zipcode"] == "8941304"  # 住用町山間の郵便番号
    assert data["original_address"] == "鹿児島県奄美市住用町大字山間戸玉593-3"