# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

住所から7桁郵便番号を取得するFastAPI WebAPIプロジェクト。日本郵便の `ken_all.csv` データを使用し、
住所文字列の正規化と階層インデックス検索により高精度な郵便番号変換を提供する。

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

### 環境セットアップ
```bash
uv sync  # 依存関係のインストール
```

### テスト実行
```bash
uv run pytest -v                           # 全テスト実行
unittest は必ず全テスト実行を行い、全体テストが 20秒以下になるようにすること。
```

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

**詳細な技術仕様は `ARCHITECTURE.md` を参照。**

## Test-Driven Development

本プロジェクトはTDD手法で開発されており、すべての機能についてテストファーストで実装されている。新機能追加時も同様のアプローチを継続すること。

## Data Dependencies

- `ken_all.csv`: 日本郵便公式データ（UTF-8エンコーディング）
- CSVフォーマット: 列2=郵便番号、列6=都道府県、列7=市区町村、列8=町域

## Error Handling

- 400: バリデーションエラー（空住所等）
- 404: 住所が見つからない
- 422: Pydanticバリデーションエラー
- 500: 内部エラー（都道府県抽出失敗等）
