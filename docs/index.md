---
title: PostgreSQL Handbook
hide:
  - navigation
  - toc
---

<div class="spa-home" markdown>

<!-- HERO SECTION -->
<div class="spa-hero" markdown>

<div class="spa-hero__badge">
  <span class="spa-badge-dot"></span>
  <span>PostgreSQL 18 Ready &bull; Cẩm nang thực chiến nội bộ</span>
</div>

<h1 class="spa-hero__title">PostgreSQL Handbook</h1>

<p class="spa-hero__subtitle">
  Cẩm nang toàn diện về thiết kế cơ sở dữ liệu, tối ưu hóa truy vấn chuyên sâu và vận hành hạ tầng PostgreSQL độ sẵn sàng cao trong môi trường Production.
</p>

<div class="spa-hero__actions">
  <a href="guide/" class="spa-btn spa-btn--primary">
    <span>Bắt đầu khám phá</span>
    <span style="font-size: 1.1rem; line-height: 1;">→</span>
  </a>
  <a href="guide/performance/query-tuning/" class="spa-btn spa-btn--secondary">
    <span>⚡ Tối ưu hiệu năng</span>
  </a>
  <a href="operations/" class="spa-btn spa-btn--outline">
    <span>🛡️ Sổ tay vận hành</span>
  </a>
</div>

<!-- STATS BAR -->
<div class="spa-stats">
  <div class="spa-stat-item">
    <div class="spa-stat-value">4+</div>
    <div class="spa-stat-label">Chuyên đề trọng tâm</div>
  </div>
  <div class="spa-stat-divider"></div>
  <div class="spa-stat-item">
    <div class="spa-stat-value">100%</div>
    <div class="spa-stat-label">Thực tế sản xuất</div>
  </div>
  <div class="spa-stat-divider"></div>
  <div class="spa-stat-item">
    <div class="spa-stat-value">Deep</div>
    <div class="spa-stat-label">Bản chất & Execution Plan</div>
  </div>
  <div class="spa-stat-divider"></div>
  <div class="spa-stat-item">
    <div class="spa-stat-value">Ready</div>
    <div class="spa-stat-label">Scripts & Playbooks</div>
  </div>
</div>

</div>

<!-- SECTION 1: CORE MODULES -->
<div class="spa-section-header">
  <span class="spa-section-tag">CHUYÊN ĐỀ CỐT LÕI</span>
  <h2 class="spa-section-title">Khám Phá Các Phân Hệ Tài Liệu</h2>
  <p class="spa-section-desc">
    Tài liệu được phân loại theo từng giai đoạn vòng đời dự án: từ thiết kế mô hình dữ liệu, viết truy vấn, đến giám sát và khắc phục sự cố tải cao.
  </p>
</div>

