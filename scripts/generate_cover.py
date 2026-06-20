#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Agently 品牌背景图 900x500"""
from PIL import Image, ImageDraw, ImageFont
import os

# 900x500 画布
img = Image.new('RGB', (900, 500), color='white')
draw = ImageDraw.Draw(img)

# 蓝紫渐变 (顶部 #3B82F6 → 底部 #8A2BE2)
for y in range(500):
    r = int(59 + (138 - 59) * y / 500)
    g = int(130 + (43 - 130) * y / 500)
    b = int(246 + (226 - 246) * y / 500)
    draw.line([(0, y), (900, y)], fill=(r, g, b))

# 字体 - 使用支持中文的 Noto Sans CJK
font = ImageFont.truetype('/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc', 48)
font2 = ImageFont.truetype('/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc', 20)

# 主标题
bbox = draw.textbbox((0, 0), 'Agently', font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
draw.text(((900 - tw) / 2, (500 - th) / 2), 'Agently', fill='white', font=font)

# 副标题
bbox2 = draw.textbbox((0, 0), 'AI 资讯 · 每日速览', font=font2)
tw2, th2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
draw.text(((900 - tw2) / 2, (500 - th) / 2 + th + 20), 'AI 资讯 · 每日速览', fill='white', font=font2)

# 保存
out_dir = '/root/workspace/agently.top/frontend/public'
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'agently_cover.jpg')
img.save(out_path, quality=95)
print(f'Generated: {out_path}')
