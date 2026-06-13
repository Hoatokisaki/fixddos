/**
 * MODULE SECURITY 1: FRONTEND RATE LIMITING & BOT DETECTION
 * Tác dụng: Ngăn chặn spam request từ trình duyệt, kiểm tra bot cơ bản.
 */

const AntiDDoS_Module1 = {
    requestCount: 0,
    lastRequestTime: Date.now(),
    maxRequestsPerSecond: 3, // Giới hạn 3 click/giây

    // 1. Thuật toán Rate Limiting (Chống Spam Click)
    checkRateLimit: function() {
        const currentTime = Date.now();
        if (currentTime - this.lastRequestTime < 1000) {
            this.requestCount++;
        } else {
            this.requestCount = 1;
            this.lastRequestTime = currentTime;
        }

        if (this.requestCount > this.maxRequestsPerSecond) {
            console.warn("CẢNH BÁO TẤN CÔNG: Phát hiện hành vi spam!");
            alert("Hệ thống nhận diện hành vi bất thường. Vui lòng thử lại sau!");
            return false; // Chặn hành động
        }
        return true; // Cho phép
    },

    // 2. Thuật toán phát hiện Bot cơ bản
    detectBot: function() {
        // Môi trường tự động hóa (Selenium, Puppeteer) thường có navigator.webdriver = true
        if (navigator.webdriver) {
            document.body.innerHTML = "<h1 style='color:red; text-align:center; margin-top:20%'>TRUY CẬP BỊ TỪ CHỐI (BOT DETECTED)</h1>";
            return true;
        }
        return false;
    },

    init: function() {
        if (this.detectBot()) return;

        // Gắn bảo vệ vào nút bấm
        const btn = document.getElementById('verify-btn');
        if (btn) {
            btn.addEventListener('click', (e) => {
                if (!this.checkRateLimit()) {
                    e.preventDefault(); // Hủy sự kiện nếu spam
                } else {
                    console.log("Xác thực an toàn. Gửi dữ liệu tới Backend...");
                    // Thêm logic gọi API (fetch/axios) tới Flask/Django tại đây
                }
            });
        }
    }
};

// Khởi chạy Module
document.addEventListener('DOMContentLoaded', () => {
    AntiDDoS_Module1.init();
});
