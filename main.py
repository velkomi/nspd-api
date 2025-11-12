from fastapi import FastAPI
from pydantic import BaseModel
import httpx

app = FastAPI(title="NSPD API", version="4.0.0")

class SearchRequest(BaseModel):
    cadastral_number: str

async def get_nspd_data(cadastral_number: str):
    """Получает данные из NSPD API"""
    url = f"https://nspd.gov.ru/api/geoportal/v2/search/geoportal?thematicSearchId=1&query={cadastral_number}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
    return {"status": "ok"}

@app.post("/search")
async def search(request: SearchRequest):
    """Поиск по кадастровому номеру"""
    data = await get_nspd_data(request.cadastral_number)
    
    if "error" in data:
        return {
            "cadastral_number": request.cadastral_number,
            "status": "error",
            "message": "Object not found"
        }
    
    features = None
    if "features" in data:
        features = data.get("features", [])
    elif "data" in data and isinstance(data["data"], dict):
        data_obj = data["data"]
        if "features" in data_obj:
            features = data_obj["features"]
    
    if not features or len(features) == 0:
        return {
            "cadastral_number": request.cadastral_number,
            "status": "error",
            "message": "No features found"
        }
    
    feature = features[0]
    props = feature.get("properties", {})
    options = props.get("options", {})
    geometry = feature.get("geometry", {})
    
    # === ПЛОЩАДЬ: УТОЧНЕННАЯ или ДЕКЛАРИРОВАННАЯ ===
    area_verified = options.get("land_record_area_verified")
    area_declared = options.get("declared_area")
    area_specified = options.get("specified_area")
    area_record = options.get("land_record_area")
    
    final_area = None
    area_type = None
    
    if area_verified is not None:
        final_area = area_verified
        area_type = "уточненная"
    elif area_declared is not None:
        final_area = area_declared
        area_type = "декларированная"
    elif area_specified is not None or area_record is not None:
        final_area = area_specified or area_record
        area_type = "уточненная"
    
    # === СТАТУС УЧАСТКА ===
    status_value = options.get("status", "") or options.get("previously_posted", "")
    
    return {
        "cadastral_number": request.cadastral_number,
        "status": "success",
        "data": {
            "cadastral_number": options.get("cad_num", ""),
            "cadastral_district": props.get("cadastralDistrictsCode", ""),
            "quarter_cad_number": options.get("quarter_cad_number", ""),
            "area": final_area,
            "area_type": area_type,
            "readable_address": options.get("readable_address", ""),
            "land_category": options.get("land_record_category_type", ""),
            "land_record_type": options.get("land_record_type", ""),
            "land_record_subtype": options.get("land_record_subtype", ""),
            "permitted_use": options.get("permitted_use_established_by_document", ""),
            "ownership_type": options.get("ownership_type", ""),
            "status": status_value,
            "registration_date": options.get("registration_date", ""),
            "land_record_reg_date": options.get("land_record_reg_date", ""),
            "cadastral_cost": options.get("cost_value", None),
            "cost_per_sqm": options.get("cost_index", None),
            "cost_registration_date": options.get("cost_registration_date", ""),
        },
        "geometry": geometry
    }

@app.get("/search/{cadastral_number}")
async def search_get(cadastral_number: str):
    request = SearchRequest(cadastral_number=cadastral_number)
    return await search(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
