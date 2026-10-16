# 🏸 Hệ Thống Gợi Ý Vợt Cầu Lông & Theo Dõi Biến Động Giá (End-to-End Portfolio)

## 1. Điểm nổi bật của dự án
- **Dữ liệu đa nguồn (220+ cây vợt):** Tổng hợp từ ShopVNB, FBSport, ChiakiVN kèm pipeline làm sạch (`cleaning.py`) chuẩn hóa trọng lượng (`3U/4U/5U`), điểm cân bằng, độ cứng đũa và ghi log lý do điền khuyết (`imputation_reason`).
- **Mô hình gợi ý kết hợp (Hybrid Recommender):** Lọc theo ràng buộc cứng (Ngân sách, Trình độ, Tiền sử chấn thương cổ tay/khuỷu tay) kết hợp xếp hạng bằng độ tương đồng có trọng số và giải thích mức độ đóng góp của từng thông số.
- **Thực nghiệm & Đánh giá (`evaluation.py`):** So sánh Weighted Similarity, KNN và Decision Tree bằng độ đo **Hit@3** và nghiên cứu loại bỏ đặc trưng (**Ablation Study**).
- **Theo dõi biến động giá (`alerts.py`):** Phát hiện giảm giá bất thường bằng **Z-Score** và **Rolling Median**, tích hợp gửi cảnh báo qua Telegram Bot.

## 2. Hạn chế của bộ nhãn khảo sát (Ground Truth Limitations)
- Bộ nhãn khảo sát hiện tại thu thập từ nhóm 15-30 người chơi cấp CLB nên vẫn mang tính chủ quan theo cảm giác tay cá nhân.
- Chưa tách biệt được ảnh hưởng của loại cước đan (VD: Yonex Exbolt 63, BG66 Ultimax) và mức căng (kg) lên độ cứng và độ nảy thực tế khi đánh.
