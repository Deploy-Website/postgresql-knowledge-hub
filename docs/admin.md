---
title: Quản Trị Bài Viết
hide:
  - navigation
  - toc
---

<div class="admin-wrapper" style="max-width: 1240px; margin: 0 auto; padding: 0.5rem 0 2rem;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem;">
    <div>
      <h1 style="font-size: 1.6rem; font-weight: 800; margin: 0; letter-spacing: -0.02em;">Quản Trị Nội Dung Handbook</h1>
      <p style="font-size: 0.85rem; color: var(--md-default-fg-color--light); margin: 0.2rem 0 0;">Thêm, chỉnh sửa bài viết (Markdown & Live Preview), quản lý chuyên mục và đồng bộ menu điều hướng tự động.</p>
    </div>
    <div style="display: flex; gap: 0.5rem;">
      <a href="http://127.0.0.1:8001/" target="_blank" class="md-button md-button--primary" style="font-size: 0.82rem; border-radius: 8px;">
        Mở trang quản trị riêng (Port 8001) ↗
      </a>
    </div>
  </div>

  <iframe src="http://127.0.0.1:8001/" style="width: 100%; height: 860px; border: 1px solid var(--site-divider); border-radius: 14px; background: #0f172a; box-shadow: 0 4px 20px rgba(0,0,0,0.15);"></iframe>

  <div style="margin-top: 1.5rem; padding: 1.25rem; background: var(--md-code-bg-color); border-radius: 12px; border: 1px solid var(--site-divider); font-size: 0.82rem;">
    <b>💡 Mẹo:</b> Giao diện quản trị trên kết nối trực tiếp với backend qua cổng <code>8001</code>. Bạn có thể:
    <ul style="margin: 0.5rem 0 0.5rem 1.25rem; line-height: 1.6;">
      <li><b>Sửa bài viết:</b> Bấm <b>✏️ Sửa bài</b> để sửa tiêu đề, đổi chuyên mục (tự động chuyển file), đổi tên file và soạn thảo Markdown trực tiếp có tab <b>Xem trước</b> và phím tắt <code>Ctrl + S</code>.</li>
      <li><b>Quản lý chuyên mục:</b> Bấm <b>📁 Thêm chuyên mục</b> ở thanh công cụ trên cùng, hoặc bấm <b>✏️ Đổi tên</b> / <b>🗑️ Xóa</b> tại tiêu đề mỗi chuyên mục.</li>
      <li><b>Dòng lệnh (CLI):</b> Sử dụng <code>python new_article.py -e</code> để sửa bài hoặc <code>python new_article.py</code> để vào menu tương tác.</li>
    </ul>
  </div>
</div>
