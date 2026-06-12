from fastapi import FastAPI, Request, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from api.modules.fixattack1 import Layer7Shield
import os
import redis

app = FastAPI()

# Kết nối Redis (Tùy chọn, gắn biến KV_URL từ Vercel vào đây)
REDIS_URL = os.environ.get("KV_URL")
redis_client = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None

# Khởi tạo khiên chống DDoS từ Module 1
shield1 = Layer7Shield(redis_client=redis_client, rate_limit=50)

@app.middleware("http")
async def ddos_middleware(request: Request, call_next):
    client_ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0]
    user_agent = request.headers.get("user-agent", "")

    # Bỏ qua kiểm tra cho các file tĩnh (css, js, hình ảnh)
    if request.url.path.startswith("/public"):
        return await call_next(request)

    # Chạy thuật toán từ fixattack1
    analysis = shield1.analyze_request(client_ip, user_agent)
    
    if analysis["status"] == "blocked":
        return JSONResponse(
            status_code=429,
            content={"error": "Access Denied", "detail": analysis["reason"]}
        )

    return await call_next(request)

# Gắn giao diện HTML vào route chính
@app.get("/", response_class=HTMLResponse)
async def read_dashboard():
    # Đọc file index.html từ thư mục public
    html_path = os.path.join(os.path.dirname(__file__), "..", "public", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()