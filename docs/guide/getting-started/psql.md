# Kết nối PostgreSQL bằng psql

`psql` là client dòng lệnh chính thức để quản trị và chạy SQL.

## Kết nối

```bash
psql -h localhost -p 5432 -U app_user -d appdb
```

Dùng `-W` nếu muốn buộc hỏi mật khẩu. Không đưa mật khẩu vào câu lệnh shell hoặc repository.

## Các lệnh hữu ích

```text
\conninfo       -- Hiển thị kết nối hiện tại
\l              -- Danh sách database
\dt             -- Danh sách table trong search_path
\d+ orders      -- Mô tả bảng orders
\timing on      -- Bật thời gian chạy lệnh
\q              -- Thoát
```

## Kiểm tra phiên bản

```sql
SELECT version();
SHOW server_version;
SHOW client_encoding;
```

Tham khảo: [psql official manual](https://www.postgresql.org/docs/current/app-psql.html).
