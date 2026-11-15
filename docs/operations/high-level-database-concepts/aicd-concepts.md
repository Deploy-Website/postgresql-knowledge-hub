# ACID trong PostgreSQL: Bản chất & Thực chiến

!!! abstract "Tổng quan"
    **ACID** là 4 đặc tính cốt lõi đảm bảo các giao dịch (transaction) cơ sở dữ liệu được xử lý tin cậy và toàn vẹn, ngay cả khi xảy ra sự cố phần cứng hoặc xung đột đồng thời.

## 1. Bản chất & Cơ chế nội tại

| Tính chất | Bản chất | Cơ chế triển khai trong PostgreSQL |
| :--- | :--- | :--- |
| **A**tomicity *(Nguyên tử)* | **"Tất cả hoặc không có gì"** | Quản lý trạng thái giao dịch qua `XID` trong `pg_xact`; hỗ trợ `SAVEPOINT` để hoàn tác từng phần. |
| **C**onsistency *(Nhất quán)* | **"Dữ liệu luôn hợp lệ"** | Ép buộc qua `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `CHECK`, `NOT NULL`, `Triggers` và `DEFERRABLE`. |
| **I**solation *(Cô lập)* | **"Đồng thời không xung đột"** | **MVCC** (cột ẩn `xmin`, `xmax`) giúp đọc/ghi không chặn nhau; hỗ trợ 3 mức cô lập thực tế (*Read Committed*, *Repeatable Read*, *Serializable*). |
| **D**urability *(Bền vững)* | **"Commit là bất biến"** | **WAL** (`pg_wal`) ghi tuần tự ra đĩa trước khi cập nhật dữ liệu chính; phục hồi qua `Checkpoint` & `fsync`. |

## 2. Áp dụng thực tế trong dự án

=== "Atomicity (Giao dịch & Khóa)"

    **Bài toán:** Tạo đơn hàng, trừ tồn kho và trừ tiền ví phải thành công cùng lúc, hoặc hủy toàn bộ nếu 1 bước lỗi. Ngoài ra, dùng để chống chạy trùng Cron Job.

    ```sql
    BEGIN;
    -- 1. Khóa chống chạy trùng tiến trình ngầm (tự nhả khóa khi COMMIT/ROLLBACK)
    SELECT pg_try_advisory_xact_lock(1001);

    -- 2. Chuỗi thao tác nghiệp vụ
    UPDATE wallets SET balance = balance - 500 WHERE user_id = 1;
    UPDATE products SET stock = stock - 1 WHERE id = 99;
    INSERT INTO orders (user_id, product_id) VALUES (1, 99);
    COMMIT;
    ```

=== "Consistency (Chốt chặn DB)"

    **Bài toán:** Code Backend luôn có thể dính bug hoặc bị gọi API song song gây sai lệch số dư, âm kho.

    !!! tip "Nguyên tắc thiết kế"
        Luôn đặt ràng buộc trực tiếp dưới Database thay vì chỉ validate ở tầng Application:
        ```sql
        ALTER TABLE products ADD CONSTRAINT check_positive_stock CHECK (stock >= 0);
        ALTER TABLE wallets ADD CONSTRAINT check_positive_balance CHECK (balance >= 0);
        ```

=== "Isolation (Chống Race Condition)"

    **Bài toán:** Săn sale món hàng cuối cùng. Mức mặc định `Read Committed` dễ gây bán lố (Overselling).

    * **Giải pháp 1 (Nâng cấp Isolation):** Dùng `Repeatable Read` hoặc `Serializable` (cần viết logic retry ở Backend khi DB báo lỗi xung đột mã `40001`).
    * **Giải pháp 2 (Khóa bi quan):** Dùng `SELECT ... FOR UPDATE` khi cần khóa trực tiếp dòng dữ liệu đang tranh chấp.

    ```sql
    BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;
    -- Đọc snapshot nhất quán tại thời điểm bắt đầu transaction
    SELECT stock FROM products WHERE id = 99;
    UPDATE products SET stock = stock - 1 WHERE id = 99;
    COMMIT;
    ```

=== "Durability (Tối ưu hiệu năng)"

    **Bài toán:** Đánh đổi giữa **độ an toàn tuyệt đối** và **tốc độ ghi (Throughput)** thông qua tham số `synchronous_commit`.

    | Loại hệ thống | Cấu hình khuyến nghị | Hệ quả thực tế |
    | :--- | :--- | :--- |
    | **Tài chính, Thanh toán** | `fsync = on`<br>`synchronous_commit = on` | Đảm bảo 100% dữ liệu nằm trên ổ cứng trước khi báo thành công. |
    | **Tracking, Log hành vi** | `fsync = on`<br>`synchronous_commit = off` | Tăng tốc độ ghi gấp nhiều lần; chấp nhận mất vài mili-giây log cuối nếu sập nguồn. |

## 3. Tóm tắt quy tắc áp dụng

!!! warning "Lưu ý khi lên Production"
    1. **Không giữ Transaction mở quá lâu:** Gây phình to bảng (Table Bloat) do MVCC không dọn được rác (`VACUUM`) và giữ khóa gây nghẽn hệ thống.
    2. **Luôn xử lý Retry với `40001`:** Khi dùng `Repeatable Read` hoặc `Serializable`, ứng dụng bắt buộc phải bắt lỗi `serialization_failure` để chạy lại giao dịch.