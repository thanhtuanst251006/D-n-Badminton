# 🏸 Racket Pro

Ứng dụng Streamlit gợi ý vợt cầu lông theo lối chơi, trình độ và ngân sách, kèm so sánh radar và minh họa phát hiện giảm giá.

## Chạy trên máy

Yêu cầu Python 3.11 trở lên. Chạy các lệnh từ thư mục dự án:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

Trên macOS/Linux, kích hoạt môi trường bằng `source .venv/bin/activate`. Trên Windows có thể chạy `CHAY_NGAY.bat` để cài thư viện, kiểm thử và mở ứng dụng.

## Tính năng

- Hồ sơ người chơi: tỷ lệ tấn công, trình độ, ngân sách và ưu tiên vợt nhẹ / đũa mềm.
- Lọc thương hiệu, nguồn minh họa và tìm tên vợt; xem danh mục, sắp xếp giá và tải CSV hỗ trợ tiếng Việt trong Excel.
- Xếp hạng bằng tương đồng có trọng số: trọng lượng 25%, cân bằng 45%, độ cứng 30%; có giải thích và radar so sánh tối đa 3 vợt.
- Bộ lọc ngân sách và độ cứng áp dụng trước xếp hạng. Ngân sách 0 cho kết quả rỗng; ở API, `None` bỏ giới hạn ngân sách. Ưu tiên vợt nhẹ giới hạn ≤84g và độ cứng ≤3,2/5.
- Lịch sử giá mô phỏng 14 ngày cho tối đa 4 vợt; phát hiện giá mới nhất giảm ít nhất 8% so với trung vị lịch sử và Z-score ≤−1,8.
- So sánh Weighted Similarity, KNN và Decision Tree trên 15 tình huống mẫu, cùng bộ lọc ràng buộc. KNN chuẩn hóa theo miền đặc trưng; Decision Tree học ánh xạ thông số sang tên vợt. Ablation lần lượt loại một đặc trưng.
- Cache dữ liệu có thời hạn, cập nhật khi file danh mục thay đổi; chỉ tính đánh giá khi mở màn hình tương ứng.

## Dữ liệu và giới hạn

**220 dòng trong danh mục hiện tại là dữ liệu sinh mô phỏng**, gồm các biến thể và nhãn nguồn ShopVNB, FBSport, ChiakiVN. Không phải 220 sản phẩm đã xác minh hoặc giá trực tuyến. `generate_multi_source_catalog` tạo dữ liệu này; hàm `scrape_shopvnb` riêng biệt chưa được nối với ứng dụng và chưa xác minh hoạt động với website hiện tại.

15 tình huống đánh giá được khai báo trong mã nguồn; repo chưa cung cấp bằng chứng khảo sát CLB độc lập. Hit@3 là tỷ lệ tình huống có ít nhất một kết quả trong top 3 khớp từ khóa nhãn. Đây là thử nghiệm minh họa, chưa phải kiểm định trên người dùng thực tế. Điểm khớp thể hiện tương đồng thông số, không phải xác suất hài lòng; loại cước, mức căng và cảm giác tay chưa được mô hình hóa.

Lịch sử giá được sinh khi xem màn hình demo, có cài sẵn một mức giảm. Ứng dụng **chưa lưu lịch sử giá thực, chạy theo lịch hoặc tự gửi Telegram**. Hàm `send_telegram_alert` chỉ là tiện ích riêng, dùng biến môi trường `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID`; không commit thông tin bí mật. Giới hạn trọng lượng và độ cứng chỉ là quy tắc chọn vợt, không phải chứng nhận an toàn y tế.

## Kiểm tra chất lượng

```powershell
python -m ruff check src tests app
python -m ruff format --check src tests app
python -m pytest tests -q
```

Kiểm thử gồm chuẩn hóa dữ liệu, ràng buộc gợi ý, mô hình với danh mục nhỏ/rỗng, phát hiện giảm giá và tương tác giao diện bằng Streamlit AppTest. GitHub Actions chạy kiểm tra khi push vào `main` hoặc mở pull request trên Python 3.11 và 3.14.

## Docker

```sh
docker build -t racket-pro .
docker run --rm -p 8501:8501 racket-pro
```

Mở http://localhost:8501. Cấu hình giao diện ở `.streamlit/config.toml`, mã ứng dụng ở `app/`, thuật toán ở `src/racket_rec/`, dữ liệu demo ở `data/`.
