# Monitoring PostgreSQL

## Session đang hoạt động

```sql
SELECT pid, usename, datname, state, wait_event_type, wait_event,
       now() - query_start AS duration,
       left(query, 120) AS query
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY duration DESC NULLS LAST;
```

## Các kết nối theo trạng thái

```sql
SELECT state, count(*)
FROM pg_stat_activity
GROUP BY state
ORDER BY count(*) DESC;
```

Các cột nhạy cảm có thể bị ẩn hoặc trả `NULL` tùy quyền người xem. Để tổng hợp truy vấn theo thời gian, có thể cân nhắc extension `pg_stat_statements` nếu môi trường được cấu hình phù hợp.

Tham khảo: [Monitoring database activity](https://www.postgresql.org/docs/current/monitoring-stats.html).
