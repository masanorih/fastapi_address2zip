# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

住所から7桁郵便番号を取得するFastAPI WebAPIプロジェクト。日本郵便の `ken_all.csv` データを使用し、
住所文字列の正規化と階層インデックス検索により高精度な郵便番号変換を提供する。

## Prerequisites

### Required Data File

このアプリケーションの動作には **ken_all.csv** ファイルが必要です。

- **ファイル名**: `ken_all.csv`
- **配置場所**: プロジェクトルートディレクトリ
- **入手先**: [日本郵便 郵便番号ダウンロード](https://www.post.japanpost.jp/zipcode/download.html)
- **エンコーディング**: UTF-8

**重要**: このファイルはリポジトリに含まれていません（.gitignoreで除外）。上記URLから最新版をダウンロードし、UTF-8エンコーディングで保存してください。

## Core Architecture

### 3層アーキテクチャ
1. **AddressNormalizer** (`address_normalizer.py`) - 住所文字列の正規化
   - 全角→半角変換、漢数字変換、番地・建物名除去
   - 都道府県・市区町村・町域への分割機能

2. **AddressResolver** (`address_resolver.py`) - 住所→郵便番号解決
   - ken_all.csvから階層辞書インデックス構築（都道府県→市区町村→町域）
   - 完全一致 + フォールバック検索（前方一致、部分一致）

3. **FastAPI WebAPI** (`main.py`) - HTTP APIエンドポイント

## API Endpoints

### GET `/`
住所変換APIを使用するサンプルアプリケーションのHTMLページ

**リクエスト:**
- HTTPメソッド: GET
- パラメータ: なし
- ヘッダー: 特別な要件なし

**レスポンス (200):**
- Content-Type: `text/html; charset=utf-8`
- Body: HTMLページコンテンツ

**機能:**
- 住所入力フォーム付きのWebインターフェース
- サンプル住所のクリック入力機能（6つのプリセット住所）
- リアルタイム住所変換デモ（JavaScriptによる非同期通信）
- API仕様の説明表示
- レスポンシブデザインのモダンUI

**エラーレスポンス:**
- 500: テンプレートファイル（`templates/index.html`）の読み込み失敗

### POST `/address2zipcode`
住所文字列から7桁郵便番号を取得するメインAPI

**リクエスト:**
```json
{
  "address": "東京都港区六本木５丁目"
}
```

**レスポンス (200):**
```json
{
  "zipcode": "1060032",
  "original_address": "東京都港区六本木５丁目",
  "normalized_address": "東京都港区六本木5丁目"
}
```

**機能:**
- 住所文字列の自動正規化（全角→半角、漢数字変換、番地除去）
- 階層検索による高精度な郵便番号検索
- 完全一致失敗時のフォールバック検索

**エラーレスポンス:**
- 422: バリデーションエラー（空文字列等）
- 404: 住所が見つからない場合
- 500: 内部エラー（住所解析失敗等）

### GET `/health`
サービスの稼働状況を確認するヘルスチェックAPI

**レスポンス (200):**
```json
{
  "status": "healthy"
}
```

### データフロー
```
住所文字列 → AddressNormalizer → AddressResolver → 7桁郵便番号
```

## Development Commands

### 完全セットアップ手順
1. **依存関係インストール**: `uv sync`
2. **データファイル準備**: ken_all.csvをダウンロード・配置
   - [日本郵便 郵便番号ダウンロード](https://www.post.japanpost.jp/zipcode/download.html)
   - プロジェクトルートに`ken_all.csv`として保存（UTF-8エンコーディング）
3. **テスト実行で確認**: `uv run pytest -v`
4. **開発サーバー起動**: `uv run python main.py`

### 環境セットアップ
```bash
uv sync  # 依存関係のインストール
```

### テスト実行
```bash
uv run pytest -v                           # 全テスト実行（約85テストケース）
```

**ken_all.csvスキップ機能**:
- ken_all.csvが存在しない場合、該当テストは自動的にスキップされる
- `@requires_ken_all_csv`デコレーターによる自動制御（test/conftest.py）
- モックデータを使用するテストは継続実行される
- スキップされたテストには日本郵便ダウンロードURLが表示される

### サーバー起動
```bash
uv run python main.py                      # 開発サーバー起動（localhost:8000）
uv run uvicorn main:app --reload           # オートリロード付き起動
```

## Implementation Strategy

プロジェクトは`address_to_zipcode_strategy.md`に記載された階層インデックス + 正規化アプローチを採用：

- **正規化**: 表記ゆれ対応（全角数字、漢数字、番地除去、札幌住所の双方向数字変換）
- **階層検索**: O(1)の辞書アクセスによる高速検索
- **フォールバック**: 完全一致失敗時の段階的検索（前方一致→部分一致）

## Documentation Structure

### 技術文書
- `docs/ARCHITECTURE.md` - 包括的な技術仕様書（設計戦略・実装詳細・代替手法比較）
- `docs/ADDRESS_RESOLUTION_ISSUES.md` - 困難住所パターンの解決記録

### 開発記録
- 郵便番号解決の技術的課題と解決策をTDDアプローチで文書化
- 特殊住所パターン（札幌、苫小牧、稚内等）の対応履歴

## Test-Driven Development

本プロジェクトはTDD手法で開発されており、すべての機能についてテストファーストで実装されている。新機能追加時も同様のアプローチを継続すること。

## Data Dependencies

### ken_all.csv仕様
- **提供元**: 日本郵便公式データ
- **更新頻度**: 月次更新
- **エンコーディング**: UTF-8（必須）
- **CSVフォーマット**: 
  - 列2: 郵便番号（7桁）
  - 列6: 都道府県名
  - 列7: 市区町村名  
  - 列8: 町域名

### データファイル不在時の動作
- **アプリケーション起動**: エラーで停止（`FileNotFoundError`）
- **テスト実行**: 該当テストをスキップし継続実行
- **スキップ対象**: ken_all.csvを直接使用するテスト（約13テストケース）
- **継続実行**: モックデータを使用するテスト（約72テストケース）

## Error Handling

### HTTPステータスコード
- **200**: 正常処理（郵便番号変換成功）
- **404**: 住所解決失敗（データベースに存在しない住所）
- **422**: バリデーションエラー（Pydantic）
  - 空文字列、null値、型不一致等
  - リクエストボディの形式エラー
- **500**: 内部エラー
  - ken_all.csvファイル不在（`FileNotFoundError`）
  - 都道府県抽出失敗（住所正規化エラー）
  - システム例外・予期しないエラー

### エラーレスポンス例
```json
// 422 バリデーションエラー
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "address"],
      "msg": "String should have at least 1 character"
    }
  ]
}

// 404 住所見つからず
{
  "detail": "Address not found"
}

// 500 内部エラー  
{
  "detail": "Internal server error"
}
```
