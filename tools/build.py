# -*- coding: utf-8 -*-
"""把京东商详截图裁掉重复的固定栏、去重叠、拼成一条连续长页。"""
from PIL import Image, ImageChops, ImageStat
import os, json

D = "/Users/claudy/Desktop/京东"
OUT = "/Users/claudy/WorkBuddy/2026-11-05-16-27-11/jd-detail/assets"
os.makedirs(OUT, exist_ok=True)

# (文件, 区块标签, 顶栏裁切点, 底栏裁切点)  —— 按真实浏览顺序
ORDER = [
    ("截图1.jpg",                                  "商品 · 首屏",       200, 2500),
    ("77379d412d8acc022f60c503ff5c47ef.jpg",       "商品 · 评价区",     400, 2500),
    ("b04fb2a72c07af6da7367196feedf497.jpg",       "商品 · 店铺与推荐", 400, 2500),
    ("c5353fb463dd942f97c8866f956de997.jpg",       "推荐 · 商品流",     400, 2500),
    ("121ce28ce8465fbae5d7f8ed9b03219b.jpg",       "推荐 · 活动专区",   400, 2500),
    ("d7e3c901bcb2c26be01c48b105ee3840.jpg",       "详情 · 商品介绍",   400, 2500),
    ("b957a5a8b84196226772a67e3cc63789.jpg",       "详情 · 影像系统",   400, 2500),
    ("e62973a58b2fb599c8235aa0cc0d900d.jpg",       "详情 · 芯片性能",   400, 2500),
    ("088299be45e63a524daac714a4734f83.jpg",       "详情 · 规格参数",   400, 2500),
    ("cdc3359b7d623491cd9f557210bd88ed.jpg",       "详情 · 服务说明",   400, 2500),
    ("667fbc623f9ae3984e0b59d6396af295.jpg",       "详情 · 看了又看",   400, 2500),
]

W = 1320
SCALE = 2 / 3           # 输出长图宽 880
FULL_W = int(W * SCALE)

def sig(im, step=6, cols=55):
    """低分辨率灰度行签名，用于相邻截图重叠检测。"""
    h = im.height // step
    g = im.convert("L").resize((cols, h), Image.LANCZOS)
    px = list(g.getdata())
    return [px[y*cols:(y+1)*cols] for y in range(h)]

def overlap(prev, nxt, L=18, thr=8.0):
    """用「下一段开头」在「上一段」里定位，返回应跳过的重复像素数。"""
    a, b = sig(prev), sig(nxt)
    if len(a) < L + 4 or len(b) < L:
        return 0, 999, 0
    # 模板要有纹理，避免纯白区域到处误匹配
    off = 0
    for _ in range(6):
        tpl = b[off:off+L]
        flat = [v for r in tpl for v in r]
        m = sum(flat)/len(flat)
        if (sum((v-m)**2 for v in flat)/len(flat))**0.5 > 7:
            break
        off += 8
    if off + L > len(b):
        return 0, 999, 0
    tpl = b[off:off+L]
    best, bestp = 1e9, -1
    for q in range(0, len(a) - L):
        s = 0
        for i in range(L):
            r1, r2 = a[q+i], tpl[i]
            for x in range(0, 55, 2):
                s += abs(r1[x] - r2[x])
        mae = s / (L * 28)
        if mae < best:
            best, bestp = mae, q
    if best < thr:
        skip = (len(a) - bestp + off) * 6
        if 0 < skip <= 1900:
            return skip, best, bestp
    return 0, best, bestp

segs, report = [], []
for idx, (f, label, yt, yb) in enumerate(ORDER):
    im = Image.open(os.path.join(D, f)).convert("RGB")
    if im.width != W:
        im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    crop = im.crop((0, yt, W, min(yb, im.height)))
    skip = 0
    if idx > 0:
        skip, mae, k = overlap(segs[-1]["img"], crop)
        report.append(f"{idx:2d} {label:14s} mae={mae:6.2f} k={k:3d} skip={skip:4d}px")
    if skip and skip < crop.height - 300:
        crop = crop.crop((0, skip, W, crop.height))
    segs.append({"img": crop, "label": label, "src": f, "src_top": yt + skip, "src_bottom": yt + skip + crop.height})

print("\n".join(report))
total = sum(s["img"].height for s in segs)
print(f"\n段数={len(segs)} 原尺寸总高={total}px -> 输出 {FULL_W}x{int(total*SCALE)}")

canvas = Image.new("RGB", (W, total), "white")
y = 0
meta = []
for s in segs:
    canvas.paste(s["img"], (0, y))
    h = s["img"].height
    meta.append({
        "label": s["label"], "src": s["src"],
        "y0": round(y * SCALE), "y1": round((y + h) * SCALE),
        "src_top": s["src_top"], "src_bottom": s["src_bottom"],
    })
    y += h

long_img = canvas.resize((FULL_W, int(total * SCALE)), Image.LANCZOS)
long_img.save(os.path.join(OUT, "page-long.jpg"), quality=88, optimize=True)
with open(os.path.join(OUT, "segments.json"), "w", encoding="utf-8") as fp:
    json.dump({"width": FULL_W, "height": long_img.height, "segments": meta}, fp, ensure_ascii=False, indent=2)
with open(os.path.join(OUT, "segments.js"), "w", encoding="utf-8") as fp:
    fp.write("window.JD_SEG=" + json.dumps({
        "total": long_img.height,
        "groups": [x[1] for x in ORDER],
        "seg": [[m["y0"], m["y1"]] for m in meta],
    }, ensure_ascii=False) + ";")

# 详情图轮播素材
GALLERY = [
    ("8a37777ff2399727c7c88b6629491e50.jpg", "gallery-1.jpg", "超宽阔显示屏 · 纳米纹理内屏减少眩光"),
    ("93aec55626afbcdf10fd9dcbd024e18b.jpg", "gallery-2.jpg", "常用 App 并排铺开 · 双电池系统 · 2 纳米制程"),
    ("d056c7960941634fd006451da2b733ab.jpg", "gallery-3.jpg", "折叠、站立、各种拗造型"),
]
gmeta = []
for src, name, cap in GALLERY:
    im = Image.open(os.path.join(D, src)).convert("RGB").resize((900, 900), Image.LANCZOS)
    im.save(os.path.join(OUT, name), quality=87, optimize=True)
    gmeta.append({"file": name, "caption": cap})
# 点击查看后的界面（截图 15）
v = Image.open(os.path.join(D, "dd346a62e2feee3b812a8866a1ca0d03.jpg")).convert("RGB")
v.resize((int(v.width * 0.5), int(v.height * 0.5)), Image.LANCZOS).save(os.path.join(OUT, "viewer-ref.jpg"), quality=86, optimize=True)
with open(os.path.join(OUT, "gallery.json"), "w", encoding="utf-8") as fp:
    json.dump(gmeta, fp, ensure_ascii=False, indent=2)

# 检查用缩略长图（宽 220）
canvas.resize((220, int(total * 220 / W)), Image.LANCZOS).save(os.path.join(OUT, "_preview.png"))
print("长图与轮播素材已生成")
