# Pagination: offset và keyset

Với dữ liệu lớn và trang nằm sâu, `OFFSET` có thể phải duyệt nhiều bản ghi trước khi trả trang hiện tại. Keyset pagination thường phù hợp hơn với chức năng “Load more”.

## Offset (đơn giản)

```sql
SELECT id, created_at
FROM orders
ORDER BY created_at DESC, id DESC
LIMIT 50 OFFSET 10000;
```

## Keyset (cursor)

```sql
SELECT id, created_at
FROM orders
WHERE (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

Index tham khảo:

```sql
CREATE INDEX CONCURRENTLY idx_orders_created_id
ON orders (created_at DESC, id DESC);
```

`created_at` cần được định nghĩa `NOT NULL` hoặc xử lý `NULL` rõ ràng; cột `id` đảm bảo thứ tự quyết định. Với kết quả có thể thay đổi liên tục, cả hai cách đều cần cân nhắc consistency của phân trang.

Tham khảo: [LIMIT and OFFSET](https://www.postgresql.org/docs/current/queries-limit.html), [Indexes and ORDER BY](https://www.postgresql.org/docs/current/indexes-ordering.html).
