# Quy trình tối ưu truy vấn

1. **Ghi nhận baseline**: SQL, parameters, thời gian thực thi, số dòng, tài nguyên I/O.
2. **Đọc execution plan**: dùng `EXPLAIN (ANALYZE, BUFFERS)` với dữ liệu đại diện.
3. **Tìm bottleneck**: scan quá nhiều, sort, join cardinality sai, filter không chọn lọc, blocking.
4. **Thử một thay đổi**: viết lại predicate, cập nhật thống kê hoặc bổ sung index phù hợp.
5. **Đo lại**: cùng tham số, điều kiện hệ thống tương đương và nhiều lượt chạy.
6. **Kiểm thử hồi quy**: query khác, chi phí ghi, disk usage, thay đổi dữ liệu.

## Ví dụ cập nhật thống kê

```sql
ANALYZE orders;
```

!!! tip "Nguyên tắc"
    Đừng tối ưu chỉ theo `cost` ước lượng. So sánh **thời gian thực tế + buffers + tính đúng của kết quả**.

Tham khảo: [Performance Tips](https://www.postgresql.org/docs/current/performance-tips.html).
