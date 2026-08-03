# Crypto Vibe-Coding Backtesting — Design

## Mục tiêu

Tạo một môi trường học quantitative trading cho người mới hoàn toàn, tập trung vào crypto và backtest trước. Người dùng sẽ dùng AI để tạo và giải thích code bằng tiếng Việt, thay vì học Python theo giáo trình trước.

Kết quả của giai đoạn đầu là một backtest có thể tái lập cho một chiến lược đơn giản, có phí giao dịch, đánh giá trên dữ liệu chưa dùng để thiết kế chiến lược, và được so sánh với buy-and-hold. Không đặt lệnh thật.

## Phạm vi và nguyên tắc an toàn

- Chỉ backtest và paper trading; không thêm API key có quyền giao dịch hoặc rút tiền.
- Chỉ dùng dữ liệu lịch sử và các cặp thanh khoản cao (BTC/USDT, ETH/USDT) trong giai đoạn đầu.
- Mỗi thử nghiệm phải cấu hình phí, khoảng thời gian dữ liệu, cặp giao dịch và khung thời gian rõ ràng.
- Không coi backtest là bằng chứng lợi nhuận tương lai.
- Không dùng ML, reinforcement learning, đòn bẩy, futures hoặc tối ưu tham số hàng loạt trong giai đoạn đầu.

## Công cụ và repo được chọn

### Repo chính: Freqtrade

`freqtrade/freqtrade` là framework duy nhất được clone ở pha đầu. Nó cung cấp sẵn luồng tải dữ liệu, chiến lược mẫu, backtest, báo cáo và dry-run/paper trading cho crypto. Việc dùng một framework duy nhất giảm phần cấu hình cần hiểu khi mới bắt đầu.

Các repo chỉ để tham khảo sau khi hoàn thành pha đầu:

- `polakowo/vectorbt`: nghiên cứu nhanh nhiều biến thể chiến lược.
- `mementum/backtrader`: học cấu trúc backtest bằng Python khi cần hiểu sâu hơn.
- `hummingbot/hummingbot`: market making; ngoài phạm vi hiện tại.
- `microsoft/qlib` và `AI4Finance-Foundation/FinRL`: ML/RL; ngoài phạm vi hiện tại.

Không clone chiến lược cộng đồng để chạy nguyên trạng. Chỉ lấy ý tưởng sau khi có baseline riêng và kiểm tra điều kiện dữ liệu/chi phí.

## Lộ trình 8 tuần

### Tuần 1 — Môi trường và ngôn ngữ kết quả

- Clone Freqtrade, chạy chiến lược mẫu và tạo backtest đầu tiên.
- Hiểu 5 chỉ số: tổng lợi nhuận, max drawdown, win rate, số lệnh, Sharpe/Sortino.
- Học cách yêu cầu AI: giải thích một file/cấu hình bằng tiếng Việt, chỉ ra giả định và tạo thay đổi nhỏ có thể kiểm chứng.

### Tuần 2 — Dữ liệu và baseline

- Tải dữ liệu spot lịch sử cho BTC/USDT và ETH/USDT.
- Dùng buy-and-hold làm baseline.
- Chạy một chiến lược EMA/RSI cực đơn giản, có phí giao dịch; lưu cấu hình và kết quả.

### Tuần 3 — Cơ chế chiến lược

- Thử riêng từng thay đổi: entry, exit, stop-loss hoặc take-profit.
- Không đổi nhiều hơn một ý tưởng trong một lần chạy.
- Yêu cầu AI xuất bảng so sánh với baseline.

### Tuần 4 — Kiểm tra tính đáng tin

- Tách dữ liệu theo thời gian: phần phát triển và phần out-of-sample.
- Kiểm tra look-ahead bias, survivorship bias, phí và slippage giả định.
- Loại bỏ thay đổi chỉ hiệu quả trong tập phát triển.

### Tuần 5 — Quản trị rủi ro

- Đánh giá max drawdown, chuỗi thua, tỷ lệ thắng/thua, exposure và số lệnh.
- Đặt giới hạn rủi ro giả định, không dùng đòn bẩy.

### Tuần 6 — Tái lập và nhật ký

- Chuẩn hoá cách lưu cấu hình, dữ liệu, kết quả và ghi chú giả thuyết.
- Một kết quả phải chạy lại được bằng cùng command/config.

### Tuần 7–8 — Paper trading (chỉ khi đạt tiêu chí)

- Chỉ dry-run sau khi chiến lược vượt baseline out-of-sample và không có lỗi dữ liệu rõ ràng.
- So sánh kỳ vọng backtest với kết quả dry-run; không tối ưu liên tục để khớp kết quả.

## Luồng thực hành

1. Viết một giả thuyết ngắn (ví dụ: “khi EMA ngắn cắt EMA dài, xu hướng có thể tiếp diễn”).
2. Dùng AI tạo thay đổi nhỏ trong strategy/config.
3. Chạy backtest có phí giao dịch.
4. Lưu báo cáo và so sánh với buy-and-hold.
5. Kiểm tra out-of-sample và rủi ro.
6. Ghi kết luận: giữ, loại hoặc cần thêm dữ liệu.

## Tiêu chí hoàn thành giai đoạn đầu

- Có một chiến lược đơn giản chạy lại được trên BTC/USDT và ETH/USDT.
- Có baseline buy-and-hold và một báo cáo so sánh.
- Có kết quả out-of-sample; không chỉ báo cáo giai đoạn đẹp nhất.
- Biết trả lời: chiến lược vào/ra khi nào, giả định phí bao nhiêu, drawdown cao nhất bao nhiêu, và vì sao chưa dùng tiền thật.

## Xử lý lỗi và xác minh

- Nếu tải dữ liệu hoặc chạy framework lỗi, giữ nguyên log lỗi và yêu cầu AI giải thích trước khi đổi cấu hình.
- Nếu kết quả bất thường, kiểm tra timezone, dữ liệu thiếu, cặp giao dịch, khung thời gian, phí và look-ahead bias trước khi sửa chiến lược.
- Sau mỗi thay đổi, chạy lại một backtest cố định để phát hiện hồi quy.
- Không ghi API key vào repo hay file cấu hình được commit.
