# Freqtrade Docker Isolation — Design

## Mục tiêu

Chạy Freqtrade cho backtest crypto trong một Docker Compose project riêng, không dùng chung host port, network hoặc dữ liệu với Docker project hiện tại của người dùng.

## Bối cảnh đã kiểm tra

Docker Engine đang chạy. Project hiện tại tên `docker` có hai PostgreSQL container và đang bind:

- `5432:5432`
- `5433:5432`

Host port `8090` hiện không có process lắng nghe.

## Thiết kế được chọn

### Backtest trước, không mở host port

Các lệnh backtest và tải dữ liệu dùng:

```bash
docker compose run --rm freqtrade ...
```

Cách này không publish cổng ra máy host, nên không thể tranh chấp với `5432`, `5433` hoặc dịch vụ khác. Container chỉ dùng network nội bộ của Compose trong thời gian chạy lệnh.

### UI/paper trading sau này dùng port riêng

Chỉ khi người dùng cần FreqUI hoặc dry-run mới publish:

```yaml
ports:
  - "8090:8080"
```

FreqUI sẽ truy cập tại `http://localhost:8090`. Port `8080` là port nội bộ của container; `8090` là port riêng trên host.

## Cô lập dữ liệu và network

- Freqtrade chạy trong Compose project riêng, ví dụ project name `freqtrade`.
- Không dùng tên container, network hoặc volume của project `docker` hiện tại.
- Source Freqtrade nằm trong `vendor/freqtrade/` và được bỏ qua khỏi Git parent repo.
- `user_data/` chứa config, dữ liệu lịch sử, SQLite, log và report; tất cả được giữ local và bỏ qua khỏi Git.
- Không thêm API key, API secret, quyền rút tiền, leverage, futures hoặc lệnh live.

## Quy trình triển khai

1. Xác minh Docker Compose project hiện tại vẫn chạy bình thường.
2. Clone Freqtrade branch `stable` vào `vendor/freqtrade/`.
3. Kiểm tra Compose file mà không khởi động bot.
4. Tạo `user_data/` và chạy backtest bằng `docker compose run --rm`.
5. Chỉ thêm mapping `8090:8080` trong một thay đổi riêng nếu người dùng yêu cầu UI/dry-run.
6. Kiểm tra parent Git status, container list và port bindings sau mỗi thay đổi.

## Xử lý xung đột

- Nếu `8090` đã bị chiếm trước khi bật UI, dừng triển khai UI và chọn một port khác sau khi xác nhận.
- Nếu container hiện tại có trạng thái bất thường, không restart hoặc chỉnh sửa nó; chỉ báo cáo và giữ Freqtrade chưa chạy.
- Nếu Docker Compose tự tạo network/volume khác tên dự kiến, kiểm tra tên thực tế trước khi tiếp tục.

