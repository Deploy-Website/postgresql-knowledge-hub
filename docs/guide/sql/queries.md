# SQL cho ứng dụng thực tế

Giả sử bảng `orders` có các cột `id`, `customer_id`, `status`, `created_at`.

## Lọc và sắp xếp

```sql
SELECT id, customer_id, status, created_at
FROM orders
WHERE status = 'PAID'
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

## Thống kê theo khách hàng

```sql
SELECT customer_id, count(*) AS total_orders
FROM orders
WHERE status = 'PAID'
GROUP BY customer_id
ORDER BY total_orders DESC;
```

## Tránh SELECT * khi không cần thiết

Trong API, chỉ lấy trường cần thiết để giảm dữ liệu truyền và rõ ràng contract trả về. Luôn sử dụng bind parameters ở tầng application thay vì nối chuỗi SQL từ input.

Tham khảo: [Queries](https://www.postgresql.org/docs/current/queries.html).
