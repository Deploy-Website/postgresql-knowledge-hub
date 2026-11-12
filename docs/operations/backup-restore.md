# Backup & Restore

`pg_dump` tạo backup logic cho một database; `pg_restore` khôi phục archive được tạo ở custom/directory/tar format.

## Dump custom format

```bash
pg_dump -h localhost -U app -d appdb -Fc -f appdb.dump
```

## Restore vào database đã tạo

```bash
createdb -h localhost -U app appdb_restore
pg_restore -h localhost -U app -d appdb_restore --no-owner appdb.dump
```

!!! warning "Kiểm thử restore"
    Backup chỉ thực sự hữu ích khi có thể restore thành công. Kiểm thử định kỳ trên môi trường cô lập và kiểm tra quyền/extension/schema. `pg_dump` không thay thế chiến lược PITR (point-in-time recovery) khi cần RPO thấp.

Tham khảo: [Backup and Restore](https://www.postgresql.org/docs/current/backup.html).
