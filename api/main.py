from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
import os
import redis

# Xử lý lỗi import module
try:
    from api.modules.fixattack1 import Layer7Shield
except ImportError:
    from modules.fixattack1 import Layer7Shield

app = FastAPI()

# Kết nối Redis
REDIS_URL = os.environ.get("KV_URL")
redis_client = None
if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping() 
    except Exception as e:
        print(f"Không thể kết nối Redis: {e}")
        redis_client = None

# Khởi tạo khiên chống DDoS
shield1 = Layer7Shield(redis_client=redis_client, rate_limit=50)

# Hàm Radar: Tự động quét tìm file tĩnh bất chấp môi trường Vercel
def get_static_path(filename):
    current_dir = os.path.dirname(__file__)
    root_dir = os.getcwd()
    
    # 3 ngóc ngách mà Vercel thường giấu file
    possible_paths = [
        os.path.join(root_dir, "public", filename),           # Nằm ngoài Root (Khuyên dùng)
  
        os.path.join(current_dir, "..", "public", filename)   # Nằm lùi lại 1 thư mục
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return possible_paths[0] # Trả về đường dẫn gốc để hiện lỗi rõ ràng nếu vẫn mất

@app.middleware("http")
async def ddos_middleware(request: Request, call_next):
    client_ip = request.headers.get("x-forwarded-for", request.client.host)
    if client_ip:
        client_ip = client_ip.split(",")[0]
        
    user_agent = request.headers.get("user-agent", "")

    # Bỏ qua kiểm tra DDoS cho các file tĩnh (tránh tự block giao diện)
    if request.url.path.startswith("/public"):
        return await call_next(request)

    # Chạy thuật toán lọc DDoS
    analysis = shield1.analyze_request(client_ip, user_agent)
    
    if analysis["status"] == "blocked":
        return JSONResponse(
            status_code=429,
            content={"error": "Access Denied", "detail": analysis["reason"]}
        )

    return await call_next(request)

# Route cấp phát file CSS
@app.get("/public/style.css")
async def read_css():
    css_path = get_static_path("style.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="text/css")
    except Exception as e:
        return Response(content=f"/* Lỗi tải CSS: {e} | Path: {css_path} */", media_type="text/css")

# Route chính cấp phát giao diện HTML
@app.get("/", response_class=HTMLResponse)
async def read_dashboard():
    html_path = get_static_path("index.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"<h1>Lỗi tải giao diện: {e}</h1><p>Đường dẫn radar vừa quét: {html_path}</p>"