<div class="spa-grid">

  <!-- Card 1 -->
  <a href="guide/" class="spa-card">
    <div>
      <div class="spa-card__top">
        <div class="spa-card__icon">📘</div>
        <span class="spa-card__badge">Nền tảng</span>
      </div>
      <h3 class="spa-card__title">Guide & SQL Engine</h3>
      <p class="spa-card__desc">
        Thiết lập môi trường chuẩn với Docker và psql, hiểu rõ kiến trúc lưu trữ, Transaction Isolation Levels, ACID và cơ chế MVCC.
      </p>
      <div class="spa-card__tags">
        <span class="spa-tag">psql</span>
        <span class="spa-tag">Docker</span>
        <span class="spa-tag">MVCC</span>
        <span class="spa-tag">Transactions</span>
      </div>
    </div>
    <div class="spa-card__footer">
      <span>Đọc hướng dẫn kiến trúc</span>
      <span>→</span>
    </div>
  </a>

  <!-- Card 2 -->
  <a href="guide/performance/query-tuning/" class="spa-card">
    <div>
      <div class="spa-card__top">
        <div class="spa-card__icon">⚡</div>
        <span class="spa-card__badge">Hiệu năng</span>
      </div>
      <h3 class="spa-card__title">Tối Ưu Truy Vấn & Indexing</h3>
      <p class="spa-card__desc">
        Đọc hiểu từng node trong EXPLAIN ANALYZE (Buffers, Loops), xây dựng chiến lược đánh Index B-Tree, GIN, Partial và quy trình tinh chỉnh query.
      </p>
      <div class="spa-card__tags">
        <span class="spa-tag">EXPLAIN ANALYZE</span>
        <span class="spa-tag">B-Tree</span>
        <span class="spa-tag">GIN</span>
        <span class="spa-tag">Index Tuning</span>
      </div>
    </div>
    <div class="spa-card__footer">
      <span>Xem quy trình tối ưu</span>
      <span>→</span>
    </div>
  </a>

  <!-- Card 3 -->
  <a href="operations/" class="spa-card">
    <div>
      <div class="spa-card__top">
        <div class="spa-card__icon">🛡️</div>
        <span class="spa-card__badge">Vận hành</span>
      </div>
      <h3 class="spa-card__title">Vận Hành & Bảo Mật</h3>
      <p class="spa-card__desc">
        Chủ động quản lý bloat và dọn rác với VACUUM/Autovacuum, sao lưu khôi phục thảm họa (Backup/PITR), và quản trị Roles & RBAC an toàn.
      </p>
      <div class="spa-card__tags">
        <span class="spa-tag">Autovacuum</span>
        <span class="spa-tag">pg_stat</span>
        <span class="spa-tag">Backup PITR</span>
        <span class="spa-tag">Security</span>
      </div>
    </div>
    <div class="spa-card__footer">
      <span>Mở sổ tay vận hành</span>
      <span>→</span>
    </div>
  </a>

  <!-- Card 4 -->
  <a href="troubleshooting/" class="spa-card">
    <div>
      <div class="spa-card__top">
        <div class="spa-card__icon">🔍</div>
        <span class="spa-card__badge">Sự cố</span>
      </div>
      <h3 class="spa-card__title">Troubleshooting & Best Practices</h3>
      <p class="spa-card__desc">
        Playbooks chẩn đoán lỗi kiệt Connection Pool, phân tích Blocking & Deadlocks, cùng kỹ thuật phân trang (Pagination) hàng chục triệu dòng.
      </p>
      <div class="spa-card__tags">
        <span class="spa-tag">Lock Contention</span>
        <span class="spa-tag">Deadlocks</span>
        <span class="spa-tag">Pagination</span>
        <span class="spa-tag">Pool Exhaustion</span>
      </div>
    </div>
    <div class="spa-card__footer">
      <span>Tra cứu playbook sự cố</span>
      <span>→</span>
    </div>
  </a>

</div>

<!-- SECTION 2: LIVE CODE & SPOTLIGHT -->
<div class="spa-section-header">
  <span class="spa-section-tag">LIVE SHOWCASE</span>
  <h2 class="spa-section-title">Chẩn Đoán Thực Chiến & Mã Mẫu</h2>
  <p class="spa-section-desc">
    Các đoạn truy vấn chẩn đoán và lệnh quản trị sẵn sàng sử dụng ngay trên hệ thống của bạn.
  </p>
</div>

<div class="spa-terminal-box" markdown>

=== "1. Chẩn đoán EXPLAIN (ANALYZE, BUFFERS)"

    ```sql
    -- Đánh giá chi phí I/O và thời gian thực thi thực tế
    EXPLAIN (ANALYZE, BUFFERS, VERBOSE, TIMING)
    SELECT 
        o.id AS order_id,
        o.created_at,
        c.name AS customer_name,
        o.total_amount
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    WHERE o.status = 'COMPLETED'
      AND o.created_at >= NOW() - INTERVAL '30 days'
    ORDER BY o.created_at DESC
    LIMIT 20;

    -- Lưu ý: Quan sát 'Buffers: shared hit=... read=...' để phát hiện đọc đĩa vật lý
    ```

