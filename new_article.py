#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL Handbook - Tool quản lý bài viết tự động (Thêm / Xóa / Web UI).
Hỗ trợ chọn chuyên mục, tạo/xóa file markdown và cập nhật menu điều hướng (nav) trong mkdocs.yml.
"""

import os
import sys
import re
import argparse
import subprocess
import unicodedata
from pathlib import Path

# Thử import PyYAML, nếu chưa có thì cảnh báo
try:
    import yaml
except ImportError:
    print("Lỗi: Cần cài đặt PyYAML. Hãy chạy: pip install pyyaml")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent
MKDOCS_FILE = PROJECT_ROOT / "mkdocs.yml"
DOCS_DIR = PROJECT_ROOT / "docs"


def slugify(text: str) -> str:
    """Chuyển đổi tiêu đề tiếng Việt thành slug tên file không dấu."""
    t = text.replace('đ', 'd').replace('Đ', 'd')
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode('utf-8')
    t = re.sub(r'[^\w\s-]', '', t).strip().lower()
    slug = re.sub(r'[-\s]+', '-', t)
    return slug if slug else "new-article"


def load_mkdocs_config():
    """Đọc file mkdocs.yml và phân tách phần header và phần nav."""
    if not MKDOCS_FILE.exists():
        print(f"Lỗi: Không tìm thấy file cấu hình tại {MKDOCS_FILE}")
        sys.exit(1)

    content = MKDOCS_FILE.read_text(encoding="utf-8")
    
    lines = content.splitlines(keepends=True)
    nav_line_idx = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith("nav:"):
            nav_line_idx = idx
            break

    if nav_line_idx == -1:
        print("Lỗi: Không tìm thấy mục 'nav:' trong file mkdocs.yml")
        sys.exit(1)

    header_text = "".join(lines[:nav_line_idx])
    data = yaml.safe_load(content)
    nav_data = data.get("nav", [])
    
    return header_text, nav_data


def quote_yaml_key(key: str) -> str:
    """Bọc nháy kép nếu key chứa ký tự đặc biệt trong YAML."""
    special_chars = [':', '#', '"', "'", '@', '&', '%', '*', '?', '|', '>', '{', '}', '[', ']']
    if any(c in key for c in special_chars) or key.strip().startswith(('-', '`')):
        escaped = key.replace('"', '\\"')
        return f'"{escaped}"'
    return key


def serialize_nav_item(item, indent=2) -> list:
    """Format cấu trúc nav thành các dòng YAML chuẩn thụt lề 2/6/10 spaces."""
    lines = []
    prefix = " " * indent
    if isinstance(item, dict):
        for k, v in item.items():
            safe_k = quote_yaml_key(str(k))
            if isinstance(v, list):
                lines.append(f"{prefix}- {safe_k}:")
                for sub in v:
                    lines.extend(serialize_nav_item(sub, indent + 4))
            else:
                lines.append(f"{prefix}- {safe_k}: {v}")
    elif isinstance(item, list):
        for sub in item:
            lines.extend(serialize_nav_item(sub, indent))
    return lines


def format_full_nav(nav_data) -> str:
    """Tạo lại chuỗi YAML hoàn chỉnh cho phần nav."""
    lines = ["nav:\n"]
    for item in nav_data:
        sub_lines = serialize_nav_item(item, indent=2)
        for sl in sub_lines:
            lines.append(sl + "\n")
    return "".join(lines)


def get_nav_categories(nav_data):
    """Phân tích cấu trúc nav để lấy danh sách chuyên mục chính và chuyên mục con."""
    categories = {}
    
    for entry in nav_data:
        if not isinstance(entry, dict):
            continue
        for cat_name, val in entry.items():
            if cat_name.lower() in ["home", "quản trị", "admin"]:
                continue  # Bỏ qua các trang hệ thống đặc biệt
            
            cat_info = {
                "subcategories": {},
                "direct_items": [],
                "dir_hint": ""
            }
            
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        for sub_k, sub_v in item.items():
                            if isinstance(sub_v, list):
                                sub_dir = ""
                                for sub_item in sub_v:
                                    if isinstance(sub_item, dict):
                                        for _, path_str in sub_item.items():
                                            if isinstance(path_str, str):
                                                sub_dir = str(Path(path_str).parent).replace("\\", "/")
                                                break
                                    if sub_dir:
                                        break
                                cat_info["subcategories"][sub_k] = {
                                    "items": sub_v,
                                    "dir_hint": sub_dir
                                }
                            else:
                                cat_info["direct_items"].append({sub_k: sub_v})
                                if not cat_info["dir_hint"] and isinstance(sub_v, str):
                                    cat_info["dir_hint"] = str(Path(sub_v).parent).replace("\\", "/")
            elif isinstance(val, str):
                cat_info["direct_items"].append({cat_name: val})
                cat_info["dir_hint"] = str(Path(val).parent).replace("\\", "/")

            if not cat_info["dir_hint"]:
                cat_info["dir_hint"] = slugify(cat_name)

            categories[cat_name] = cat_info

    return categories


def get_all_articles_flat(nav_data):
    """Lấy danh sách phẳng tất cả bài viết phục vụ xóa hoặc hiển thị."""
    articles = []

    def walk_tree(tree, path_names):
        if isinstance(tree, list):
            for item in tree:
                walk_tree(item, path_names)
        elif isinstance(item := tree, dict):
            for k, v in item.items():
                if k.lower() in ["home", "quản trị", "admin"]:
                    continue
                if isinstance(v, list):
                    walk_tree(v, path_names + [k])
                elif isinstance(v, str):
                    full_p = DOCS_DIR / v
                    articles.append({
                        "title": k,
                        "path": v.replace("\\", "/"),
                        "category_path": " > ".join(path_names),
                        "main_category": path_names[0] if path_names else "",
                        "subcategory": path_names[1] if len(path_names) > 1 else "",
                        "exists": full_p.exists(),
                        "size": full_p.stat().st_size if full_p.exists() else 0
                    })

    for entry in nav_data:
        walk_tree(entry, [])

    return articles


def prompt_user_choice(options: list, prompt_text: str = "Chọn") -> int:
    """Hàm phụ trợ nhập lựa chọn từ danh sách."""
    while True:
        try:
            val = input(f"{prompt_text} [1-{len(options)}]: ").strip()
            idx = int(val) - 1
            if 0 <= idx < len(options):
                return idx
            print(f"⚠️ Vui lòng nhập số từ 1 đến {len(options)}.")
        except ValueError:
            print("⚠️ Giá trị nhập không hợp lệ. Vui lòng nhập số.")


def create_article(title: str, main_cat: str, sub_cat: str, rel_path: str, full_path: Path):
    """Thực hiện tạo file md và cập nhật mkdocs.yml."""
    full_path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""---
title: {title}
---

# {title}

<!-- Viết nội dung bài viết tại đây -->

"""
    full_path.write_text(content, encoding="utf-8")
    print(f"✅ Đã tạo file: docs/{rel_path}")

    header_text, nav_data = load_mkdocs_config()

    inserted = False
    for entry in nav_data:
        if isinstance(entry, dict) and main_cat in entry:
            cat_content = entry[main_cat]
            if sub_cat:
                if isinstance(cat_content, list):
                    for sub_item in cat_content:
                        if isinstance(sub_item, dict) and sub_cat in sub_item:
                            sub_list = sub_item[sub_cat]
                            if isinstance(sub_list, list):
                                sub_list.append({title: rel_path})
                                inserted = True
                                break
                    if not inserted:
                        cat_content.append({sub_cat: [{title: rel_path}]})
                        inserted = True
            else:
                if isinstance(cat_content, list):
                    cat_content.append({title: rel_path})
                    inserted = True
                elif isinstance(cat_content, str):
                    entry[main_cat] = [{main_cat: cat_content}, {title: rel_path}]
                    inserted = True
            break

    if not inserted:
        if sub_cat:
            nav_data.append({main_cat: [{sub_cat: [{title: rel_path}]}]})
        else:
            nav_data.append({main_cat: [{title: rel_path}]})

    backup_file = MKDOCS_FILE.with_suffix(".yml.bak")
    backup_file.write_text(MKDOCS_FILE.read_text(encoding="utf-8"), encoding="utf-8")

    new_nav_text = format_full_nav(nav_data)
    final_content = header_text + new_nav_text
    MKDOCS_FILE.write_text(final_content, encoding="utf-8")
    print(f"✅ Đã cập nhật menu điều hướng trong mkdocs.yml")
    print(f"🎉 Hoàn tất! Trang sẽ tự động reload ngay lập tức trên http://127.0.0.1:8000/.")


