"""
MkDocs hook tách biệt môi trường Dev (local) và Prod (GitHub Pages).
- Môi trường Dev (mkdocs.dev.yml / local): Giữ nguyên trang Quản trị (admin.md).
- Môi trường Prod (mkdocs.prod.yml hoặc MKDOCS_ENV=prod): Tự động loại bỏ
  mục 'Quản trị' khỏi menu điều hướng (nav) và không build file admin.md.
"""

import os
from pathlib import Path


def _is_prod_env(config) -> bool:
    """Xác định môi trường đang chạy là prod hay dev."""
    env = os.environ.get("MKDOCS_ENV", "").strip().lower()
    if env in ("prod", "production"):
        return True
    if env in ("dev", "development", "local"):
        return False
    cfg_path = getattr(config, "config_file_path", "") or ""
    if Path(cfg_path).name.lower() == "mkdocs.prod.yml":
        return True
    return False


def _filter_admin_nav(nav_items):
    """Đệ quy loại bỏ mục trỏ tới admin.md khỏi cấu trúc nav."""
    filtered = []
    for item in nav_items:
        if isinstance(item, dict):
            new_dict = {}
            for k, v in item.items():
                if isinstance(v, str) and v.replace("\\", "/").lstrip("/") == "admin.md":
                    continue
                if isinstance(v, list):
                    sub = _filter_admin_nav(v)
                    if sub:
                        new_dict[k] = sub
                else:
                    new_dict[k] = v
            if new_dict:
                filtered.append(new_dict)
        else:
            filtered.append(item)
    return filtered


def on_config(config):
    """Loại bỏ trang Quản trị khỏi nav khi build ở môi trường production."""
    if _is_prod_env(config) and config.get("nav"):
        config["nav"] = _filter_admin_nav(config["nav"])
    return config


def on_files(files, config):
    """Loại bỏ file admin.md khỏi danh sách file build khi ở môi trường production."""
    if _is_prod_env(config):
        for f in list(files):
            if f.src_uri.replace("\\", "/").lstrip("/") == "admin.md":
                files.remove(f)
    return files
