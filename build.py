#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""静态站点生成器：读 content/data.json + templates/ -> 输出 output/

用法：
    python build.py            # 生成到 output/
    python build.py --serve    # 生成后在本机起预览服务（http://127.0.0.1:8000）

除页面外还生成：
    output/search.json            站内搜索索引（含全拼/首字母）
    output/static/assets/*        头像与 favicon
    output/images_thumb/*         列表缩略图（源目录 images_thumb/）
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pypinyin import Style, lazy_pinyin
from PIL import Image

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content" / "data.json"
TEMPLATES = ROOT / "templates"
IMAGES = ROOT / "images"
THUMBS = ROOT / "images_thumb"
STATIC = ROOT / "static"
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "output"

RELATED_COUNT = 4

_size_cache = {}


def log(msg):
    print(msg, flush=True)


def url_of(path):
    """把 data.json 里的相对路径（images/x/01.webp）转成站点绝对路径（/images/x/01.webp）。"""
    return "/" + str(path).lstrip("/")


def thumb_of(url):
    """预览图 URL -> 缩略图 URL（images_thumb/x/NN.webp）。"""
    return url.replace("/images/", "/images_thumb/", 1)


def source_path(url):
    """站点 URL（/images/... 或 /images_thumb/...）-> 源目录文件路径。"""
    path = str(url).lstrip("/")
    if path.startswith("images_thumb/"):
        path = "images/" + path[len("images_thumb/"):]
    return IMAGES / path[len("images/"):]


def cache_bust(url):
    """给图片 URL 加 ?v=mtime，内容更新后自动失效。"""
    if not url:
        return ""
    path_file = source_path(url)
    if not path_file.exists():
        return url
    return f"{url}?v={int(path_file.stat().st_mtime)}"


def image_size(path_file):
    key = str(path_file)
    if key not in _size_cache:
        try:
            with Image.open(path_file) as img:
                _size_cache[key] = img.size
        except Exception:
            _size_cache[key] = (0, 0)
    return _size_cache[key]


def load_data():
    if not CONTENT.exists():
        sys.exit(f"找不到内容文件：{CONTENT}")
    with CONTENT.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize(data):
    """统一路径写法，补齐缩略图/尺寸信息，并按首发日期倒序排序。"""
    for m in data["models"]:
        photos = [url_of(p) for p in m.get("photos", [])]
        m["photos"] = photos
        m["cover"] = photos[0] if photos else ""

        meta = []
        thumbs = []
        for p in photos:
            t = thumb_of(p)
            thumbs.append(t)
            w, h = image_size(source_path(p))
            meta.append({"src": p, "thumb": t, "w": w, "h": h})
        m["photo_meta"] = meta
        m["thumbs"] = thumbs

        w, h = image_size(source_path(m["cover"])) if m["cover"] else (0, 0)
        m["cover_w"], m["cover_h"] = w, h

    data["models"].sort(
        key=lambda m: (str(m.get("date", "")), str(m.get("id", ""))),
        reverse=True,
    )
    return data


def _label(m):
    return m.get("item_id") or m.get("title") or m.get("id", "")


def check_images(data, warnings):
    for m in data["models"]:
        if not m["photos"]:
            warnings.append(f"作品「{_label(m)}」没有配置图片")
        for p in m["photos"]:
            if not source_path(p).exists():
                warnings.append(f"图片缺失：{p}（作品「{_label(m)}」）")
            if not (ROOT / "images_thumb" / p.lstrip("/")[len("images/"):]).exists():
                warnings.append(f"缩略图缺失：{p}（作品「{_label(m)}」）")


def make_env():
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["thumb"] = thumb_of
    env.filters["bust"] = cache_bust
    return env


def absolute(site, path):
    domain = (site.get("domain") or "").strip().rstrip("/")
    return domain + path if domain else path


def render(env, template, out_path, **ctx):
    html = env.get_template(template).render(**ctx)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path


def copy_tree(src: Path, dst: Path):
    if not src.exists():
        return 0
    n = 0
    for p in src.rglob("*"):
        if p.is_file():
            target = dst / p.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            n += 1
    return n


def build_search_index(categories, models):
    """站内搜索索引：标题/编号/标签/分类/场景 + 全拼 + 首字母。"""
    cat_names = {c["id"]: c.get("name", "") for c in categories}
    items = []

    for m in models:
        cat_name = cat_names.get(m.get("category"), "")
        tags = m.get("tags") or []
        text = " ".join([
            m.get("title", ""),
            m.get("item_id", ""),
            " ".join(tags),
            cat_name,
            m.get("scene", ""),
        ])
        full = "".join(lazy_pinyin(text)).lower()
        initials = "".join(
            lazy_pinyin(text, style=Style.FIRST_LETTER)
        ).lower()

        items.append({
            "id": m["id"],
            "code": m.get("item_id", ""),
            "title": m.get("title", ""),
            "cat": cat_name,
            "tags": tags,
            "url": f"/m/{m['id']}/",
            "thumb": cache_bust(m["thumbs"][0]) if m.get("thumbs") else "",
            "text": text.lower(),
            "py": full,
            "ini": initials,
        })

    return {"items": items}


def make_assets(warnings):
    """头像（圆形裁剪后 144/72 WebP）与 favicon（32px PNG）。"""
    src = ASSETS / "avatar-source.jpg"
    out_dir = OUTPUT / "static" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        warnings.append(f"头像源文件缺失：{src}")
        return

    img = Image.open(src).convert("RGB")
    width, height = img.size
    side = int(min(width, height) * 0.42)
    center_x = int(width * 0.62)
    center_y = int(height * 0.19)
    left = max(0, min(center_x - side // 2, width - side))
    top = max(0, min(center_y - side // 2, height - side))
    square = img.crop((left, top, left + side, top + side))

    for size in (144, 72):
        square.resize((size, size), Image.LANCZOS).save(
            out_dir / f"avatar-{size}.webp",
            "WEBP",
            quality=88,
            method=6,
        )
    square.resize((32, 32), Image.LANCZOS).save(out_dir / "favicon-32.png")


def build():
    data = normalize(load_data())
    site = data["site"]
    categories = data["categories"]
    models = data["models"]
    cat_by_id = {c["id"]: c for c in categories}

    warnings = []
    check_images(data, warnings)
    for m in models:
        if m["category"] not in cat_by_id:
            warnings.append(f"作品「{_label(m)}」的分类 id「{m['category']}」不在分类列表中")

    counts = {c["id"]: 0 for c in categories}
    for m in models:
        if m["category"] in counts:
            counts[m["category"]] += 1

    static_ver = str(int(max(
        (STATIC / "style.css").stat().st_mtime,
        (STATIC / "app.js").stat().st_mtime,
    )))

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    env = make_env()
    pages = 0

    common = {
        "site": site,
        "categories": categories,
        "counts": counts,
        "static_ver": static_ver,
        "current_cat": "",
    }

    # 首页 = 推荐（全部作品，首发日期倒序）
    render(
        env, "index.html", OUTPUT / "index.html",
        **common,
        models=models,
        title=f"{site['name']} · {site['tagline']}",
        description=site["description"],
        og_image=absolute(site, models[0]["cover"] if models else ""),
        active_nav="",
    )
    pages += 1

    # 分类页
    for c in categories:
        cat_models = [m for m in models if m["category"] == c["id"]]
        render(
            env, "category.html", OUTPUT / "c" / c["id"] / "index.html",
            **{**common, "current_cat": c["id"]},
            cat=c,
            models=cat_models,
            title=f"{c['name']} - {site['name']}",
            description=f"{c['name']}：{c['desc']}。{site['description']}",
            og_image=absolute(
                site,
                next((m["cover"] for m in cat_models), ""),
            ),
        )
        pages += 1

    # 作品详情页
    for m in models:
        cat = cat_by_id.get(
            m["category"], {"id": m["category"], "name": m["category"]}
        )
        related = [
            x for x in models
            if x["category"] == m["category"] and x["id"] != m["id"]
        ][:RELATED_COUNT]
        render(
            env, "model.html", OUTPUT / "m" / m["id"] / "index.html",
            **{**common, "current_cat": m["category"]},
            m=m, cat=cat, related=related,
            title=f"【{m.get('item_id', '')}】{m.get('title', '')} · {cat['name']} - {site['name']}",
            description=(m.get("desc") or "")[:110] or f"{m.get('title', '')}的{cat['name']}写真作品",
            og_image=absolute(site, m["cover"]),
        )
        pages += 1

    # 帮助 / 招募（占位）
    for page, template in (("help", "help.html"), ("join", "join.html")):
        render(
            env, template, OUTPUT / page / "index.html",
            **common,
            title=f"{'帮助' if page == 'help' else '招募'} - {site['name']}",
            description=site["description"],
            og_image=absolute(site, models[0]["cover"] if models else ""),
        )
        pages += 1

    # 404
    render(
        env, "404.html", OUTPUT / "404.html",
        **common,
        title=f"页面不存在 - {site['name']}",
        description=site["description"],
        og_image="",
    )

    n_static = copy_tree(STATIC, OUTPUT / "static")
    n_images = copy_tree(IMAGES, OUTPUT / "images")
    n_thumbs = copy_tree(THUMBS, OUTPUT / "images_thumb")

    make_assets(warnings)

    search_data = build_search_index(categories, models)
    (OUTPUT / "search.json").write_text(
        json.dumps(search_data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    log(
        f"生成 {pages} 个页面，拷贝 static {n_static} 个 / "
        f"images {n_images} 个 / images_thumb {n_thumbs} 个文件"
    )
    log(f"搜索索引：{len(search_data['items'])} 条 -> output/search.json")
    log(f"输出目录：{OUTPUT}")
    for w in warnings:
        log(f"  ⚠ {w}")
    if warnings:
        log(f"（共 {len(warnings)} 条提示，不影响生成）")
    return OUTPUT


def serve(directory: Path, port: int = 8000):
    import functools
    import http.server
    import socketserver

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(directory)
    )
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        log(f"预览地址： http://127.0.0.1:{port}/  （Ctrl+C 结束）")
        httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="生成后起本地预览服务")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    out = build()
    if args.serve:
        serve(out, args.port)


if __name__ == "__main__":
    main()