def delete_article(rel_path: str) -> tuple:
    """
    Xóa file markdown và gỡ bỏ khỏi nav trong mkdocs.yml.
    Trả về (thành_công, thông_báo).
    """
    rel_path = rel_path.replace("\\", "/").lstrip("/")
    full_path = DOCS_DIR / rel_path

    header_text, nav_data = load_mkdocs_config()
    
    def remove_from_nav_tree(tree):
        removed_any = False
        for item in list(tree):
            if isinstance(item, dict):
                for k, v in list(item.items()):
                    if isinstance(v, str):
                        if v.replace("\\", "/").lstrip("/") == rel_path:
                            tree.remove(item)
                            return True
                    elif isinstance(v, list):
                        if remove_from_nav_tree(v):
                            removed_any = True
                            if len(v) == 0:
                                tree.remove(item)
                            return True
        return removed_any

    removed_from_nav = remove_from_nav_tree(nav_data)

    file_deleted = False
    if full_path.exists():
        try:
            full_path.unlink()
            file_deleted = True
            parent = full_path.parent
            if parent != DOCS_DIR and not any(parent.iterdir()):
                try:
                    parent.rmdir()
                except OSError:
                    pass
        except Exception as e:
            return False, f"Lỗi khi xóa file {full_path}: {e}"

    if not removed_from_nav and not file_deleted:
        return False, f"Không tìm thấy bài viết '{rel_path}' trong menu hoặc ổ đĩa."

    if removed_from_nav:
        backup_file = MKDOCS_FILE.with_suffix(".yml.bak")
        backup_file.write_text(MKDOCS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        new_nav_text = format_full_nav(nav_data)
        final_content = header_text + new_nav_text
        MKDOCS_FILE.write_text(final_content, encoding="utf-8")

    return True, f"Đã xóa thành công bài viết '{rel_path}' khỏi menu và đĩa."


def update_article(
    old_rel_path: str,
    new_title: str,
    new_main_cat: str,
    new_sub_cat: str = None,
    new_rel_path: str = None,
    new_content: str = None
) -> tuple:
    """
    Cập nhật thông tin bài viết (tiêu đề, chuyên mục, vị trí, tên file, nội dung).
    Trả về (thành_công, thông_báo).
    """
    old_rel_path = old_rel_path.replace("\\", "/").lstrip("/")
    new_title = new_title.strip() if new_title else ""
    new_main_cat = new_main_cat.strip() if new_main_cat else ""
    if new_sub_cat:
        new_sub_cat = new_sub_cat.strip()
        if not new_sub_cat or new_sub_cat == "__none__":
            new_sub_cat = None

    if not new_rel_path:
        new_rel_path = old_rel_path
    new_rel_path = new_rel_path.replace("\\", "/").lstrip("/")

    old_full_path = DOCS_DIR / old_rel_path
    new_full_path = DOCS_DIR / new_rel_path

    if not new_title:
        return False, "Tiêu đề bài viết không được để trống."
    if not new_main_cat:
        return False, "Chuyên mục chính không được để trống."
    if not new_rel_path:
        return False, "Đường dẫn file không được để trống."

    header_text, nav_data = load_mkdocs_config()

    # 1. Tìm vị trí hiện tại trong nav_data
    found_info = None  # (parent_list, index, old_title, old_main, old_sub)
    for main_entry in nav_data:
        if not isinstance(main_entry, dict):
            continue
        for m_cat, m_val in main_entry.items():
            if m_cat.lower() in ["home", "quản trị", "admin"]:
                continue
            if isinstance(m_val, list):
                for idx, item in enumerate(m_val):
                    if isinstance(item, dict):
                        for sub_k, sub_v in item.items():
                            if isinstance(sub_v, str):
                                if sub_v.replace("\\", "/").lstrip("/") == old_rel_path:
                                    found_info = (m_val, idx, sub_k, m_cat, None)
                                    break
                            elif isinstance(sub_v, list):
                                for sub_idx, sub_item in enumerate(sub_v):
                                    if isinstance(sub_item, dict):
                                        for art_k, art_v in sub_item.items():
                                            if isinstance(art_v, str) and art_v.replace("\\", "/").lstrip("/") == old_rel_path:
                                                found_info = (sub_v, sub_idx, art_k, m_cat, sub_k)
                                                break
                                    if found_info:
                                        break
                    if found_info:
                        break
            elif isinstance(m_val, str):
                if m_val.replace("\\", "/").lstrip("/") == old_rel_path:
                    found_info = ("direct_root", main_entry, m_cat, m_cat, None)
                    break
        if found_info:
            break

    if not found_info:
        return False, f"Không tìm thấy bài viết '{old_rel_path}' trong menu điều hướng."

    parent_list, idx, old_title, old_main, old_sub = found_info
    same_category = (old_main == new_main_cat and (old_sub or None) == (new_sub_cat or None))

    if same_category:
        if parent_list == "direct_root":
            parent_list[new_title] = new_rel_path
        else:
            parent_list[idx] = {new_title: new_rel_path}
    else:
        if parent_list != "direct_root":
            parent_list.pop(idx)
            # Dọn dẹp mục con rỗng nếu cần
            if len(parent_list) == 0 and old_sub:
                for main_entry in nav_data:
                    if isinstance(main_entry, dict) and old_main in main_entry:
                        cat_content = main_entry[old_main]
                        if isinstance(cat_content, list):
                            for sub_item in list(cat_content):
                                if isinstance(sub_item, dict) and old_sub in sub_item and len(sub_item[old_sub]) == 0:
                                    cat_content.remove(sub_item)
                                    break

        # Chèn vào chuyên mục mới
        inserted = False
        for entry in nav_data:
            if isinstance(entry, dict) and new_main_cat in entry:
                cat_content = entry[new_main_cat]
                if new_sub_cat:
                    if isinstance(cat_content, list):
                        for sub_item in cat_content:
                            if isinstance(sub_item, dict) and new_sub_cat in sub_item:
                                sub_list = sub_item[new_sub_cat]
                                if isinstance(sub_list, list):
                                    sub_list.append({new_title: new_rel_path})
                                    inserted = True
                                    break
                        if not inserted:
                            cat_content.append({new_sub_cat: [{new_title: new_rel_path}]})
                            inserted = True
                else:
                    if isinstance(cat_content, list):
                        cat_content.append({new_title: new_rel_path})
                        inserted = True
                    elif isinstance(cat_content, str):
                        entry[new_main_cat] = [{new_main_cat: cat_content}, {new_title: new_rel_path}]
                        inserted = True
                break

        if not inserted:
            if new_sub_cat:
                nav_data.append({new_main_cat: [{new_sub_cat: [{new_title: new_rel_path}]}]})
            else:
                nav_data.append({new_main_cat: [{new_title: new_rel_path}]})

    # Cập nhật file trên đĩa
    try:
        new_full_path.parent.mkdir(parents=True, exist_ok=True)
        if new_content is not None:
            new_full_path.write_text(new_content, encoding="utf-8")
            if old_full_path != new_full_path and old_full_path.exists():
                old_full_path.unlink()
                old_parent = old_full_path.parent
                if old_parent != DOCS_DIR and not any(old_parent.iterdir()):
                    try:
                        old_parent.rmdir()
                    except OSError:
                        pass
        else:
            if old_full_path != new_full_path:
                if old_full_path.exists():
                    old_full_path.rename(new_full_path)
                    old_parent = old_full_path.parent
                    if old_parent != DOCS_DIR and not any(old_parent.iterdir()):
                        try:
                            old_parent.rmdir()
                        except OSError:
                            pass
                else:
                    new_full_path.write_text(f"# {new_title}\n\n", encoding="utf-8")
    except Exception as e:
        return False, f"Lỗi khi lưu file trên đĩa: {e}"

    # Lưu lại mkdocs.yml
    backup_file = MKDOCS_FILE.with_suffix(".yml.bak")
    backup_file.write_text(MKDOCS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    new_nav_text = format_full_nav(nav_data)
    final_content = header_text + new_nav_text
    MKDOCS_FILE.write_text(final_content, encoding="utf-8")

    return True, f"Đã cập nhật bài viết '{new_title}' thành công!"


def rename_category(old_name: str, new_name: str, main_cat: str = None) -> tuple:
    """
    Đổi tên chuyên mục chính hoặc mục con trong mkdocs.yml.
    Trả về (thành_công, thông_báo).
    """
    old_name = old_name.strip() if old_name else ""
    new_name = new_name.strip() if new_name else ""
    if not old_name or not new_name:
        return False, "Tên chuyên mục không được để trống."
    if old_name == new_name:
        return True, "Tên chuyên mục không thay đổi."

    header_text, nav_data = load_mkdocs_config()
    renamed = False

    if main_cat is None:
        # Đổi tên chuyên mục chính (cấp 1)
        for entry in nav_data:
            if isinstance(entry, dict) and old_name in entry:
                new_entry = {}
                for k, v in entry.items():
                    if k == old_name:
                        new_entry[new_name] = v
                    else:
                        new_entry[k] = v
                entry.clear()
                entry.update(new_entry)
                renamed = True
                break
    else:
        # Đổi tên mục con (cấp 2 thuộc main_cat)
        main_cat = main_cat.strip()
        for entry in nav_data:
            if isinstance(entry, dict) and main_cat in entry:
                cat_content = entry[main_cat]
                if isinstance(cat_content, list):
                    for sub_item in cat_content:
                        if isinstance(sub_item, dict) and old_name in sub_item:
                            new_sub = {}
                            for k, v in sub_item.items():
                                if k == old_name:
                                    new_sub[new_name] = v
                                else:
                                    new_sub[k] = v
                            sub_item.clear()
                            sub_item.update(new_sub)
                            renamed = True
                            break
                break

    if not renamed:
        return False, f"Không tìm thấy chuyên mục '{old_name}' để đổi tên."

    backup_file = MKDOCS_FILE.with_suffix(".yml.bak")
    backup_file.write_text(MKDOCS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    new_nav_text = format_full_nav(nav_data)
    final_content = header_text + new_nav_text
    MKDOCS_FILE.write_text(final_content, encoding="utf-8")

    return True, f"Đã đổi tên chuyên mục '{old_name}' thành '{new_name}' thành công!"


def delete_category(cat_name: str, parent_cat: str = None) -> tuple:
    """
    Xóa một chuyên mục chính hoặc mục con khỏi menu nav trong mkdocs.yml.
    (Không xóa các file vật lý trên đĩa để bảo đảm an toàn dữ liệu).
    Trả về (thành_công, thông_báo).
    """
    cat_name = cat_name.strip() if cat_name else ""
    if not cat_name:
        return False, "Tên chuyên mục không được để trống."

    header_text, nav_data = load_mkdocs_config()
    deleted = False

    if parent_cat is None:
        # Xóa chuyên mục chính (cấp 1)
        for item in list(nav_data):
            if isinstance(item, dict) and cat_name in item:
                nav_data.remove(item)
                deleted = True
                break
    else:
        # Xóa mục con thuộc parent_cat
        parent_cat = parent_cat.strip()
        for item in list(nav_data):
            if isinstance(item, dict) and parent_cat in item:
                cat_content = item[parent_cat]
                if isinstance(cat_content, list):
                    for sub in list(cat_content):
                        if isinstance(sub, dict) and cat_name in sub:
                            cat_content.remove(sub)
                            deleted = True
                            break
                    # Nếu chuyên mục cha không còn mục con nào, gỡ khỏi nav để tránh lỗi YAML rỗng
                    if len(cat_content) == 0:
                        nav_data.remove(item)
                break

    if not deleted:
        return False, f"Không tìm thấy chuyên mục '{cat_name}' trong menu điều hướng."

    backup_file = MKDOCS_FILE.with_suffix(".yml.bak")
    backup_file.write_text(MKDOCS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    new_nav_text = format_full_nav(nav_data)
    final_content = header_text + new_nav_text
    MKDOCS_FILE.write_text(final_content, encoding="utf-8")

    return True, f"Đã xóa chuyên mục '{cat_name}' khỏi menu điều hướng thành công!"


def interactive_wizard():
    """Giao diện dòng lệnh tương tác từng bước thân thiện."""
    print("=" * 60)
    print("     POSTGRESQL HANDBOOK - QUẢN LÝ BÀI VIẾT (CLI)     ")
    print("=" * 60)
    print("  [1] ➕ Thêm bài viết mới")
    print("  [2] ✏️  Chỉnh sửa bài viết")
    print("  [3] 🗑️  Xóa bài viết")
    print("  [4] 🌐 Mở giao diện Web Admin (Giao diện đồ họa)")
    print("=" * 60)

    choice = prompt_user_choice(["add", "edit", "delete", "ui"], "Lựa chọn hành động")

    if choice == 0:
        interactive_add()
    elif choice == 1:
        interactive_edit()
    elif choice == 2:
        interactive_delete()
    elif choice == 3:
        launch_web_ui()


def interactive_add():
    """Giao diện thêm bài viết."""
    header_text, nav_data = load_mkdocs_config()
    cat_structure = get_nav_categories(nav_data)
    main_cats = list(cat_structure.keys())

    print("\n📂 BƯỚC 1: CHỌN CHUYÊN MỤC CHÍNH")
    for i, cname in enumerate(main_cats, 1):
        sub_count = len(cat_structure[cname]["subcategories"])
        item_count = len(cat_structure[cname]["direct_items"])
        info = f"({sub_count} mục con, {item_count} bài viết)" if sub_count > 0 else f"({item_count} bài viết)"
        print(f"  [{i}] {cname} {info}")
    print(f"  [{len(main_cats) + 1}] ➕ Thêm chuyên mục mới...")

    chosen_idx = prompt_user_choice(main_cats + ["new"], "Chọn chuyên mục")
    
    is_new_main_cat = (chosen_idx == len(main_cats))
    if is_new_main_cat:
        while True:
            target_main_cat = input("\n👉 Nhập tên chuyên mục mới (VD: Architecture): ").strip()
            if target_main_cat:
                break
            print("Tên chuyên mục không được để trống.")
        target_sub_cat = None
        target_dir = slugify(target_main_cat)
    else:
        target_main_cat = main_cats[chosen_idx]
        cat_info = cat_structure[target_main_cat]
        subs = list(cat_info["subcategories"].keys())

        print(f"\n📁 BƯỚC 2: CHỌN MỤC CON TRONG '{target_main_cat}'")
        options = [f"Thêm trực tiếp vào '{target_main_cat}' (không dùng mục con)"]
        for s in subs:
            count = len(cat_info["subcategories"][s]["items"])
            options.append(f"{s} ({count} bài viết)")
        options.append("➕ Thêm mục con mới...")

        for i, opt in enumerate(options, 1):
            print(f"  [{i}] {opt}")

        sub_choice_idx = prompt_user_choice(options, "Chọn vị trí")
        
        if sub_choice_idx == 0:
            target_sub_cat = None
            target_dir = cat_info["dir_hint"] or slugify(target_main_cat)
        elif sub_choice_idx == len(options) - 1:
            while True:
                target_sub_cat = input(f"\n👉 Nhập tên mục con mới trong '{target_main_cat}': ").strip()
                if target_sub_cat:
                    break
                print("Tên mục con không được để trống.")
            base_dir = cat_info["dir_hint"] or slugify(target_main_cat)
            target_dir = f"{base_dir}/{slugify(target_sub_cat)}"
        else:
            target_sub_cat = subs[sub_choice_idx - 1]
            sub_info = cat_info["subcategories"][target_sub_cat]
            target_dir = sub_info["dir_hint"] or f"{cat_info['dir_hint']}/{slugify(target_sub_cat)}"

    print("\n📝 BƯỚC 3: NHẬP TIÊU ĐỀ BÀI VIẾT")
    while True:
        title = input("👉 Tiêu đề bài viết: ").strip()
        if title:
            break
        print("Tiêu đề không được để trống.")

    default_filename = f"{slugify(title)}.md"
    print(f"\n📄 BƯỚC 4: TÊN FILE MARKDOWN")
    custom_filename = input(f"👉 Tên file [.md] (Mặc định: {default_filename}): ").strip()
    filename = custom_filename if custom_filename else default_filename
    if not filename.endswith(".md"):
        filename += ".md"

    rel_md_path = f"{target_dir}/{filename}".replace("\\", "/")
    full_md_path = DOCS_DIR / rel_md_path

    menu_location = f"{target_main_cat} > {target_sub_cat} > {title}" if target_sub_cat else f"{target_main_cat} > {title}"
    print("\n" + "=" * 60)
    print("                  XÁC NHẬN TẠO BÀI VIẾT                   ")
    print("=" * 60)
    print(f" 📄 Tiêu đề:        {title}")
    print(f" 📂 Thư mục:        docs/{target_dir}")
    print(f" 📝 File tạo:       docs/{rel_md_path}")
    print(f" 📑 Vị trí menu:    {menu_location}")
    print("=" * 60)

    if full_md_path.exists():
        print(f"⚠️ CẢNH BÁO: File {full_md_path} đã tồn tại!")
        overwrite = input("Bạn có muốn ghi đè nội dung file này không? (y/N): ").strip().lower()
        if overwrite != "y":
            print("Đã hủy thao tác.")
            return

    confirm = input("Bạn có chắc chắn muốn tạo bài viết này? (Y/n): ").strip().lower()
    if confirm in ["n", "no"]:
        print("Đã hủy thao tác.")
        return

    create_article(title, target_main_cat, target_sub_cat, rel_md_path, full_md_path)


def interactive_edit():
    """Giao diện sửa bài viết qua CLI."""
    _, nav_data = load_mkdocs_config()
    articles = get_all_articles_flat(nav_data)

    if not articles:
        print("⚠️ Không tìm thấy bài viết nào trong menu điều hướng.")
        return

    print("\n" + "=" * 60)
    print("               DANH SÁCH BÀI VIẾT ĐỂ CHỈNH SỬA            ")
    print("=" * 60)
    for idx, art in enumerate(articles, 1):
        status = "🟢" if art["exists"] else "🔴 (Không thấy file)"
        cat_info = f"[{art['category_path']}]" if art["category_path"] else ""
        print(f"  [{idx:2d}] {art['title']} {cat_info}")
        print(f"       -> docs/{art['path']} {status}")

    print("\nNhập số thứ tự bài viết cần sửa (hoặc 0 để hủy):")
    while True:
        try:
            val = input(f"Chọn bài viết [1-{len(articles)}]: ").strip()
            if val == "0":
                print("Đã hủy thao tác.")
                return
            idx = int(val) - 1
            if 0 <= idx < len(articles):
                chosen_article = articles[idx]
                break
            print(f"⚠️ Vui lòng nhập số từ 1 đến {len(articles)}.")
        except ValueError:
            print("⚠️ Giá trị nhập không hợp lệ.")

    print(f"\n📝 Đang chỉnh sửa: {chosen_article['title']} (docs/{chosen_article['path']})")
    new_title = input(f"👉 Tiêu đề mới (Enter để giữ '{chosen_article['title']}'): ").strip()
    if not new_title:
        new_title = chosen_article['title']

    old_main = chosen_article.get("main_category", "")
    old_sub = chosen_article.get("subcategory", "")

    change_cat = input("👉 Bạn có muốn đổi chuyên mục / vị trí không? (y/N): ").strip().lower()
    if change_cat == "y":
        header_text, nav_data = load_mkdocs_config()
        cat_structure = get_nav_categories(nav_data)
        main_cats = list(cat_structure.keys())

        print("\n📂 CHỌN CHUYÊN MỤC CHÍNH MỚI:")
        for i, cname in enumerate(main_cats, 1):
            print(f"  [{i}] {cname}")
        main_idx = prompt_user_choice(main_cats, "Chọn chuyên mục chính")
        target_main_cat = main_cats[main_idx]
        cat_info = cat_structure[target_main_cat]
        subs = list(cat_info["subcategories"].keys())

        if subs:
            print(f"\n📁 CHỌN MỤC CON TRONG '{target_main_cat}':")
            opts = ["(Không dùng mục con)"] + subs
            for i, opt in enumerate(opts, 1):
                print(f"  [{i}] {opt}")
            sub_idx = prompt_user_choice(opts, "Chọn mục con")
            target_sub_cat = None if sub_idx == 0 else subs[sub_idx - 1]
        else:
            target_sub_cat = None

        if target_sub_cat:
            sub_dir = cat_info["subcategories"][target_sub_cat]["dir_hint"]
            target_dir = sub_dir or f"{cat_info['dir_hint']}/{slugify(target_sub_cat)}"
        else:
            target_dir = cat_info["dir_hint"]

        filename = Path(chosen_article["path"]).name
        new_rel_path = f"{target_dir}/{filename}".replace("\\", "/")
    else:
        target_main_cat = old_main
        target_sub_cat = old_sub if old_sub else None
        new_rel_path = chosen_article["path"]

    ok, msg = update_article(
        old_rel_path=chosen_article["path"],
        new_title=new_title,
        new_main_cat=target_main_cat,
        new_sub_cat=target_sub_cat,
        new_rel_path=new_rel_path
    )
    if ok:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")


def interactive_delete():
    """Giao diện xóa bài viết qua CLI."""
    _, nav_data = load_mkdocs_config()
    articles = get_all_articles_flat(nav_data)

    if not articles:
        print("⚠️ Không tìm thấy bài viết nào trong menu điều hướng.")
        return

    print("\n" + "=" * 60)
    print("                  DANH SÁCH BÀI VIẾT                      ")
    print("=" * 60)
    for idx, art in enumerate(articles, 1):
        status = "🟢" if art["exists"] else "🔴 (Không thấy file)"
        cat_info = f"[{art['category_path']}]" if art["category_path"] else ""
        print(f"  [{idx:2d}] {art['title']} {cat_info}")
        print(f"       -> docs/{art['path']} {status}")

    print("\nNhập số thứ tự bài viết cần xóa (hoặc 0 để hủy):")
    while True:
        try:
            val = input(f"Chọn bài viết [1-{len(articles)}]: ").strip()
            if val == "0":
                print("Đã hủy thao tác.")
                return
            idx = int(val) - 1
            if 0 <= idx < len(articles):
                chosen_article = articles[idx]
                break
            print(f"⚠️ Vui lòng nhập số từ 1 đến {len(articles)}.")
        except ValueError:
            print("⚠️ Giá trị nhập không hợp lệ.")

    print("\n" + "=" * 60)
    print("                  XÁC NHẬN XÓA BÀI VIẾT                   ")
    print("=" * 60)
    print(f" 📄 Tiêu đề:        {chosen_article['title']}")
    print(f" 📝 File sẽ xóa:    docs/{chosen_article['path']}")
    print(" ⚠️ Thao tác này sẽ xóa file trên đĩa và gỡ bài viết khỏi menu.")
    print("=" * 60)

    confirm = input("Bạn có chắc chắn muốn XÓA bài viết này? (y/N): ").strip().lower()
    if confirm == "y":
        ok, msg = delete_article(chosen_article["path"])
        if ok:
            print(f"✅ {msg}")
        else:
            print(f"❌ {msg}")
    else:
        print("Đã hủy thao tác.")


def launch_web_ui():
    """Khởi động Web UI Admin Server."""
    admin_script = PROJECT_ROOT / "admin_server.py"
    if not admin_script.exists():
        print("Lỗi: Không tìm thấy admin_server.py")
        return
    print("\n🌐 Đang khởi động Web Admin Server tại http://127.0.0.1:8001/ ...")
    subprocess.run([sys.executable, str(admin_script)])


def parse_cli_args():
    """Xử lý tham số dòng lệnh."""
    parser = argparse.ArgumentParser(
        description="Tool quản lý bài viết và cập nhật menu trong PostgreSQL Handbook."
    )
    parser.add_argument("-t", "--title", help="Tiêu đề bài viết")
    parser.add_argument("-c", "--category", help="Chuyên mục chính (VD: 'Guide', 'Operations')")
    parser.add_argument("-s", "--subcategory", help="Mục con (VD: 'Hiệu năng', 'SQL')")
    parser.add_argument("-f", "--filename", help="Tên file .md tùy chọn")
    parser.add_argument("-y", "--yes", action="store_true", help="Bỏ qua xác nhận")
    parser.add_argument("-d", "--delete", action="store_true", help="Chế độ xóa bài viết")
    parser.add_argument("-e", "--edit", action="store_true", help="Chế độ chỉnh sửa bài viết")
    parser.add_argument("-p", "--path", help="Đường dẫn file cần xử lý (VD: 'guide/performance/explain.md')")
    parser.add_argument("--ui", action="store_true", help="Mở giao diện Web Admin Server")
    
    return parser.parse_args()


def main():
    args = parse_cli_args()

    if args.ui:
        launch_web_ui()
        return

    if args.delete:
        if args.path:
            rel_path = args.path.strip()
            if not args.yes:
                confirm = input(f"Xác nhận xóa '{rel_path}'? (y/N): ").strip().lower()
                if confirm != "y":
                    print("Đã hủy.")
                    return
            ok, msg = delete_article(rel_path)
            print(msg)
        else:
            interactive_delete()
        return

    if args.edit:
        interactive_edit()
        return

    if args.title and args.category:
        title = args.title.strip()
        main_cat = args.category.strip()
        sub_cat = args.subcategory.strip() if args.subcategory else None
        
        filename = args.filename.strip() if args.filename else f"{slugify(title)}.md"
        if not filename.endswith(".md"):
            filename += ".md"

        _, nav_data = load_mkdocs_config()
        cat_structure = get_nav_categories(nav_data)

        if main_cat in cat_structure:
            cat_info = cat_structure[main_cat]
            if sub_cat and sub_cat in cat_info["subcategories"]:
                target_dir = cat_info["subcategories"][sub_cat]["dir_hint"] or f"{cat_info['dir_hint']}/{slugify(sub_cat)}"
            elif sub_cat:
                target_dir = f"{cat_info['dir_hint']}/{slugify(sub_cat)}"
            else:
                target_dir = cat_info["dir_hint"]
        else:
            if sub_cat:
                target_dir = f"{slugify(main_cat)}/{slugify(sub_cat)}"
            else:
                target_dir = slugify(main_cat)

        rel_md_path = f"{target_dir}/{filename}".replace("\\", "/")
        full_md_path = DOCS_DIR / rel_md_path

        menu_location = f"{main_cat} > {sub_cat} > {title}" if sub_cat else f"{main_cat} > {title}"
        print(f"👉 Tạo bài viết: {title}")
        print(f"📂 File: docs/{rel_md_path}")
        print(f"📑 Menu: {menu_location}")

        if not args.yes:
            confirm = input("Xác nhận tạo? (Y/n): ").strip().lower()
            if confirm in ["n", "no"]:
                print("Đã hủy.")
                return

        create_article(title, main_cat, sub_cat, rel_md_path, full_md_path)
    else:
        try:
            interactive_wizard()
        except KeyboardInterrupt:
            print("\n\nĐã thoát.")
            sys.exit(0)


if __name__ == "__main__":
    main()
