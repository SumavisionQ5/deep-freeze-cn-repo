# -*- coding: utf-8 -*-
"""
gen_bilingual.py - 生成中日对照总表 data/translation/translation_all.tsv

从 skel_all.tsv (日文原文) + trans_p1-4.py (中文译文) 合成一份便于浏览
与审校的 TSV 对照表。此表仅供人工阅读，导入器不读取；
修改译文请编辑 trans_pN.py 后运行 build_iso.py。

用法 (在 tools/ 下):
  python gen_bilingual.py            # 写 data/translation/translation_all.tsv
  python gen_bilingual.py --check    # 只校验不写盘 (对照已存在的表)
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translations  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKEL = os.path.join(ROOT, "data", "original", "skel_all.tsv")
OUT = os.path.join(ROOT, "data", "translation", "translation_all.tsv")


def main():
    check_only = "--check" in sys.argv
    tr = translations.load_translations()
    fp = translations.false_positive_lines()

    with open(SKEL, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        col = {name: i for i, name in enumerate(header)}
        rows = []
        for ln in f:
            p = ln.rstrip("\n").split("\t")
            rows.append((int(p[0]), p[col["file"]], p[col["off"]], p[col["text"]]))

    out = ["line\tfile\toff\toriginal\ttranslated"]
    missing = []
    for line_no, fname, off, orig in rows:
        orig = orig.replace("\t", " ")
        translated = tr.get(line_no, "").replace("\t", " ")
        if not translated and line_no not in fp:
            missing.append(line_no)
        out.append(f"{line_no}\t{fname}\t{off}\t{orig}\t{translated}")

    if missing:
        print(f"[警告] {len(missing)} 行无译文: {missing}")
    else:
        print(f"覆盖检查通过: {len(rows)} 行全部有译文 "
              f"(含 {len(fp)} 行页脚 FP 行, 保留日文)")

    if check_only:
        return 0

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(out) + "\n")
    print(f"已写入 {OUT} ({len(out)} 行)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
