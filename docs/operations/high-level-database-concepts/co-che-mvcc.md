---
title: Cơ chế MVCC (Multi-Version Concurrency Control)
description: Kiến trúc đa phiên bản, cột ẩn xmin/xmax, Snapshot, Bloat, HOT Update và XID Wraparound.
icon: material/layers-triple
status: new
---

# MVCC trong PostgreSQL

!!! abstract "Nguyên lý cốt lõi"
    **MVCC** cho phép nhiều giao dịch đọc và ghi đồng thời mà không chặn lẫn nhau (*readers never block writers, and writers never block readers*) bằng cách duy trì nhiều phiên bản (tuples) của dữ liệu.

## 1. Kiến trúc Tuple & Quy tắc Hiển thị

Mỗi dòng dữ liệu (tuple) lưu trữ các cột hệ thống ẩn để kiểm soát phiên bản:

| Cột ẩn | Vai trò Internals |
| :--- | :--- |
| **`xmin`** | XID của giao dịch đã `INSERT` tạo ra phiên bản bản ghi này. |
| **`xmax`** | XID của giao dịch đã `DELETE` hoặc `UPDATE` bản ghi này (`0` nếu chưa bị xóa/sửa). |
| **`ctid`** | Tọa độ vật lý `(page, offset)` của phiên bản bản ghi trên ổ đĩa. |

!!! info "Bản chất thao tác ghi"
    PostgreSQL **không ghi đè tại chỗ (in-place)**: `UPDATE` thực chất là `DELETE` (gán `xmax` cho bản ghi cũ) kết hợp `INSERT` (tạo bản ghi mới với `xmin` và `ctid` mới). Một giao dịch chỉ nhìn thấy bản ghi nếu `xmin` đã `COMMIT` trước thời điểm chụp **Snapshot** và `xmax` chưa `COMMIT`.

## 2. Vận hành Thực chiến & Phỏng vấn

=== "Table Bloat & VACUUM"
    * **Nguyên nhân:** Các phiên bản cũ sau `UPDATE`/`DELETE` trở thành **Dead Tuples**, gây phình dung lượng bảng/index (Bloat) và làm chậm truy vấn.
    * **Xử lý:** **Autovacuum** dọn dẹp dead tuples và cập nhật *Free Space Map (FSM)* để tái sử dụng không gian trống (không trả dung lượng về OS trừ khi dùng `VACUUM FULL` hoặc `pg_repack`).

=== "Bẫy Idle Transaction"
    * Giao dịch mở (`BEGIN`) nhưng treo ở trạng thái `idle in transaction` sẽ giữ nguyên Snapshot cũ, khiến **Autovacuum không thể dọn dead tuples** phát sinh sau đó.
    * **Best Practice:** Luôn thiết lập `idle_in_transaction_session_timeout` trên Production để tự động ngắt các phiên treo.

=== "HOT Update (Tối ưu Ghi)"
    * Nếu cột bị `UPDATE` **không đánh Index** và trang 8KB hiện tại **còn đủ chỗ trống**, PostgreSQL thực hiện **Heap-Only Tuple (HOT) Update** — cập nhật trực tiếp trong trang mà không cần ghi lại Index.
    * **Tuning:** Đặt `fillfactor = 70..80` cho các bảng hay bị `UPDATE` để chừa sẵn không gian trống trên trang 8KB.

=== "XID Wraparound"
    * XID là số nguyên 32-bit (~4.2 tỷ giao dịch). Nếu không được dọn dẹp, bộ đếm quay vòng sẽ làm sai lệch quy tắc hiển thị dữ liệu, buộc PostgreSQL khóa toàn bộ thao tác ghi để bảo vệ DB.
    * **Cơ chế chống tràn:** `VACUUM FREEZE` đánh dấu các bản ghi cũ thành `FrozenXID` để tái sử dụng vòng đời XID.

!!! tip "Lệnh kiểm tra thực tế trên SQL"
    ```sql
    -- Xem trực tiếp các cột ẩn MVCC của một bảng
    SELECT xmin, xmax, ctid, * FROM ten_bang LIMIT 5;
    ```
