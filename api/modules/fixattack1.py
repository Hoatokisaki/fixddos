import time

class Layer7Shield:
    def __init__(self, redis_client, rate_limit=50):
        self.r = redis_client
        self.rate_limit = rate_limit
        # Danh sách các User-Agent thường được Botnet sử dụng
        self.bad_user_agents = ["curl", "python-requests", "wget", "postman", "bot"]

    def is_bad_bot(self, user_agent: str) -> bool:
        if not user_agent:
            return True
        ua_lower = user_agent.lower()
        for bot in self.bad_user_agents:
            if bot in ua_lower:
                return True
        return False

    def check_rate_limit(self, ip: str) -> bool:
        # Nếu không có Redis (chạy test local), tạm thời cho qua
        if not self.r:
            return True 
            
        current_time = int(time.time())
        key = f"limit:{ip}:{current_time}"
        
        try:
            requests = self.r.incr(key)
            if requests == 1:
                self.r.expire(key, 5) # Lưu dữ liệu trong 5 giây
                
            if requests > self.rate_limit:
                return False # Vượt ngưỡng -> Chặn
            return True # Hợp lệ -> Cho qua
        except Exception:
            return True

    def analyze_request(self, ip: str, user_agent: str) -> dict:
        if self.is_bad_bot(user_agent):
            return {"status": "blocked", "reason": "Phát hiện Botnet / Bad User-Agent"}
            
        if not self.check_rate_limit(ip):
            return {"status": "blocked", "reason": "Vượt quá ngưỡng Rate Limit (HTTP Flood)"}
            
        return {"status": "allowed", "reason": "Lưu lượng sạch"}