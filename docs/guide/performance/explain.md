# Đọc EXPLAIN ANALYZE

`EXPLAIN` cho biết kế hoạch thực thi dự kiến. `EXPLAIN ANALYZE` **thực sự chạy** câu lệnh và bổ sung số liệu thực tế.

## Ví dụ

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT id, created_at
FROM orders
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 20;
```

## Các chỉ số nên đọc

- **Execution Time**: tổng thời gian thực thi, có thể thay đổi theo tải hệ thống.
- **actual time / rows / loops**: thời gian, số hàng và số vòng lặp thực tế của node.
- **Buffers**: số buffer hit/read/dirtied/written, giúp nhận diện I/O.
- **Rows Removed by Filter**: số hàng bị loại khi lọc.

!!! warning "Tránh tác động dữ liệu"
    Với `INSERT`, `UPDATE`, `DELETE` hoặc `MERGE`, `EXPLAIN ANALYZE` vẫn thực thi thao tác; dùng transaction có `ROLLBACK` nếu chỉ muốn kiểm tra plan và không muốn giữ thay đổi. Chú ý các side effect ngoài DB không nhất thiết có thể rollback.

Tham khảo: [Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html).
