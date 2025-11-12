from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json

app = FastAPI(title="NSPD API", version="1.0.0")

class SearchRequest(BaseModel):
    cadastral_number: str

async def get_nspd_data(cadastral_number: str):
    """Получает данные из NSPD API"""
    url = f"https://nspd.gov.ru/api/geoportal/v2/search/geoportal?thematicSearchId=1&query={cadastral_number}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://nspd.gov.ru/",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status code: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/health")
async def health():
    return {"status": "ok", "message": "API is running"}

@app.post("/search")
async def search(request: SearchRequest):
    """Поиск по кадастровому номеру"""
    
    data = await get_nspd_data(request.cadastral_number)
    
    return {
        "cadastral_number": request.cadastral_number,
        "data": data
    }

@app.get("/search/{cadastral_number}")
async def search_get(cadastral_number: str):
    """GET вариант поиска"""
    request = SearchRequest(cadastral_number=cadastral_number)
    return await search(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
