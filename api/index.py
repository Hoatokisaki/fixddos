from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import redis
import time
import os

app = FastAPI(title="DDoS Protection System")

# Kết nối đến Vercel KV (Upstash Redis)
# Bạn cần lấy biến môi trường KV_URL từ màn hình Vercel Dashboard
REDIS_URL = os.environ.get("KV_URL", "redis://localhost:6379")
try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"Lỗi kết nối Redis: {e}")
    r = None

# Ngưỡng chống DDoS: 50 requests / giây cho mỗi IP
RATE_LIMIT = 50 

@app.middleware("http")
async def ddos_protection_middleware(request: Request, call_next):
    # Bỏ qua nếu không có kết nối Redis
    if r is None:
        return await call_next(request)

    client_ip = request.client.host
    # Trích xuất IP thật nếu chạy qua Proxy/Vercel
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0]

    current_time = int(time.time())
    
    # Các Key lưu trữ trong Redis
    ip_window_key = f"rate_limit:{client_ip}:{current_time}"
    req_sec_key = f"req_per_sec:{current_time}"

    try:
        # Đếm số request của IP này trong giây hiện tại
        requests_this_second = r.incr(ip_window_key)
        if requests_this_second == 1:
            r.expire(ip_window_key, 5) # Tự xóa key sau 5s để tiết kiệm RAM

        # Đếm tổng số request của cả hệ thống trong giây hiện tại (cho Dashboard)
        r.incr(req_sec_key)
        r.expire(req_sec_key, 5)

        # LOGIC CHẶN DDoS
        if requests_this_second > RATE_LIMIT:
            r.incr("metric:total_blocked")
            return JSONResponse(
                status_code=429, 
                content={"error": "Bị chặn bởi Hệ thống chống DDoS", "ip": client_ip}
            )

        # Nếu hợp lệ, cho phép request đi tiếp vào hệ thống
        response = await call_next(request)

        # Ghi nhận số liệu sau khi xử lý
        if response.status_code >= 400 and response.status_code != 429:
            r.incr("metric:total_errors")
        else:
            r.incr("metric:total_allowed")

        return response

    except Exception as e:
        print(f"Redis Error: {e}")
        # Nếu Redis lỗi, fallback cho request đi qua để không làm sập web
        return await call_next(request)

# --- CÁC ROUTE CỦA ỨNG DỤNG ---

@app.get("/")
def home():
    return {"message": "Hệ thống hoạt động bình thường. Bạn đã vượt qua tường lửa."}

# Route dành cho C-Panel / Dashboard lấy số liệu
@app.get("/api/cpanel/stats")
def get_stats():
    if r is None:
        return {"error": "Không kết nối được cơ sở dữ liệu"}
        
    current_time = int(time.time())
    
    # Lấy Req/s của giây vừa diễn ra
    req_s = r.get(f"req_per_sec:{current_time - 1}")
    
    return {
        "current_req_s": int(req_s) if req_s else 0,
        "total_allowed": int(r.get("metric:total_allowed") or 0),
        "total_blocked": int(r.get("metric:total_blocked") or 0),
        "total_errors": int(r.get("metric:total_errors") or 0),
        "rate_limit_config": RATE_LIMIT
    }
