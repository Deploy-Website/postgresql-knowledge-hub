# Transaction & MVCC

PostgreSQL sử dụng **MVCC** (Multiversion Concurrency Control) để các transaction có thể quan sát snapshot dữ liệu phù hợp mức cách ly.

## Ví dụ chuyển trạng thái đơn hàng

```sql
BEGIN;
UPDATE orders
SET status = 'PAID'
WHERE id = 1001 AND status = 'PENDING';
-- Ứng dụng cần kiểm tra số dòng bị cập nhật.
COMMIT;
```

## Điểm cần nhớ

- `READ COMMITTED` là transaction isolation mặc định của PostgreSQL.
- `UPDATE` có thể phải chờ row lock; transaction dài làm tăng thời gian chờ và gây khó khăn cho VACUUM.
- Khi nhiều transaction cập nhật cùng bản ghi, cần thiết kế retry có kiểm soát ở tầng ứng dụng.

Tham khảo: [Transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html), [MVCC](https://www.postgresql.org/docs/current/mvcc.html).
