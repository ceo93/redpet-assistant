#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REDPET 看板自动同步 · 读企微两张表 -> 生成 docs/index.html 需要的 JSON
读取用 @wecom/cli（以「ceo的机器人」身份，凭证由 GitHub Actions Secrets 恢复）。

表1 每日活跃数量整理【内】 -> EMBEDDED_DAILY_DATA 的 records（每日发言人数）
表2 社群活跃度每日记录   -> EMBEDDED_SCALE_DATA 的 records（各群规模）+ 两表 groups.size
"""
import subprocess
import json
import re
import unicodedata
from datetime import datetime, timezone, timedelta

DOC_DAILY = "e3_ASUARQa5AEYCN6JG5OQtGTKy0kxmk"  # 每日活跃数量整理【内】
DOC_SCALE = "e3_ASUARQa5AEYCNSQk5OrtoS6KhhOnH"  # 社群活跃度每日记录
YEAR = 2026


def read_sheet(docid, rng):
    """调 wecom-cli 读表，失败重试 3 次。返回 CSV 文本。rng 为读取范围（两表列数不同）。"""
    last = ""
    for attempt in range(3):
        try:
            out = subprocess.check_output(
                ["wecom-cli", "sheet", "ranges", "get",
                 "--docid", docid, "--sheet-id", "000001", "--range", rng],
                stderr=subprocess.STDOUT, timeout=120,
            )
            data = json.loads(out)
            if data.get("errcode") == 0 and data.get("content"):
                return data["content"]
            last = str(data)
        except Exception as e:
            last = str(e)
        print(f"  [retry {attempt + 1}] 读表 {docid} 失败: {last}")
    raise SystemExit(f"读取企微表失败: {docid}")


def rows_of(content):
    return [ln.split(",") for ln in content.strip().split("\r\n") if ln.strip()]


def norm_date(label):
    """把表头里的日期标签归一成 2026-08-10 这种 ISO 日期。

    兼容历史表头里的各种写法：
      8.10数量 / 8.7人数 / 9月18日 / 9-12数量 / 9.25 / 10.1 / ８.２６数量（全角）
    """
    label = label.strip()
    # 全角数字/标点统一转成半角，再清掉空格和量词后缀
    label = unicodedata.normalize("NFKC", label)
    label = label.replace(" ", "").replace("数量", "").replace("人数", "")
    # 8.10 / 8-12 / 9.25 / 10.1
    m = re.match(r"^(\d+)[\-\.](\d+)$", label)
    if m:
        return f"{YEAR}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    # 9月18日 / 10月9日
    m = re.match(r"^(\d+)月(\d+)日$", label)
    if m:
        return f"{YEAR}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def parse(content):
    """返回 (records, latest)。records={日期:{群:值}}，latest={群:最近有值}。"""
    rows = rows_of(content)
    if not rows:
        return {}, {}
    header = rows[0][1:]
    dates = [norm_date(h) for h in header]
    records, latest = {}, {}
    for row in rows[1:]:
        g = row[0].strip() if row else ""
        if not g or g == "群名":
            continue
        for i, d in enumerate(dates):
            if d is None:
                continue
            v = row[i + 1].strip() if i + 1 < len(row) else ""
            if v in ("", "、", " "):
                continue
            try:
                n = int(v)
            except ValueError:
                continue
            records.setdefault(d, {})[g] = n
            latest[g] = n
    return records, latest


def main():
    print("读表1（活跃）...")
    d_records, _ = parse(read_sheet(DOC_DAILY, "A1:CJ200"))   # 表1 有 88 列
    print("读表2（规模）...")
    s_records, s_latest = parse(read_sheet(DOC_SCALE, "A1:Z200"))   # 表2 只有 26 列

    # 群名并集（两张表可能不完全一致）
    all_groups = set()
    for d in d_records.values():
        all_groups.update(d.keys())
    for d in s_records.values():
        all_groups.update(d.keys())
    groups = sorted(all_groups)
    group_size = {g: s_latest.get(g, 0) for g in groups}

    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz).isoformat(timespec="seconds")

    daily = {
        "version": 1,
        "updatedAt": now,
        "note": "数据来自企微表格「每日活跃数量整理」自动同步；后续每日由面板填写或同步追加。",
        "groups": [{"name": g, "size": group_size.get(g, 0)} for g in groups],
        "records": d_records,
    }
    scale = {
        "version": 1,
        "updatedAt": now,
        "note": "数据来自企微表格「社群活跃度每日记录-规模」自动同步。",
        "groups": [{"name": g, "size": group_size.get(g, 0)} for g in groups],
        "records": s_records,
    }

    with open("daily_data.json", "w", encoding="utf-8") as f:
        json.dump(daily, f, ensure_ascii=False, indent=1)
    with open("scale_data.json", "w", encoding="utf-8") as f:
        json.dump(scale, f, ensure_ascii=False, indent=1)

    print(f"OK 群数={len(groups)} 活跃日期数={len(d_records)} 规模日期数={len(s_records)}")


if __name__ == "__main__":
    main()
