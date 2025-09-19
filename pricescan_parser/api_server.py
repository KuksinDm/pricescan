from fastapi import FastAPI, HTTPException
from hobbydames.parser import HobbyGamesParser
from pydantic import BaseModel

app = FastAPI(title="PriceScan Parser API", version="1.0.0")


class ParseProductRequest(BaseModel):
    url: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


@app.post("/parse/product")
async def parse_product(request: ParseProductRequest):
    parser = HobbyGamesParser()
    try:
        result = await parser.parse_product_url(request.url)
        return result.dict() if result else {"error": "Product not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await parser.close()


@app.post("/parse/search")
async def search_products(request: SearchRequest):
    parser = HobbyGamesParser()
    try:
        result = await parser.search_products(request.query, request.limit)
        return result.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await parser.close()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "pricescan-parser"}
