# Không thể kết nối PostgreSQL

## Kiểm tra theo tầng

1. **Service**: PostgreSQL đã chạy và đang listen đúng port?
2. **Network**: port có được publish/forward từ Docker hoặc WSL không?
3. **Auth**: tên database/user/password và `pg_hba.conf`?
4. **TLS**: server yêu cầu SSL hay chứng chỉ không tin cậy?

## Các lệnh hữu ích

```bash
# Trong Linux/WSL
ss -ltn | grep 5432
pg_isready -h 127.0.0.1 -p 5432

docker ps
docker logs --tail 100 pgdocs-db
```

Nếu client Windows kết nối Docker trong WSL, kiểm tra IP/port mapping trên cả Windows và WSL; `localhost` có thể hoạt động khác nhau theo WSL networking mode.

Tham khảo: [Client Authentication](https://www.postgresql.org/docs/current/client-authentication.html).
