from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
from address_resolver import AddressResolver
import os

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="住所→郵便番号変換API",
    description="日本の住所文字列から7桁郵便番号を取得するWebAPI",
    version="1.0.0"
)

# リクエストモデル
class AddressRequest(BaseModel):
    address: str
    
    @field_validator('address')
    def address_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('住所が空です')
        return v.strip()

# レスポンスモデル
class ZipcodeResponse(BaseModel):
    zipcode: str
    original_address: str
    normalized_address: str

class HealthResponse(BaseModel):
    status: str

# AddressResolverのインスタンスを初期化
csv_path = os.path.join(os.path.dirname(__file__), "ken_all.csv")
resolver = AddressResolver(csv_path)

@app.get("/", response_class=HTMLResponse)
async def root():
    """サンプルアプリケーションのHTMLページを返す"""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return html_content

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェックエンドポイント"""
    return HealthResponse(status="healthy")

@app.post("/address2zipcode", response_model=ZipcodeResponse)
async def address_to_zipcode(request: AddressRequest):
    """
    住所文字列から7桁郵便番号を取得する
    
    Args:
        request: 住所を含むリクエストデータ
        
    Returns:
        ZipcodeResponse: 郵便番号と正規化された住所を含むレスポンス
        
    Raises:
        HTTPException: 住所が見つからない場合（404）
        HTTPException: 不正なリクエストの場合（400）
    """
    try:
        # 住所から郵便番号を取得
        zipcode = resolver.resolve(request.address)
        
        if zipcode is None:
            raise HTTPException(
                status_code=404,
                detail=f"住所が見つかりません: {request.address}"
            )
        
        # 正規化された住所を取得
        normalized_address = resolver.normalizer.normalize(request.address)
        
        return ZipcodeResponse(
            zipcode=zipcode,
            original_address=request.address,
            normalized_address=normalized_address
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部エラー: {str(e)}")

# 開発用のサーバー起動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
