#!/usr/bin/env python3
"""阶段2：数据库 Schema 升级。

运行前请确保已备份: cp spatial_literature.db spatial_literature_pre_schema.db
"""

import sqlite3, os, json

DB = os.path.join(os.path.dirname(__file__), "spatial_literature.db")
TAGS_JSON = os.path.join(os.path.dirname(__file__), "tags.json")

conn = sqlite3.connect(DB)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")
print("[1/5] WAL mode enabled")

# ── 读取现有 schema 和数据 ──
cur = conn.execute("SELECT * FROM literature")
old_cols = [d[0] for d in cur.description]
rows = cur.fetchall()
print(f"[2/5] Read {len(rows)} rows, {len(old_cols)} columns")

# ── 加载标签分组 ──
with open(TAGS_JSON, "r", encoding="utf-8") as f:
    tag_groups = json.load(f)
tag_to_group = {}
for group, tags in tag_groups.items():
    for t in tags:
        tag_to_group[t.strip()] = group

# ── 新表列定义 ──
new_col_defs = []
for c in old_cols:
    if c == "pmid":
        new_col_defs.append(("pmid", "TEXT"))
    elif c == "uncertainty_score":
        new_col_defs.append(("uncertainty_score", "REAL"))
    else:
        new_col_defs.append((c, "TEXT"))  # 其余列统一 TEXT（已有 BigInt 的保留原意）
# 特殊列修正
for i, (name, _) in enumerate(new_col_defs):
    if name == "is_manually_confirmed":
        new_col_defs[i] = (name, "INTEGER")
    elif name == "citation_count":
        new_col_defs[i] = (name, "INTEGER")

new_col_defs.append(("is_discarded", "INTEGER DEFAULT 0"))

# ── 创建新 literature 表 ──
conn.execute("DROP TABLE IF EXISTS literature_new")
col_parts = [f"{name} {dtype}" for name, dtype in new_col_defs]
create_sql = f"CREATE TABLE literature_new ({', '.join(col_parts)}, PRIMARY KEY (pmid))"
conn.execute(create_sql)
print(f"  New table columns: {[n for n, _ in new_col_defs]}")

# ── 创建 article_tags 表 ──
conn.execute("""
    CREATE TABLE IF NOT EXISTS article_tags (
        pmid TEXT NOT NULL,
        tag TEXT NOT NULL,
        tag_group TEXT NOT NULL,
        PRIMARY KEY (pmid, tag)
    )
""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_article_tags_pmid ON article_tags(pmid)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_article_tags_tag ON article_tags(tag)")

# ── 逐行迁移 ──
old_col_idx = {c: i for i, c in enumerate(old_cols)}
new_col_names = [n for n, _ in new_col_defs]

discard_migrated = 0
tag_rows_inserted = 0

for row in rows:
    row_dict = dict(zip(old_cols, row))

    # ── 分离 Discarded ──
    is_discarded = 0
    tags_str = str(row_dict.get("tags", "") or "")
    if "Discarded" in tags_str:
        is_discarded = 1
        discard_migrated += 1
        cleaned = [t.strip() for t in tags_str.split(";")
                   if t.strip() and t.strip() != "Discarded"]
        tags_str = "; ".join(cleaned)
        row_dict["tags"] = tags_str

    # ── 转换 uncertainty_score ──
    try:
        us_val = float(row_dict.get("uncertainty_score", 0) or 0)
    except (ValueError, TypeError):
        us_val = 0.0
    row_dict["uncertainty_score"] = us_val

    # ── is_manually_confirmed 转整数 ──
    try:
        row_dict["is_manually_confirmed"] = int(row_dict.get("is_manually_confirmed", 0) or 0)
    except (ValueError, TypeError):
        row_dict["is_manually_confirmed"] = 0

    row_dict["is_discarded"] = is_discarded

    # ── 插入 literature_new ──
    values = []
    for name in new_col_names:
        val = row_dict.get(name)
        if val is None:
            val = "" if name != "uncertainty_score" and name != "is_discarded" and name != "is_manually_confirmed" else 0
        values.append(val)

    placeholders = ", ".join(["?" for _ in new_col_names])
    conn.execute(
        f"INSERT OR REPLACE INTO literature_new ({', '.join(new_col_names)}) VALUES ({placeholders})",
        values
    )

    # ── 拆分标签写入 article_tags ──
    if tags_str:
        for t in tags_str.split(";"):
            t = t.strip()
            if not t:
                continue
            group = tag_to_group.get(t, "method_note")
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO article_tags (pmid, tag, tag_group) VALUES (?, ?, ?)",
                    (row_dict["pmid"], t, group)
                )
                tag_rows_inserted += 1
            except sqlite3.IntegrityError:
                pass

# ── 原子替换 ──
conn.execute("DROP TABLE IF EXISTS literature")
conn.execute("ALTER TABLE literature_new RENAME TO literature")
conn.execute("CREATE INDEX IF NOT EXISTS idx_pmid ON literature(pmid)")

conn.commit()

# ── 验证 ──
cur = conn.execute("PRAGMA table_info(literature)")
print("[3/5] New schema:")
for r in cur.fetchall():
    print(f"  {r[1]:25s} {r[2]:15s} pk={r[5]}")

cur = conn.execute("SELECT COUNT(*) FROM literature")
print(f"[4/5] Row count: {cur.fetchone()[0]}")

cur = conn.execute("SELECT COUNT(*) FROM article_tags")
print(f"     Tag rows: {cur.fetchone()[0]}")

cur = conn.execute("SELECT COUNT(*) FROM literature WHERE is_discarded=1")
print(f"     Discarded: {cur.fetchone()[0]} (migrated from tags: {discard_migrated})")

conn.close()
print("[5/5] Schema migration complete.")
