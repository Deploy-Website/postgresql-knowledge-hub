# Indexing

Index tăng tốc nhiều loại truy vấn nhưng làm tăng chi phí ghi, dung lượng lưu trữ và bảo trì. Vì vậy nên tạo index theo **workload thực tế**.

## Index phù hợp với truy vấn

Với truy vấn lọc theo `customer_id` và sắp xếp theo thời gian:

```sql
CREATE INDEX CONCURRENTLY idx_orders_customer_created
ON orders (customer_id, created_at DESC, id DESC);
```

!!! note "CREATE INDEX CONCURRENTLY"
    Có thể giảm mức chặn ghi so với `CREATE INDEX` thông thường, nhưng tốn thêm công việc và không chạy bên trong transaction block.

## Các loại index hay gặp

| Loại | Tình huống phổ biến |
|---|---|
| B-tree | So sánh, range, ORDER BY |
| GIN | `jsonb`, arrays, full-text search |
| BRIN | Bảng rất lớn, cột tương quan với thứ tự vật lý |

!!! tip "Cách đánh giá"
    Đo bằng `EXPLAIN (ANALYZE, BUFFERS)` trên dữ liệu và thống kê đại diện. Đừng tạo index chỉ vì một cột xuất hiện trong `WHERE`.

Tham khảo: [Indexes](https://www.postgresql.org/docs/current/indexes.html).
