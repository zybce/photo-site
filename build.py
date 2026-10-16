#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""静态站点生成器：读 content/data.json + templates/ -> 输出 output/

用法：
    python build.py            # 生成到 output/
    python build.py --serve    # 生成后在本机起预览服务（http://127.0.0.1:8000）
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content" / "data.json"
TEMPLATES = ROOT / "templates"
IMAGES = ROOT / "images"
STATIC = ROOT / "static"
OUTPUT = ROOT / "output"

LATEST_COUNT = 4
RELATED_COUNT = 4


def log(msg):
    print(msg, flush=True)


def url_of(path):
    """把 data.json 里的相对路径（images/x/01.webp）转成站点绝对路径（/images/x/01.webp）。"""
    return "/" + str(path).lstrip("/")


def load_data():
    if not CONTENT.exists():
        sys.exit(f"找不到内容文件：{CONTENT}")
    with CONTENT.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize(data):
    """统一路径写法，并按日期倒序排好人物列表。"""
    for m in data["models"]:
        m["photos"] = [url_of(p) for p in m.get("photos", [])]
        m["cover"] = m["photos"][0] if m["photos"] else ""
    data["models"].sort(key=lambda m: m.get("date", ""), reverse=True)
    return data


def check_images(data, warnings):
    for m in data["models"]:
        if not m["photos"]:
            warnings.append(f"人物「{m['name']}」没有配置图片")
        for p in m["photos"]:
            if not (IMAGES / p.lstrip("/")[len("images/"):]).exists():
                warnings.append(f"图片缺失：{p}（人物「{m['name']}」）")


def make_env():
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
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
            warnings.append(f"人物「{m['name']}」的分类 id「{m['category']}」不在分类列表中")

    counts = {c["id"]: 0 for c in categories}
    for m in models:
        if m["category"] in counts:
            counts[m["category"]] += 1

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    env = make_env()
    pages = 0

    # 首页
    render(
        env, "index.html", OUTPUT / "index.html",
        site=site, categories=categories, counts=counts,
        latest=models[:LATEST_COUNT],
        title=f"{site['name']} · {site['tagline']}",
        description=site["description"],
        og_image=absolute(site, models[0]["cover"] if models else ""),
    )
    pages += 1

    # 分类页
    for c in categories:
        render(
            env, "category.html", OUTPUT / "c" / c["id"] / "index.html",
            site=site, cat=c,
            models=[m for m in models if m["category"] == c["id"]],
            title=f"{c['name']} - {site['name']}",
            description=f"{c['name']}：{c['desc']}。{site['description']}",
            og_image=absolute(site, next((m["cover"] for m in models if m["category"] == c["id"]), "")),
        )
        pages += 1

    # 人物详情页
    for m in models:
        cat = cat_by_id.get(m["category"], {"id": m["category"], "name": m["category"]})
        related = [x for x in models if x["category"] == m["category"] and x["id"] != m["id"]][:RELATED_COUNT]
        render(
            env, "model.html", OUTPUT / "m" / m["id"] / "index.html",
            site=site, m=m, cat=cat, related=related,
            title=f"{m['name']} · {cat['name']} - {site['name']}",
            description=(m.get("desc") or "")[:110] or f"{m['name']}的{cat['name']}写真作品",
            og_image=absolute(site, m["cover"]),
        )
        pages += 1

    n_static = copy_tree(STATIC, OUTPUT / "static")
    n_images = copy_tree(IMAGES, OUTPUT / "images")

    log(f"生成 {pages} 个页面，拷贝 static {n_static} 个 / images {n_images} 个文件")
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

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
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
