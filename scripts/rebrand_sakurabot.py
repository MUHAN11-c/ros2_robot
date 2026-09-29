# -*- coding: utf-8 -*-
"""品牌重塑：樱雷机器人研习社 / Sakura Robotics Lab → 樱机实验室 / SakuraBot Lab
同时把吉祥物素材路径从 assets/images/mascot*.svg 迁移到 assets/mascots/*.webp。
历史日志（重写路线图旧条目）不改。幂等可重跑。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGED = []


def patch(path, pairs):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    hit = False
    for old, new in pairs:
        got = text.count(old)
        if got == 0 and new in text:
            continue  # 已应用
        assert got == 1, f"{path}: 「{old[:36]}…」实际 {got} 处"
        text = text.replace(old, new)
        hit = True
    if hit:
        p.write_text(text, encoding="utf-8")
        CHANGED.append(path)


# ============ 1. 品牌名替换 ============
patch("mkdocs.yml", [
    ("site_description: 樱雷机器人研习社 · 面向机器人开发者的系统化知识库",
     "site_description: 樱机实验室 SakuraBot Lab · 面向机器人开发者的系统化知识库"),
    ("copyright: Sakura Robotics Lab · 樱雷机器人研习社",
     "copyright: SakuraBot Lab · 樱机实验室"),
])

patch("overrides/home.html", [
    ("<!-- Sakura Robotics Lab · 首页 Hero（左文案 + 右吉祥物，克制品牌视觉） -->",
     "<!-- SakuraBot Lab · 樱机实验室 · 首页 Hero（左文案 + 右插画，克制品牌视觉） -->"),
    ("SAKURA ROBOTICS LAB · 樱雷机器人研习社",
     "SAKURABOT LAB · 樱机实验室"),
])

patch("javascripts/app.js", [
    (" * Sakura Robotics Lab · app.js", " * SakuraBot Lab · app.js"),
])

patch("javascripts/mascot.js", [
    (" * Sakura Robotics Lab · 浮动吉祥物助手（紫樱）",
     " * SakuraBot Lab · 樱机实验室 · 浮动吉祥物助手（紫樱）"),
    ('if (/\\/$/.test(path)) return "樱雷机器人研习社";',
     'if (/\\/$/.test(path)) return "樱机实验室";'),
])

patch("stylesheets/mascot-assistant.css", [
    ("   Sakura Robotics Lab · 浮动吉祥物助手（rt-assistant）",
     "   SakuraBot Lab · 樱机实验室 · 浮动吉祥物助手（rt-assistant）"),
])

patch("stylesheets/tokens.css", [
    ("   Sakura Robotics Lab · Design Tokens",
     "   SakuraBot Lab · Design Tokens"),
    ("   樱雷机器人研习社 — 原创 Sakure-Electro 视觉系统",
     "   樱机实验室 SakuraBot Lab — 原创视觉系统"),
])

patch("scripts/sync_docs.py", [
    ("title: Robotics Tutorial · 樱雷机器人研习社",
     "title: Robotics Tutorial · 樱机实验室"),
])

patch("scripts/unify_symbols.py", [
    ('"""全站符号统一（樱雷符号表）：⭐→★、📋→◆。',
     '"""全站符号统一（樱机符号表）：⭐→★、📋→◆。'),
])

# ============ 2. 内容层 ============
patch("00_项目导航/从零开始学习路线总图.md", [
    ("> 🌸 品牌意象「樱雷」：樱 = 筑基的耐心，雷 = 前沿的锋芒——Sakura Robotics Lab 一路陪伴你。",
     "> 🌸 品牌意象「樱机」：樱 = 筑基的耐心，机 = 机器与机巧——SakuraBot Lab 一路陪伴你。"),
])

patch("00_项目导航/教学文档编写规范_零基础改编版.md", [
    ("允许轻度幽默与品牌意象点缀（樱雷/紫樱）",
     "允许轻度幽默与品牌意象点缀（樱机/紫樱）"),
    ("## 九、樱雷符号表（v6.2 新增，全站强制）",
     "## 九、樱机符号表（v6.2 新增，全站强制）"),
])

patch("02_C++基础与进阶/00_零基础入门/50_类与对象初步.md", [
    ('Battery bat("樱雷动力", 100.0);', 'Battery bat("樱机动力", 100.0);'),
])

# 历史脚本中的 new 字符串同步（防重跑回退）
patch("scripts/apply_ip_sweep.py", [
    ('Battery bat("稻妻动力", 100.0);\', \'Battery bat("樱雷动力", 100.0);\'),',
     'Battery bat("稻妻动力", 100.0);\', \'Battery bat("樱机动力", 100.0);\'),'),
])

# ============ 3. 素材路径迁移（svg → webp 素材库） ============
patch("overrides/home.html", [
    ("{{ 'assets/images/mascot.svg' | url }}", "{{ 'assets/mascots/sakura-02.webp' | url }}"),
    ('alt="紫樱 · 机器人研究员吉祥物"', 'alt="紫樱 · 樱机实验室看板娘"'),
])

patch("overrides/partials/mascot-assistant.html", [
    ("{{ 'assets/images/mascot-head.svg' | url }}", "{{ 'assets/mascots/avatar-128.webp' | url }}"),
    ("<span>Sakura · Robotics Study Assistant</span>",
     "<span>SakuraBot · Study Assistant</span>"),
])

patch("scripts/sync_docs.py", [
    # 404 用 04 号插画
    ('<img class="rt-404__mascot" src="assets/images/mascot.svg" alt="紫樱" width="180">',
     '<img class="rt-404__mascot" src="assets/mascots/sakura-04.webp" alt="紫樱" width="180">'),
    # 目录页提示卡用半身像
    ("![紫樱](assets/images/mascot.svg)", "![紫樱](assets/mascots/bust.webp)"),
])

patch("08_可视化实验室/README.md", [
    ("![紫樱](../assets/images/mascot.svg)", "![紫樱](../assets/mascots/bust.webp)"),
])

patch("00_项目导航/从零开始学习路线总图.md", [
    ("![紫樱](../assets/images/mascot.svg)", "![紫樱](../assets/mascots/bust.webp)"),
])

patch("stylesheets/components.css", [
    ("/* 内容页中的吉祥物默认出场尺寸约束（:where 置零优先级，让 hero/tip/404 专属尺寸生效） */\n.md-typeset :where(img[src*=\"assets/images/mascot\"]) {",
     "/* 内容页中的吉祥物默认出场尺寸约束（:where 置零优先级，让 hero/tip/404 专属尺寸生效） */\n.md-typeset :where(img[src*=\"assets/mascots/\"]) {"),
])

print(f"品牌重塑完成：{len(CHANGED)} 个文件")
for c in CHANGED:
    print("  ✔", c)
