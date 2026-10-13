#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REDPET 看板自动同步 · 把 sync.py 生成的两个 JSON 注入 docs/index.html
替换页面里的 const EMBEDDED_DAILY_DATA = {...}; 和 const EMBEDDED_SCALE_DATA = {...};
"""
import json
import re

HTML = "docs/index.html"


def main():
    daily = json.load(open("daily_data.json", encoding="utf-8"))
    scale = json.load(open("scale_data.json", encoding="utf-8"))

    html = open(HTML, encoding="utf-8").read()
    dj = json.dumps(daily, ensure_ascii=False)
    sj = json.dumps(scale, ensure_ascii=False)

    # 非贪婪匹配到第一个 };（JSON 内部不会出现 }; 字面量）
    html, n1 = re.subn(
        r"const EMBEDDED_DAILY_DATA\s*=\s*\{.*?\};\s*",
        f"const EMBEDDED_DAILY_DATA = {dj};",
        html, flags=re.S,
    )
    html, n2 = re.subn(
        r"const EMBEDDED_SCALE_DATA\s*=\s*\{.*?\};\s*",
        f"const EMBEDDED_SCALE_DATA = {sj};",
        html, flags=re.S,
    )

    if n1 == 0 or n2 == 0:
        raise SystemExit(f"未找到变量占位，注入失败 n1={n1} n2={n2}（检查 docs/index.html 变量名）")

    open(HTML, "w", encoding="utf-8").write(html)
    print(f"OK 已注入 DAILY_DATA(n={n1}) SCALE_DATA(n={n2})")


if __name__ == "__main__":
    main()
