---
title: Xử lý bẫy Idle in Transaction
description: Runbook toàn diện điều tra, xử lý và phòng tránh bẫy Idle in Transaction trong PostgreSQL, Amazon Aurora và Spring Boot.
icon: material/database-clock
---

# Xử lý bẫy Idle in Transaction

!!! abstract "Bản chất & Phạm vi áp dụng"
    * **Khái niệm:** `idle in transaction` là trạng thái một database session đã mở giao dịch (`BEGIN`) nhưng tạm dừng không gửi lệnh SQL tiếp theo tới PostgreSQL, đồng thời cũng chưa kết thúc bằng `COMMIT` hoặc `ROLLBACK`.
    * **Phạm vi áp dụng:** PostgreSQL (mọi phiên bản), Amazon Aurora PostgreSQL, Java / Spring Boot (`@Transactional`, Spring Data JPA/Hibernate), HikariCP.
    * **Hệ quả chính:** Gây cạn kiệt Connection Pool (`ConnectionTimeoutException`), cản trở `VACUUM` dọn dẹp Dead Tuples dẫn đến Table/Index Bloat nghiêm trọng, và có thể giữ các loại khóa (Locks) làm treo nghẽn diện rộng.

---

## 1. Bản chất & Cơ chế phát sinh lỗi

### 1.1. Phân biệt các trạng thái của Session

Trong bảng quản lý `pg_stat_activity`, mỗi session luôn thuộc một trong các trạng thái sau:

| Trạng thái | Hành vi của Database Backend | Đánh giá rủi ro |
| :--- | :--- | :--- |
| **`active`** | Backend đang tích cực xử lý dữ liệu hoặc chờ tài nguyên đĩa/CPU cho query hiện tại. | Bình thường (trừ khi query chạy chậm bất thường vượt SLA). |
| **`idle`** | Kết nối đang rảnh rỗi trong pool, **không có transaction nào đang mở**. | Hoàn toàn an toàn và lành mạnh. |
| **`idle in transaction`** | Giao dịch đã mở nhưng client dừng gửi lệnh (đang bận làm việc khác). | **Nguy hiểm**: Giữ Snapshot cũ, giữ Connection và có thể giữ Lock. |
| **`idle in transaction (aborted)`** | Giao dịch gặp lỗi cú pháp/ràng buộc nhưng ứng dụng chưa gọi `ROLLBACK`. | **Nguy hiểm**: Chiếm dụng tài nguyên tương tự như trên cho đến khi bị đóng. |

### 1.2. Chu trình phát sinh bẫy trong ứng dụng

Nguyên nhân phổ biến nhất trong thực tế là việc đặt annotation `@Transactional` bao trùm toàn bộ method nghiệp vụ chứa các tác vụ bên ngoài (External I/O):

```text
│ 1. Client gửi request -> Spring kích hoạt method @Transactional
│    └── HikariCP cấp Connection -> Gửi BEGIN mở transaction trên PostgreSQL
│                                                                
│ 2. Thực hiện câu lệnh SQL đầu tiên                             
│    └── SELECT / UPDATE hoàn tất nhanh chóng trong vài mili-giây
│                                                                
│ 3. ⚠️ BẪY NGUY HIỂM: Gọi HTTP API bên ngoài / Xử lý File / Đợi Message Queue
│    ├── Client tạm ngừng gửi câu lệnh SQL cho Database          
│    ├── Database: Chuyển sang trạng thái "idle in transaction"  
│    ├── Giữ nguyên Snapshot MVCC (chặn Autovacuum dọn dẹp Dead Tuples)     
│    ├── Giữ khóa dòng/bảng (có thể gây Lock Wait / Treo request khác)      
│    └── HikariCP Connection bị chiếm dụng (Active tăng cao, gây nghẽn pool)
│                                                                
│ 4. Sau vài giây / vài phút chờ đối tác phản hồi                
│    └── Ứng dụng mới gửi câu lệnh SQL kế tiếp hoặc gửi lệnh COMMIT         

```

---

## 2. Tác hại đối với Database & Ứng dụng

