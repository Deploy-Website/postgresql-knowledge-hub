# Chạy PostgreSQL bằng Docker

Kịch bản development: khởi tạo PostgreSQL riêng trong Docker Engine trên Linux hoặc WSL Ubuntu.

=== "Docker CLI"

    ```bash
    docker volume create pgdocs-data
    docker run -d \
      --name pgdocs-db \
      -e POSTGRES_USER=app \
      -e POSTGRES_PASSWORD=change-me-dev-only \
      -e POSTGRES_DB=appdb \
      -p 127.0.0.1:5432:5432 \
      -v pgdocs-data:/var/lib/postgresql \
      postgres:18
    ```

=== "Compose"

    ```yaml
    services:
      postgres:
        image: postgres:18
        environment:
          POSTGRES_USER: app
          POSTGRES_PASSWORD: change-me-dev-only
          POSTGRES_DB: appdb
        ports:
          - "127.0.0.1:5432:5432"
        volumes:
          - pgdocs-data:/var/lib/postgresql
    volumes:
      pgdocs-data:
    ```

## Kết nối vào container

```bash
docker exec -it pgdocs-db psql -U app -d appdb
```

!!! warning "Chỉ dành cho môi trường phát triển"
    Mật khẩu trong ví dụ không an toàn cho production. Trong dự án thật, quản lý secrets riêng và kiểm soát việc mở cổng kết nối.

!!! note "Lưu trữ phiên bản 18"
    Docker Official Image PostgreSQL 18 dùng bố cục volume khác phiên bản trước; kiểm tra [docker-library/postgres](https://github.com/docker-library/docs/blob/master/postgres/README.md) trước khi đổi major version.
