# 🏸 Racket Pro

Ứng dụng Streamlit tra cứu nhiều dòng vợt cầu lông tại các shop, có giá công bố, link sản phẩm và gợi ý theo thông số. Mở ứng dụng sẽ vào **Giá thật từ shop**; phần **Demo thuật toán** được tách riêng.

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

- Danh mục giá thật từ [ShopVNB](https://shopvnb.com/vot-cau-long.html), [FBShop](https://fbshop.vn/vot-cau-long/) và [HVShop](https://hvshop.vn/vot-cau-long/). Bản ghi ngày 21/10/2026 gồm **482 chào bán** (173 + 117 + 192), 429 có giá công khai; mỗi dòng là một chào bán, không phải một mẫu vợt duy nhất.
- Tìm theo tên/dòng vợt, lọc shop, thương hiệu và ngân sách; sắp xếp giá, mở link sản phẩm, xuất CSV tiếng Việt. Giữ nguyên giá khuyến mãi, khoảng giá và giá liên hệ; có thời điểm ghi nhận theo từng chào bán.
- Gợi ý từ giá thật chỉ dùng các chào bán có đủ thông số shop công bố. Không tự điền giá hoặc thông số bị thiếu. Khoảng giá phải nằm toàn bộ trong ngân sách; nhiều nhóm trọng lượng chưa xác định phiên bản sẽ không được chấm điểm.
- Hồ sơ người chơi: tỷ lệ tấn công, trình độ, ngân sách và ưu tiên vợt nhẹ / đũa mềm.
- Lọc thương hiệu, nguồn minh họa và tìm tên vợt; xem danh mục, sắp xếp giá và tải CSV hỗ trợ tiếng Việt trong Excel.
- Xếp hạng bằng tương đồng có trọng số: trọng lượng 25%, cân bằng 45%, độ cứng 30%; có giải thích và radar so sánh tối đa 3 vợt.
- Bộ lọc ngân sách và độ cứng áp dụng trước xếp hạng. Ngân sách 0 cho kết quả rỗng; ở API, `None` bỏ giới hạn ngân sách. Ưu tiên vợt nhẹ giới hạn ≤84g và độ cứng ≤3,2/5.
- Lịch sử giá mô phỏng 14 ngày cho tối đa 4 vợt; phát hiện giá mới nhất giảm ít nhất 8% so với trung vị lịch sử và Z-score ≤−1,8.
- So sánh Weighted Similarity, KNN và Decision Tree trên 15 tình huống mẫu, cùng bộ lọc ràng buộc. KNN chuẩn hóa theo miền đặc trưng; Decision Tree học ánh xạ thông số sang tên vợt. Ablation lần lượt loại một đặc trưng.
- Cache dữ liệu có thời hạn, cập nhật khi file danh mục thay đổi; chỉ tính đánh giá khi mở màn hình tương ứng.

## Dữ liệu và giới hạn

`data/processed/shop_offers.csv` lưu bản ghi giá thật; `shop_status.json` ghi trạng thái lần thu thập. Bộ lấy dữ liệu ở `src/racket_rec/live_catalog.py`, hỗ trợ phân trang, bỏ trùng URL và giới hạn tốc độ (mỗi shop một hàng đợi, nghỉ 0,5 giây giữa các lượt). Chỉ lấy một phần danh mục, bỏ combo/set/vợt tập. Cùng mẫu có thể xuất hiện ở nhiều shop hoặc tên/phiên bản khác nhau; ứng dụng không tự gộp tên gần giống thành một sản phẩm.

**Giá thật là giá ghi nhận tại thời điểm thu thập**, không phải giá trực tuyến được cập nhật mỗi lần mở trang. Giá có thể khác theo màu, trọng lượng, phiên bản, chi nhánh, cước và khuyến mãi; cần mở link shop để kiểm tra giá cuối cùng và tồn kho. Thông số trống được giữ nguyên; điểm 1–5 và trọng lượng theo nhóm U là quy đổi gần đúng. Chỉ 226/482 chào bán có đủ ba thông số trong bản ghi đầu tiên, và không phải tất cả đều có giá công khai hoặc đáp ứng ngân sách. Chiaki trả HTTP 403 trong lần kiểm tra nên chưa được tích hợp.

**220 dòng trong chế độ Demo thuật toán là dữ liệu sinh mô phỏng**, gồm các biến thể và nhãn nguồn ShopVNB, FBSport, ChiakiVN. Không trộn chúng với danh mục giá thật. `generate_multi_source_catalog` tạo dữ liệu demo này; hàm `scrape_shopvnb` cũ không được dùng trong luồng giá thật mới.

15 tình huống đánh giá được khai báo trong mã nguồn; repo chưa cung cấp bằng chứng khảo sát CLB độc lập. Hit@3 là tỷ lệ tình huống có ít nhất một kết quả trong top 3 khớp từ khóa nhãn. Đây là thử nghiệm minh họa, chưa phải kiểm định trên người dùng thực tế. Điểm khớp thể hiện tương đồng thông số, không phải xác suất hài lòng; loại cước, mức căng và cảm giác tay chưa được mô hình hóa.

Lịch sử giá được sinh khi xem màn hình demo, có cài sẵn một mức giảm. Ứng dụng **chưa lưu lịch sử giá thực, chạy theo lịch hoặc tự gửi Telegram**. Hàm `send_telegram_alert` chỉ là tiện ích riêng, dùng biến môi trường `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID`; không commit thông tin bí mật. Giới hạn trọng lượng và độ cứng chỉ là quy tắc chọn vợt, không phải chứng nhận an toàn y tế.

## Cập nhật giá thật

Trên Windows, chạy `CAP_NHAT_GIA.bat`, hoặc từ thư mục dự án:

```powershell
$env:PYTHONPATH="src"
python -m racket_rec.live_catalog --pages 10 --details 30
```

Trên macOS/Linux: `PYTHONPATH=src python -m racket_rec.live_catalog --pages 10 --details 30`.

`--pages` là số trang danh mục mỗi shop (1–20); `--details` là số chào bán đầu tiên mỗi shop được truy cập trang chi tiết khi chưa đủ thông số (0–100). HVShop thường công bố đủ ba thông số ngay tại danh mục. Không cần tải lại toàn bộ website để ứng dụng chạy: bản ghi đi kèm repo dùng được ngay, CI không truy cập shop.

Nếu một shop lỗi hoặc chỉ đọc được một phần, giữ lại các dòng cũ chưa thay được cùng thời điểm ghi nhận cũ; lỗi ghi trong `shop_status.json`. Website đổi cấu trúc có thể cần cập nhật bộ đọc. Sau khi cập nhật, tải lại ứng dụng để nhận bản ghi mới.

## Kiểm tra chất lượng

```powershell
python -m ruff check src tests app
python -m ruff format --check src tests app
python -m pytest tests -q
```

Kiểm thử offline gồm đọc HTML theo từng shop, giá khuyến mãi/khoảng giá/liên hệ, link trùng và sai domain, thông số thiếu, bảo toàn dữ liệu khi shop lỗi, ràng buộc gợi ý, mô hình với danh mục nhỏ/rỗng, cảnh báo giá demo và tương tác cả hai chế độ bằng Streamlit AppTest. GitHub Actions chạy kiểm tra khi push vào `main` hoặc mở pull request trên Python 3.11 và 3.14.

## Docker

```sh
docker build -t racket-pro .
docker run --rm -p 8501:8501 racket-pro
```

Mở http://localhost:8501. Cấu hình giao diện ở `.streamlit/config.toml`, mã ứng dụng ở `app/`, thuật toán và bộ lấy dữ liệu ở `src/racket_rec/`, các bản ghi dữ liệu ở `data/`.