| Tác động | Cơ chế nội tại & Hậu quả thực tế |
| :--- | :--- |
| **Cạn connection pool** | Connection bị chiếm giữ cứng trong suốt thời gian client chờ dịch vụ ngoài, khiến HikariCP rơi vào trạng thái `Active` tăng vọt, các request mới bị dồn vào hàng đợi `Pending` và kết thúc bằng lỗi `ConnectionTimeoutException`. |
| **Cản trở VACUUM & Table Bloat** | Transaction giữ Snapshot tương ứng với `backend_xmin` cũ. **Autovacuum không thể xóa bất kỳ Dead Tuple nào** có tuổi đời sau thời điểm đó, khiến bảng và Index phình to nhanh chóng (Bloat), gây suy giảm bộ đệm RAM (Shared Buffers). |
| **Giữ Lock gây nghẽn dây chuyền** | Nếu transaction đã thực hiện lệnh ghi (`UPDATE`, `DELETE`, `SELECT ... FOR UPDATE`), các row lock hoặc table lock sẽ được giữ nguyên cho tới khi `COMMIT`/`ROLLBACK`. Các transaction khác cập nhật cùng dòng sẽ bị chặn đứng (Lock Wait). |
| **Nguy cơ XID Wraparound** | Nếu một transaction bị treo nhiều giờ hoặc nhiều ngày, nó giữ chặn bộ đếm giao dịch toàn cục, đẩy database tới gần ngưỡng khẩn cấp phòng chống tràn số XID. |

!!! note "Lưu ý về Snapshot và Lock"
    Không phải cứ `idle in transaction` là sẽ giữ Lock. Nhưng một transaction mở lâu **luôn luôn giữ Snapshot**, gây cản trở `VACUUM` ngay cả khi chỉ thực hiện các câu lệnh đọc (`SELECT`). Do đó, cần xử lý triệt để ngay cả khi không thấy có session khác bị block.

---

## 3. Runbook điều tra trên PostgreSQL

Sử dụng các truy vấn sau trực tiếp trên môi trường cần giám sát:

=== "1. Liệt kê session treo"

    Truy vấn danh sách các session đang ở trạng thái `idle in transaction`, sắp xếp theo thời gian mở giao dịch lâu nhất:

    ```sql
    SELECT
        pid,
        usename,
        application_name,
        client_addr,
        state,
        now() - xact_start AS transaction_duration,
        now() - state_change AS idle_duration,
        backend_xid,
        backend_xmin,
        left(query, 200) AS last_query
    FROM pg_stat_activity
    WHERE state IN ('idle in transaction', 'idle in transaction (aborted)')
    ORDER BY xact_start ASC;
    ```

    **Ý nghĩa các cột quan trọng:**
    * `pid`: Mã định danh tiến trình backend (dùng để hủy hoặc ngắt kết nối).
    * `application_name`: Tên định danh ứng dụng (giúp phân biệt Web API, Worker hay Batch Job).
    * `transaction_duration`: Tổng thời gian transaction đã mở (càng lớn càng nguy hiểm).
    * `idle_duration`: Thời gian backend không nhận thêm query nào kể từ câu lệnh gần nhất.
    * `backend_xmin`: Điểm mốc snapshot MVCC (dùng để xác định nguy cơ chặn `VACUUM`).

=== "2. Tìm session gây nghẽn (Blocker)"

    Xác định chính xác session nào đang giữ Lock và chặn các session khác chờ đợi:

    ```sql
    SELECT
        blocked.pid AS blocked_pid,
        blocked.application_name AS blocked_app,
        blocked.state AS blocked_state,
        now() - blocked.query_start AS blocked_duration,
        blocker.pid AS blocker_pid,
        blocker.application_name AS blocker_app,
        blocker.state AS blocker_state,
        now() - blocker.xact_start AS blocker_transaction_duration,
        left(blocked.query, 120) AS blocked_query,
        left(blocker.query, 120) AS blocker_last_query
    FROM pg_stat_activity AS blocked
    CROSS JOIN LATERAL unnest(pg_blocking_pids(blocked.pid)) AS p(blocker_pid)
    JOIN pg_stat_activity AS blocker ON blocker.pid = p.blocker_pid
    ORDER BY blocked.query_start;
    ```

    !!! tip "Đọc kết quả"
        Nếu `blocker_state` hiển thị `idle in transaction`, đây chính là trường hợp kinh điển: ứng dụng đã cập nhật dữ liệu nhưng không commit/rollback, khiến câu query của các session khác (`blocked_pid`) bị treo vô hạn định.

