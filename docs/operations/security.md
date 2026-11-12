# Roles & Security

Nên tách vai trò quản trị và tài khoản ứng dụng, cấp quyền tối thiểu cần thiết.

## Ví dụ phân quyền cho app

```sql
CREATE ROLE app_reader LOGIN PASSWORD 'replace-with-secure-secret';
GRANT CONNECT ON DATABASE appdb TO app_reader;
-- Thực thi trong database appdb:
GRANT USAGE ON SCHEMA public TO app_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_reader;
```

Cấp quyền cho bảng tạo mới cần `ALTER DEFAULT PRIVILEGES` đúng role tạo bảng. Tránh lưu secrets trong source code, shell history hoặc trong tài liệu nội bộ công khai.

Tham khảo: [Database Roles](https://www.postgresql.org/docs/current/user-manag.html), [Privileges](https://www.postgresql.org/docs/current/ddl-priv.html).