=== "2. Phát hiện truy vấn gây kẹt Lock (Blocking)"

    ```sql
    -- Tìm phiên làm việc (PID) đang chặn các giao dịch khác
    SELECT
        blocked_locks.pid     AS blocked_pid,
        blocked_activity.usename  AS blocked_user,
        blocking_locks.pid    AS blocking_pid,
        blocking_activity.usename AS blocking_user,
        blocked_activity.query    AS blocked_statement,
        blocking_activity.query   AS blocking_statement
    FROM  pg_catalog.pg_locks         blocked_locks
    JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
    JOIN pg_catalog.pg_locks         blocking_locks 
        ON blocking_locks.locktype = blocked_locks.locktype
        AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
        AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
        AND blocking_locks.pid != blocked_locks.pid
    JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
    WHERE NOT blocked_locks.granted;
    ```

=== "3. Kiểm tra độ trễ Autovacuum & Bloat"

    ```sql
    -- Top các bảng có nhiều dead tuples chưa được dọn dẹp
    SELECT
        schemaname,
        relname AS table_name,
        n_live_tup AS live_rows,
        n_dead_tup AS dead_rows,
        ROUND(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio_pct,
        last_vacuum,
        last_autovacuum
    FROM pg_stat_user_tables
    WHERE n_dead_tup > 1000
    ORDER BY n_dead_tup DESC
    LIMIT 10;
    ```

</div>

<!-- SECTION 3: CORE PRINCIPLES -->
<div class="spa-section-header">
  <span class="spa-section-tag">NGUYÊN TẮC THIẾT KẾ</span>
  <h2 class="spa-section-title">Tại Sao Cẩm Nang Này Khác Biệt?</h2>
  <p class="spa-section-desc">
    Được biên soạn với góc nhìn kỹ thuật từ các hệ thống chịu tải cao, hướng tới tính ứng dụng tức thì.
  </p>
</div>

<div class="spa-principles-grid">
  <div class="spa-principle">
    <div class="spa-principle__icon">🎯</div>
    <h3 class="spa-principle__title">Tập Trung Vào Bản Chất</h3>
    <p class="spa-principle__desc">
      Không chỉ đưa ra cú pháp lệnh; chúng tôi giải thích cơ chế bên dưới như Shared Buffers, WAL, Heap Tuples và Locking Engine.
    </p>
  </div>
  <div class="spa-principle">
    <div class="spa-principle__icon">🧪</div>
    <h3 class="spa-principle__title">Đo Đạc & Kiểm Chứng</h3>
    <p class="spa-principle__desc">
      Mọi khuyến nghị tối ưu đều đi kèm lệnh đo lường execution plan và chỉ số cache hit ratio trước và sau khi áp dụng.
    </p>
  </div>
  <div class="spa-principle">
    <div class="spa-principle__icon">🛡️</div>
    <h3 class="spa-principle__title">Nguyên Tắc An Toàn Production</h3>
    <p class="spa-principle__desc">
      Cảnh báo rủi ro khóa bảng (AccessExclusiveLock), thời gian chờ lock_timeout và kịch bản rollback trong từng thao tác DDL.
    </p>
  </div>
</div>

<!-- SECTION 4: CALL TO ACTION BANNER -->
<div class="spa-cta-banner">
  <h2>Sẵn Sàng Làm Chủ PostgreSQL?</h2>
  <p>
    Bắt đầu với các bài hướng dẫn từ cơ bản đến nâng cao hoặc tham khảo tài liệu kỹ thuật chính thức.
  </p>
  <div class="spa-hero__actions" style="margin-bottom: 0;">
    <a href="guide/" class="spa-btn spa-btn--primary">
      <span>Đọc Guide ngay</span>
      <span>→</span>
    </a>
    <a href="https://www.postgresql.org/docs/18/" target="_blank" rel="noopener" class="spa-btn spa-btn--secondary">
      <span>Official PostgreSQL 18 Docs ↗</span>
    </a>
  </div>
</div>

!!! info "Ghi chú phiên bản tham chiếu"
    Toàn bộ mã SQL và cấu hình trong handbook này được kiểm thử trên **PostgreSQL 18** và tương thích với PostgreSQL 14–17. Trước khi áp dụng thay đổi cấu hình trên môi trường sản xuất, hãy luôn kiểm tra lại trong môi trường Staging/Test.

</div>