=== "3. Thống kê tổng quan trạng thái"

    Đếm số lượng kết nối phân bổ theo từng ứng dụng và trạng thái:

    ```sql
    SELECT
        coalesce(application_name, '[Unknown]') AS app_name,
        state,
        count(*) AS total_connections
    FROM pg_stat_activity
    WHERE datname = current_database()
    GROUP BY application_name, state
    ORDER BY app_name, total_connections DESC;
    ```

---

## 4. Xử lý khẩn cấp (Emergency Runbook)

Khi phát hiện session gây treo hệ thống trên Production, thực hiện theo thứ tự ưu tiên:

### Bước 1: Đánh giá trước khi can thiệp
1. Xác định PID thuộc dịch vụ nào qua `application_name` và `client_addr`.
2. Kiểm tra câu lệnh gần nhất (`query`) và thời gian mở (`transaction_duration`).
3. Kiểm tra xem PID này có đang chặn các query khác không (qua `pg_blocking_pids`).

### Bước 2: Hủy hoặc Buộc ngắt kết nối

* **`pg_cancel_backend(pid)` (Hủy query hiện tại):**
    ```sql
    SELECT pg_cancel_backend(12345);
    ```
    > [!NOTE]
    > Lệnh này chỉ hủy query đang chạy ở trạng thái `active`. **Không có tác dụng** đối với session đang ở trạng thái `idle in transaction`.

* **`pg_terminate_backend(pid)` (Ngắt toàn bộ kết nối):**
    ```sql
    SELECT pg_terminate_backend(12345);
    ```
    Lệnh này sẽ lập tức đóng kết nối TCP của backend. PostgreSQL sẽ tự động **ROLLBACK** giao dịch đang dang dở và giải phóng toàn bộ khóa (locks) cùng Snapshot.

!!! danger "Nguyên tắc an toàn trên Production"
    * **Không chạy terminate hàng loạt:** Tránh dùng lệnh `terminate` trên toàn bộ bảng mà không lọc điều kiện thời gian (`transaction_duration > interval '5 minutes'`) và loại trừ chính session quản trị của bạn.
    * **Hệ quả phía ứng dụng:** Khi backend bị terminate, ứng dụng client sẽ nhận lỗi kết nối (ví dụ `PSQLException: FATAL: terminating connection`). Đảm bảo ứng dụng có cơ chế retry an toàn hoặc xử lý ngoại lệ phù hợp.

---

## 5. Phòng ngừa tại PostgreSQL & Amazon Aurora

Thiết lập "dây đai an toàn" trực tiếp trên database để tự động tiêu diệt các session bị bỏ quên.

### 5.1. Cấu hình `idle_in_transaction_session_timeout`

Tham số này quy định thời gian tối đa một session được phép dừng chờ sau khi đã mở transaction. Khi vượt ngưỡng, PostgreSQL sẽ chủ động ngắt kết nối.

=== "Cấu hình cấp Database"
    ```sql
    -- Áp dụng cho toàn bộ kết nối vào database chỉ định
    ALTER DATABASE app_production 
    SET idle_in_transaction_session_timeout = '60s';
    ```

=== "Cấu hình cấp User/Role (Khuyên dùng)"
    ```sql
    -- Áp dụng riêng cho role của ứng dụng (tránh ảnh hưởng đến migration hoặc dba)
    ALTER ROLE app_user 
    SET idle_in_transaction_session_timeout = '60s';
    ```

=== "Kiểm tra hiệu lực"
    ```sql
    SELECT name, setting, unit, source 
    FROM pg_settings 
    WHERE name = 'idle_in_transaction_session_timeout';
    ```

