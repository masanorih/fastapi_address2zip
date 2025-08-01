import pytest
import os

def requires_ken_all_csv(func):
    """
    ken_all.csvファイルが存在する場合のみテストを実行するデコレーター
    
    ken_all.csvは日本郵便から提供されるデータファイルで、
    このファイルが存在しない場合はテストをスキップします。
    
    Usage:
        @requires_ken_all_csv
        def test_something_with_ken_all_csv(self):
            ...
    """
    return pytest.mark.skipif(
        not os.path.exists('ken_all.csv'),
        reason="ken_all.csv not found - please download from Japan Post (https://www.post.japanpost.jp/zipcode/download.html)"
    )(func)