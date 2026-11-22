# SoundTube VN — Backend ShazamIO Miễn Phí 100%

Gói này tích hợp sẵn giao diện **SoundTube VN** (`index.html`) cùng backend **FastAPI + ShazamIO** (`server.py`) giúp nhận diện nhạc phát trên PC/Tab và Micro hoàn toàn miễn phí, không giới hạn lượt.

## Cách 1: Chạy ngay trên máy tính (Windows / macOS / Linux)

1. Cài đặt **Python 3.10+** và **FFmpeg** (nếu chưa có FFmpeg, trên Windows chạy `winget install Gyan.FFmpeg`).
2. Mở Terminal / PowerShell trong thư mục giải nén và chạy:
   ```bash
   pip install -r requirements.txt
   python server.py
   ```
3. Mở trình duyệt Chrome/Edge truy cập: `http://localhost:8000`
4. Bấm **Cài đặt API** (góc trên bên phải):
   - Tích chọn **"Tự dùng backend cùng máy chủ"**
   - Dán **YouTube Data API v3 Key** (nếu muốn tìm trực tiếp toàn bộ YouTube)
   - Bấm **Kiểm tra khóa** → thấy dấu tích xanh → bấm **Lưu cài đặt**.

## Cách 2: Đưa lên mạng (Railway / Render) bằng Docker

1. Đẩy thư mục này lên GitHub repo mới.
2. Trên **Railway** hoặc **Render**, chọn **New Web Service → Deploy from GitHub** (tự nhận diện `Dockerfile`).
3. Sau khi deploy xong, bạn có thể truy cập trực tiếp link `https://...` đó hoặc dán link `https://...` vào ô **Backend ShazamIO** trong mục **Cài đặt API**.