### 5.2. So sánh các bộ Timeout cốt lõi

| Tham số | Mục đích bảo vệ | Hành vi khi kích hoạt |
| :--- | :--- | :--- |
| **`idle_in_transaction_session_timeout`** | Đóng session treo bên trong transaction | Ngắt kết nối backend, rollback transaction |
| **`statement_timeout`** | Giới hạn thời gian thực thi của một lệnh SQL đơn lẻ | Hủy câu lệnh SQL hiện tại, transaction chuyển sang `aborted` |
| **`lock_timeout`** | Giới hạn thời gian chờ xin cấp khóa | Hủy câu lệnh đang chờ khóa, tránh xếp hàng chờ dài |
| **`idle_session_timeout`** | Đóng session rảnh rỗi bên ngoài transaction | Đóng kết nối TCP rác không dùng đến |

### 5.3. Lưu ý riêng với Amazon Aurora PostgreSQL

1. **Parameter Groups:** Trong Aurora, cấu hình thông qua **DB Cluster Parameter Group** (áp dụng toàn cluster) hoặc **DB Parameter Group** (áp dụng từng instance).
2. **Dynamic Parameter:** `idle_in_transaction_session_timeout` là tham số **dynamic**, có hiệu lực ngay mà không yêu cầu reboot cluster.
3. **Aurora Serverless / Auto-scaling:** Đặt timeout hợp lý giúp giải phóng kết nối nhanh chóng, tránh kích hoạt mở rộng dung lượng (scale-up) không cần thiết do kết nối ảo.

---

## 6. Khắc phục triệt để trong Spring Boot

!!! tip "Nguyên tắc vàng"
    **Tuyệt đối không giữ Transaction Database trong lúc chờ công việc không thuộc Database.**
    Các tác vụ như: gọi HTTP API (Rest/Feign/WebClient), upload S3, gửi mail, hoặc xử lý file lớn **bắt buộc phải nằm ngoài** `@Transactional`.

=== "Anti-Pattern (Sai lầm phổ biến)"

    ```java
    @Service
    @RequiredArgsConstructor
    public class OrderProcessingService {

        private final OrderRepository orderRepository;
        private final PaymentGatewayClient paymentGatewayClient;

        @Transactional // ⚠️ NGUY HIỂM: Transaction bao trùm toàn bộ
        public void processOrder(Long orderId) {
            Order order = orderRepository.findById(orderId).orElseThrow();
            order.setStatus("PROCESSING");
            orderRepository.save(order); // Lệnh SQL đầu tiên chạy xong

            // BẪY: Cuộc gọi HTTP có thể mất từ 3s - 30s.
            // Trong suốt thời gian này, PostgreSQL rơi vào IDLE IN TRANSACTION!
            PaymentResponse payment = paymentGatewayClient.charge(order.getAmount());

            order.setStatus(payment.isSuccess() ? "PAID" : "FAILED");
            orderRepository.save(order);
        }
    }
    ```

=== "Clean Architecture (Giải pháp chuẩn)"

    Tách luồng xử lý thành 3 pha độc lập: **Read (DB) -> Remote Call (I/O) -> Write (DB)**:

    ```java
    @Service
    @RequiredArgsConstructor
    public class OrderProcessingFacade {

        private final OrderReadService orderReadService;
        private final PaymentGatewayClient paymentGatewayClient;
        private final OrderWriteService orderWriteService;

        // Method điều phối KHÔNG mang annotation @Transactional
        public void processOrder(Long orderId) {
            // 1. Pha đọc: Transaction mở và commit ngay lập tức
            OrderSnapshot snapshot = orderReadService.getOrderSnapshot(orderId);

            // 2. Pha External Call: Chạy bên ngoài transaction DB hoàn toàn
            PaymentResponse payment = paymentGatewayClient.charge(snapshot.amount());

            // 3. Pha ghi: Mở transaction mới, cập nhật và commit ngay
            orderWriteService.updateOrderStatus(orderId, payment.isSuccess());
        }
    }
    ```

    Chi tiết các Service thành phần:

    ```java
    @Service
    @RequiredArgsConstructor
    public class OrderReadService {
        private final OrderRepository orderRepository;

        @Transactional(readOnly = true)
        public OrderSnapshot getOrderSnapshot(Long orderId) {
            return orderRepository.findById(orderId)
                .map(OrderSnapshot::from) // Chuyển sang DTO bất biến
                .orElseThrow();
        }
    }

    @Service
    @RequiredArgsConstructor
    public class OrderWriteService {
        private final OrderRepository orderRepository;

        @Transactional
        public void updateOrderStatus(Long orderId, boolean success) {
            Order order = orderRepository.findById(orderId).orElseThrow();
            order.setStatus(success ? "PAID" : "FAILED");
        }
    }
    ```

