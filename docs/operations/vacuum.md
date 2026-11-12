# VACUUM & ANALYZE

`VACUUM` dọn các dead tuples để tái sử dụng dung lượng và hỗ trợ duy trì sức khỏe lưu trữ; `ANALYZE` cập nhật thống kê phục vụ query planner.

## Thao tác

```sql
VACUUM (VERBOSE, ANALYZE) orders;
```

## Tình huống thực tế

Sau batch `UPDATE`/`DELETE` lớn, hãy kiểm tra autovacuum, tỉ lệ dead tuples và hiệu năng truy vấn. Không mặc định chạy `VACUUM FULL` vì lệnh này khóa bảng mạnh và cần thêm dung lượng lưu trữ.

Tham khảo: [Routine VACUUM](https://www.postgresql.org/docs/current/routine-vacuuming.html), [VACUUM](https://www.postgresql.org/docs/current/sql-vacuum.html).
