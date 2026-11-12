# PostgreSQL Handbook (MkDocs Material)

Website tài liệu PostgreSQL **độc lập**, giao diện tối giản lấy cảm hứng từ Vue.js Guide; gồm menu bên trái, mục lục bên phải, tìm kiếm và light/dark mode.

## Chạy local (Môi trường Dev - có trang Quản trị)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Khởi động đồng thời Web tài liệu (Port 8000) & Web Admin (Port 8001)
python dev.py

# Hoặc chạy riêng MkDocs Dev
mkdocs serve -f mkdocs.dev.yml
```

Mở: http://127.0.0.1:8000/ (tab **Quản trị** chỉ hiển thị ở môi trường Dev/Local).

## Build & Deploy (Môi trường Prod - ẩn trang Quản trị)

Dự án tách riêng 2 cấu hình từ file gốc [`mkdocs.yml`](mkdocs.yml):
- **Dev (`mkdocs.dev.yml`):** Dùng cho máy local, hiển thị tab **Quản trị** (`docs/admin.md`).
- **Prod (`mkdocs.prod.yml`):** Dùng khi build/deploy lên GitHub Pages qua [`hooks/env_hook.py`](hooks/env_hook.py), tự động ẩn tab **Quản trị** và loại bỏ trang `/admin/` khỏi bản build tĩnh.

```bash
# Build bản Production (không bao gồm trang Admin)
mkdocs build -f mkdocs.prod.yml --strict
```

Output nằm trong thư mục `site/`; GitHub Actions ([`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)) tự động build theo `mkdocs.prod.yml` và deploy lên nhánh `gh-pages` mỗi khi push vào `main`.

## Quản lý bài viết (Thêm / Xóa / Web UI)

Dự án hỗ trợ 2 hình thức quản trị nội dung linh hoạt: qua **Giao diện Web (Web UI)** hoặc qua **Dòng lệnh (CLI)**.

### Cách 1: Quản trị trực tiếp trên Giao diện Web (Khuyên dùng)
Server quản trị [`admin_server.py`](admin_server.py) cho phép bạn quản lý bài viết trực quan trên trình duyệt:

1. **Khởi chạy Admin Server:**
   ```bash
   python admin_server.py
   ```
2. **Truy cập & Đăng nhập:**
   - **Cách A (Nhúng sẵn trong trang tài liệu):** Mở tab **[Quản trị](http://127.0.0.1:8000/admin/)** trên thanh menu của handbook.
   - **Cách B (Trang quản trị độc lập):** Mở trực tiếp tại **[http://127.0.0.1:8001/](http://127.0.0.1:8001/)**.
   - **Thông tin đăng nhập:**
     - **Tài khoản:** `vinh.nt`
     - **Mật khẩu:** `Setup12345a@`
3. **Các tính năng trên giao diện:**
   - 🔒 **Bảo mật xác thực:** Yêu cầu đăng nhập trước khi xem và thao tác trên danh sách bài viết. Có nút đăng xuất tiện lợi.
   - 📂 **Toggle đóng/mở chuyên mục:** Đầu mỗi mục lớn đều có nút đóng/mở (`▶` / `▼`). **Mặc định các mục lớn đều đóng gọn gàng**, kèm 2 nút "Mở tất cả" và "Đóng tất cả".
   - 🔍 **Tìm kiếm nhanh** bài viết theo tiêu đề hoặc đường dẫn file (tự động mở mục có kết quả phù hợp).
   - ➕ **Tạo bài viết mới:** Modal chọn chuyên mục, mục con, nhập tiêu đề (tự động sinh slug tên file chuẩn) và tự đồng bộ vào `mkdocs.yml`.
   - ✏️ **Chỉnh sửa bài viết toàn diện (Edit Article):**
     - Sửa **Tiêu đề** hiển thị trên menu và website.
     - Di chuyển bài viết sang **Chuyên mục chính / Mục con** khác (hệ thống tự động di chuyển file vật lý sang thư mục mới tương ứng và dọn thư mục cũ nếu rỗng).
     - Đổi tên file Markdown `.md`.
     - Soạn thảo nội dung Markdown trực tiếp với thanh công cụ định dạng nhanh (In đậm, Nghiêng, Tiêu đề, Code block, Bảng, Ghi chú Admonition).
     - Chuyển đổi giữa tab **Soạn thảo** và tab **Xem trước (Live Preview)** Markdown theo thời gian thực.
     - Hỗ trợ phím tắt `Ctrl + S` để lưu nhanh, phím `Tab` để thụt lề 2 dấu cách và bộ đếm số từ / ký tự.
   - 📁 **Quản lý chuyên mục linh hoạt:**
     - Nút **📁 Thêm chuyên mục:** Tạo ngay chuyên mục mới kèm file `index.md` mặc định và cập nhật `mkdocs.yml`.
     - Nút **✏️ Đổi tên:** Đổi tên chuyên mục chính hoặc mục con trực tiếp trên giao diện.
     - Nút **🗑️ Xóa:** Gỡ bỏ chuyên mục hoặc mục con khỏi menu điều hướng an toàn.
   - 🗑️ **Xóa bài viết:** Nút xóa với popup xác nhận an toàn, tự động xóa file trên đĩa và gỡ liên kết khỏi menu điều hướng.
   - 👁️ **Xem trước tức thì:** Bấm xem bài viết được live reload ngay trên website tài liệu.

### Cách 2: Sử dụng dòng lệnh (CLI)
Sử dụng công cụ [`new_article.py`](new_article.py):

```bash
# Giao diện tương tác từng bước (chọn Thêm / Sửa / Xóa / Mở Web UI)
python new_article.py

# Thêm bài viết nhanh bằng lệnh
python new_article.py -t "Quản lý Partitioning" -c "Guide" -s "Hiệu năng"

# Chỉnh sửa bài viết qua dòng lệnh (chọn bài từ danh sách, đổi tiêu đề / chuyên mục)
python new_article.py -e

# Xóa bài viết qua dòng lệnh
python new_article.py -d
# hoặc truyền đường dẫn file trực tiếp:
python new_article.py -d -p "guide/performance/partitioning.md"
```

## Tùy chỉnh

- Nội dung và menu: `mkdocs.yml` (`nav`) + `docs/**/*.md`.
- Màu sắc, layout: `docs/stylesheets/extra.css`.
- Thay `site_url` bằng URL production của bạn trước khi build/deploy.
- Search mặc định phân tích tiếng Anh; tiếng Việt vẫn được index theo từ khóa, nhưng khả năng tách từ tiếng Việt có thể hạn chế.

## Cách tổ chức nội dung

- `guide/`: kiến thức nền, SQL, query tuning.
- `operations/`: vận hành, bảo trì, backup, phân quyền.
- `best-practices/`: kinh nghiệm đã kiểm chứng và quy trình chuẩn.
- `troubleshooting/`: playbook các sự cố đã gặp.

Các đoạn SQL chỉ có tính minh họa. Thử trên môi trường test, xem execution plan và đánh giá tác động trước khi dùng trên production.

Tham khảo: https://www.postgresql.org/docs/current/ và https://squidfunk.github.io/mkdocs-material/

# Chạy ứng dụng bao gồm client 8000 và admin 8001

.venv\Scripts\python.exe dev.py