### 6.1. Không truyền JPA Entity ra ngoài Transaction

Luôn chuyển đổi sang **Java Record / DTO** trước khi rời khỏi ranh giới transaction:

```java
public record OrderSnapshot(
    Long orderId,
    BigDecimal amount,
    String customerEmail
) {
    public static OrderSnapshot from(Order entity) {
        return new OrderSnapshot(entity.getId(), entity.getAmount(), entity.getEmail());
    }
}
```

* **Lợi ích:** Ngăn chặn hoàn toàn lỗi `LazyInitializationException` và tránh việc vô tình kích hoạt các câu truy vấn ngầm ngoài ý muốn (N+1 query problem).

### 6.2. Cảnh báo bẫy Self-Invocation trong Spring Proxy

Spring quản lý giao dịch bằng cơ chế AOP Proxy. Khi một method gọi một method khác `@Transactional` **trong cùng một Class**:
* Lời gọi **không đi qua Proxy**.
* Annotation `@Transactional` ở method được gọi sẽ **bị bỏ qua hoàn toàn**.
* **Giải pháp:** Luôn tách các method transactional sang một Spring Bean khác như cấu trúc Facade ở trên.

---

## 7. Cấu hình Connection Pool (HikariCP)

### 7.1. Cấu hình mẫu trong `application.yml`

```yaml
spring:
  datasource:
    hikari:
      pool-name: AppHikariCP
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000       # 30 giây: Hết thời gian chờ mượn connection
      max-lifetime: 1800000            # 30 phút: Vòng đời tối đa của 1 connection
      idle-timeout: 600000             # 10 phút: Thu hồi connection rảnh rỗi
      leak-detection-threshold: 60000  # 60 giây: Cảnh báo connection bị giữ quá lâu
```

### 7.2. Phân tích chức năng các tham số HikariCP

| Tham số | Vai trò | Có giải quyết được `Idle in Transaction`? |
| :--- | :--- | :--- |
| `maximum-pool-size` | Giới hạn số kết nối vật lý tối đa của pool | **Không**; tăng size chỉ trì hoãn sự cố, làm DB chịu tải nặng hơn. |
| `connection-timeout` | Thời gian tối đa ứng dụng chờ mượn kết nối | **Không**; chỉ quăng lỗi khi pool đã bị cạn kiệt. |
| `idle-timeout` | Đóng bớt kết nối rảnh rỗi khi vượt `minimumIdle` | **Không**; chỉ áp dụng cho kết nối `idle`, không áp dụng cho kết nối đang bận. |
| `leak-detection-threshold` | In stack trace cảnh báo kết nối bị giữ quá lâu | **Hỗ trợ điều tra**: Giúp định vị chính xác dòng code Java mượn connection mà quên trả. |

!!! warning "Lưu ý về Leak Detection"
    `leak-detection-threshold` chỉ ghi log cảnh báo kèm stack trace (vị trí lấy connection), **không tự động đóng connection hay hủy transaction**. Đây là công cụ hữu hiệu trong giai đoạn kiểm thử hoặc điều tra nguyên nhân.

---

## 8. Observability & Cảnh báo sớm

### 8.1. Đặt `ApplicationName` trên JDBC URL

Cấu hình tên định danh cho từng module giúp phân tách rõ ràng trên `pg_stat_activity`:

