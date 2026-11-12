# Truy vấn chờ lock

Khi một truy vấn chờ lâu, kiểm tra xem nó có bị session khác chặn hay không.

```sql
SELECT a.pid, a.state, a.wait_event_type, a.wait_event,
       pg_blocking_pids(a.pid) AS blocking_pids,
       now() - a.query_start AS duration,
       left(a.query, 120) AS query
FROM pg_stat_activity AS a
WHERE cardinality(pg_blocking_pids(a.pid)) > 0
ORDER BY duration DESC NULLS LAST;
```

## Xử lý an toàn

- Xác định transaction block, owner và nghiệp vụ liên quan.
- Kiểm tra transaction đang `idle in transaction`.
- Ưu tiên xử lý logic ứng dụng; chỉ hủy query/session khi đã đánh giá tác động.

Tham khảo: [Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html), [Monitoring](https://www.postgresql.org/docs/current/monitoring-stats.html).