```text
jdbc:postgresql://postgres-db:5432/app_db?ApplicationName=order-service-api
```

Khuyến nghị đặt tên theo mẫu: `[service-name]-[workload-type]` (ví dụ: `order-api`, `billing-worker`, `report-batch`).

### 8.2. Cảnh báo sớm với Prometheus / CloudWatch

* **Ngưỡng giám sát PostgreSQL:**
    Cảnh báo khi có session `state = 'idle in transaction'` kéo dài quá 60 giây:
    ```sql
    SELECT count(*) 
    FROM pg_stat_activity 
    WHERE state = 'idle in transaction' 
      AND (now() - state_change) > interval '60 seconds';
    ```
* **Chỉ số HikariCP (Micrometer):**
    * `hikaricp.connections.active`: Tăng tiệm cận `maximum-pool-size`.
    * `hikaricp.connections.pending`: Lớn hơn 0 liên tục (báo hiệu request đang bị dồn ứ chờ connection).

---

## 9. Checklist kiểm tra trước khi lên Production

- [ ] **Không gọi HTTP/Third-party API** bên trong method `@Transactional`.
- [ ] **Không thực hiện tác vụ I/O chậm** (ghi file, message queue, xử lý ảnh) trong transaction.
- [ ] **Dữ liệu trả về ngoài transaction** là DTO / Record bất biến (không trả JPA Entity).
- [ ] **Đã kiểm tra Self-Invocation:** Các ranh giới transaction được gọi thông qua Spring Bean Proxy.
- [ ] **Cấu hình `ApplicationName`** trong JDBC connection string của mọi microservice.
- [ ] **Thiết lập `idle_in_transaction_session_timeout`** trên PostgreSQL (khuyến nghị 30s - 60s).
- [ ] **Bật HikariCP Metrics** và theo dõi `hikaricp.connections.pending`.
- [ ] **Có Runbook xử lý khẩn cấp** (`pg_terminate_backend`) phân quyền cho đội ngũ On-call.

---

## 10. Các hiểu lầm kinh điển (Common Pitfalls)

| Lầm tưởng | Thực tế kỹ thuật |
| :--- | :--- |
| *"Tăng `maximum-pool-size` sẽ hết lỗi cạn connection"* | **Sai lầm**. Nếu transaction bị treo 30 giây, mọi pool size dù là 20 hay 200 cũng sẽ bị lấp đầy sau vài chục request, đồng thời khiến CPU database quá tải. |
| *"Dùng `@Transactional(readOnly = true)` thì không lo bị bẫy"* | **Sai lầm**. `readOnly = true` chỉ tối ưu hóa flush mode của Hibernate; nó vẫn mở một transaction thật trên PostgreSQL và vẫn giữ Snapshot chặn `VACUUM`. |
| *"Cấu hình `idle-timeout` của HikariCP sẽ tự ngắt connection treo"* | **Sai lầm**. HikariCP chỉ thu hồi connection không có ai dùng. Connection đang nằm trong `@Transactional` được xem là `Active`, HikariCP không được phép can thiệp. |
| *"Cứ thấy session idle là terminate"* | **Sai lầm**. Trạng thái `idle` bình thường là kết nối sẵn sàng trong pool của ứng dụng. Chỉ được xử lý các session `idle in transaction`. |

---

## 11. Tài liệu tham khảo chính thức

* 🐘 [PostgreSQL: Runtime Configuration - Client Connection Defaults](https://www.postgresql.org/docs/current/runtime-config-client.html) — Chi tiết về `idle_in_transaction_session_timeout`.
* 🐘 [PostgreSQL: Monitoring Database Activity](https://www.postgresql.org/docs/current/monitoring-stats.html) — Hướng dẫn phân tích view `pg_stat_activity`.
* 🍃 [Spring Framework: Declarative Transaction Management](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative.html) — Cơ chế Proxy AOP và Transaction Boundaries.
* ⚡ [HikariCP: Configuration & Best Practices](https://github.com/brettwooldridge/HikariCP) — Hướng dẫn tối ưu Connection Pool và Leak Detection.
