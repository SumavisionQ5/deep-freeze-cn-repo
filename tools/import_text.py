# -*- coding: utf-8 -*-
"""
import_text.py - 文本一键导入器 (译文 → SAF → ISO BIN)

功能: 将 data/translation/trans_p1-p4.py 中的全部译文, 以自定义码页编码写入
已打补丁的 ISO BIN。这是修改译文后重新生成镜像的核心工具。

工作方式:
  * data/original/skel_all.tsv 提供行号 → (SAF 文件, SAF 内文件, 文本偏移) 映射
  * data/original/text_extract.csv 提供每条原文的原始字节 (用于写前校验,
    确保没有错位——若某条原文校验失败则跳过并报告, 不盲写)
  * 对每个被修改的 .B 数据文件: LZSS 解压 → 原位替换文本 → 清零填充 →
    重压缩 → 更新目录 clen → 写回 ISO
  * 空间约束: 译文编码后字节数 ≤ 原文占用 + 其后零填充 (保留 1 字节终止符);
    重压缩后 ≤ 该文件可用扇区空间 (不移动任何文件偏移)
  * OVERLAY.SAF 的 SCRIPT.B 无译文, 但承担 tutorial 字体路径补丁
    (*KANJI2.KPX→*KANJI.KPX 等 12 字节等长替换, 见 HACKING.md 第 7 节),
    即使无译文条目也会强制执行

用法:
  python import_text.py --check     # 只校验 (码表覆盖/原文匹配/空间), 不写盘
  python import_text.py             # 校验 + 写盘 (需已用 build_iso.py 生成镜像,
                                    # 或独立运行时传入 --bin 参数)
  python import_text.py --bin PATH  # 指定目标 BIN
"""
import csv
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import saf
import codepage
import translations

sys.stdout.reconfigure(encoding='utf-8')

AD = os.path.dirname(os.path.abspath(__file__))
SKEL_TSV = os.path.join(config.DATA_DIR, "original", "skel_all.tsv")
CSV_PATH = os.path.join(config.DATA_DIR, "original", "text_extract.csv")

# import 按骨架表驱动 (行号 → SAF/文件/偏移), 因此会自动覆盖骨架中出现的
# 全部资源包 (MENU1-5 与 OVERLAY 及其内全部含译文 .B 文件), 不受
# config.TEXT_SAFS 限制。SKEL 的 SAF 必须存在于 config.SAF_LBNS 中。

# SCRIPT.B 字体路径补丁 (v8): tutorial 教学模式加载 KANJI2 字库,
# 必须改指主字库; 等长 12 字节替换, 空间无变化
SCRIPT_B_FONT_PATCHES = {
    0x24: (b'*KANJI2.KPX\x00', b'*KANJI.KPX\x00\x00'),
    0x30: (b'KANJI2.TBL\x00\x00', b'KANJI.TBL\x00\x00\x00'),
}


def load_skeleton():
    """加载骨架 TSV: {行号: {file, off, ind, nl, jlen, text}}"""
    skel = {}
    for ln in open(SKEL_TSV, encoding='utf-8').read().splitlines()[1:]:
        p = ln.split('\t')
        skel[int(p[0])] = dict(file=p[1], off=p[2], ind=int(p[3]),
                               nl=int(p[4]), jlen=int(p[5]), text=p[6])
    return skel


def load_csv_hex():
    """加载 CSV 原始字节: {(file, off小写): hex}"""
    m = {}
    for r in csv.DictReader(open(CSV_PATH, encoding='utf-8-sig')):
        key = (r['file'], r['text_off'].lower())
        if key not in m:
            m[key] = r['hex']
    return m


def build_edit_plan():
    """构建编辑计划: {SAF名: {SAF内文件名: [edit...]}}"""
    all_tr = translations.load_translations()
    skel = load_skeleton()
    csv_hex = load_csv_hex()
    ccm = codepage.load_codepage()

    plan = {}
    for k, trans in sorted(all_tr.items()):
        s = skel[k]
        tag, fname = s['file'].split('__', 1)
        safn = tag + '.SAF'
        assert safn in config.SAF_LBNS, f"skel 引用了未知 SAF: {safn}"
        plan.setdefault(safn, {}).setdefault(fname, []).append({
            'line': k,
            'text_off': int(s['off'], 16),
            'orig_hex': csv_hex.get((s['file'], s['off'].lower()), ''),
            'translation': trans,
            'skel_text': s['text'],
        })
    return plan, ccm


def process_file(dec, edits, ccm, ctx, dry_run):
    """对单个解压后的 .B 文件执行文本替换; 返回 (ok, skip, fail)"""
    n_ok = n_skip = 0
    for r in sorted(edits, key=lambda x: x['text_off']):
        toff = r['text_off']
        orig = r['orig_hex']
        orig_len = len(orig) // 2

        if toff + orig_len > len(dec):
            print(f"  [警告] L{r['line']} {ctx} 0x{toff:X}: 偏移越界, 跳过")
            n_skip += 1
            continue

        if bytes(dec[toff:toff + orig_len]).hex() != orig:
            print(f"  [警告] L{r['line']} {ctx} 0x{toff:X}: 原文校验失败 (数据可能与预期不符), 跳过")
            n_skip += 1
            continue

        try:
            new_bytes = codepage.encode_text(r['translation'], ccm)
        except ValueError as ex:
            print(f"  [警告] L{r['line']}: {ex}, 跳过")
            n_skip += 1
            continue

        # 可用空间 = 原文 + 其后零填充, 保留 1 字节 0x00 终止符
        end = toff + orig_len
        pad_end = end
        while pad_end < len(dec) and dec[pad_end] == 0:
            pad_end += 1
        avail = (pad_end - 1) - toff

        if len(new_bytes) > avail:
            print(f"  [警告] L{r['line']} 0x{toff:X}: 译文 {len(new_bytes)}B > 可用 {avail}B, 跳过")
            print(f"         原文: {r['skel_text'][:30]}")
            print(f"         译文: {r['translation'][:30]}")
            n_skip += 1
            continue

        if not dry_run:
            dec[toff:toff + len(new_bytes)] = new_bytes
            for q in range(toff + len(new_bytes), pad_end):
                dec[q] = 0
        n_ok += 1
    return n_ok, n_skip


def apply_font_patches(dec, ctx):
    """SCRIPT.B 字体路径补丁; 返回 (是否修改, 失败数)"""
    changed = False
    fails = 0
    for poff, (old_s, new_s) in SCRIPT_B_FONT_PATCHES.items():
        if bytes(dec[poff:poff + len(old_s)]) == old_s:
            dec[poff:poff + len(new_s)] = new_s
            print(f"  [FONT] {ctx} +0x{poff:X}: {old_s!r} -> {new_s!r}")
            changed = True
        elif bytes(dec[poff:poff + len(new_s)]) == new_s:
            print(f"  [FONT] {ctx} +0x{poff:X}: 已是新值")
        else:
            cur = bytes(dec[poff:poff + 12])
            print(f"  [FONT][失败] {ctx} +0x{poff:X}: 非预期字节 {cur!r}")
            fails += 1
    return changed, fails


def import_all(f, dry_run=False):
    """对已打开的目标 BIN 执行全部译文导入; 返回 0 成功"""
    plan, ccm = build_edit_plan()

    total_ok = total_skip = total_fail = 0

    # 先做码表覆盖检查
    missing = set()
    for tag, files in plan.items():
        for fname, edits in files.items():
            for r in edits:
                for ch in r['translation']:
                    if ch != '|' and ch not in ccm:
                        missing.add(ch)
    if missing:
        print(f"[错误] {len(missing)} 个字符不在码表中: "
              + ' '.join(f"U+{ord(c):04X}({c})" for c in sorted(missing)))
        return 1
    print(f"码表覆盖检查: 通过 (码表 {len(ccm)} 字)")

    for safn in sorted(plan):
        lbn, size = config.SAF_LBNS[safn]
        saf_data = bytearray(saf.iso_read_bytes(f, lbn, 0, size))
        es = saf.saf_entries(bytes(saf_data))
        dirty = False
        print(f"\n--- {safn} (LBN {lbn}) ---")

        for fname, edits in sorted(plan[safn].items()):
            e = saf.find_entry(es, fname)
            if e is None:
                print(f"  [跳过] {safn} 中找不到 {fname}")
                total_fail += 1
                continue
            off = e.sector * saf.USER_SIZE
            raw = bytes(saf_data[off:off + e.clen])
            dec = bytearray(saf.lzss_decompress(raw))
            ctx = f"{fname}@{safn}"

            font_patched = False
            if safn == 'OVERLAY.SAF' and fname.lstrip('*').upper() == 'SCRIPT.B':
                font_patched, ffail = apply_font_patches(dec, ctx)
                total_fail += ffail

            n_ok, n_skip = process_file(dec, edits, ccm, ctx, dry_run)
            total_ok += n_ok
            total_skip += n_skip

            if n_ok == 0 and not font_patched:
                continue

            if dry_run:
                continue

            comp = saf.lzss_compress(bytes(dec))
            if saf.lzss_decompress(comp) != bytes(dec):
                print(f"  [失败] {fname}: 往返校验失败")
                total_fail += 1
                continue
            # 可用空间 = 下一文件起始扇区 - 本文件起始扇区
            nxt = min([x.sector for x in es if x.sector > e.sector],
                      default=len(saf_data) // saf.USER_SIZE)
            space = nxt * saf.USER_SIZE - off
            if len(comp) > space:
                print(f"  [失败] {fname}: 重压缩 {len(comp)}B > 空间 {space}B")
                total_fail += 1
                continue
            saf_data[off:off + len(comp)] = comp
            for q in range(off + len(comp), off + e.clen):
                saf_data[q] = 0
            struct.pack_into('<H', saf_data, e.dir_off + 16, len(comp))
            dirty = True
            extra = " + 字体补丁" if font_patched else ""
            print(f"  [OK] {fname}: {n_ok} 条替换 ({n_skip} 跳过){extra}, clen {e.clen}->{len(comp)}")

        # OVERLAY.SAF: SCRIPT.B 无译文条目时也强制应用字体补丁
        if safn == 'OVERLAY.SAF' and 'SCRIPT.B' not in {k.lstrip('*').upper()
                                                        for k in plan[safn]}:
            e = saf.find_entry(es, 'SCRIPT.B')
            if e is None:
                print(f"  [错误] OVERLAY.SAF 中找不到 SCRIPT.B")
                total_fail += 1
            else:
                off = e.sector * saf.USER_SIZE
                dec = bytearray(saf.lzss_decompress(bytes(saf_data[off:off + e.clen])))
                changed, ffail = apply_font_patches(dec, "SCRIPT.B@" + safn)
                total_fail += ffail
                if changed and not dry_run:
                    comp = saf.lzss_compress(bytes(dec))
                    nxt = min([x.sector for x in es if x.sector > e.sector],
                              default=len(saf_data) // saf.USER_SIZE)
                    space = nxt * saf.USER_SIZE - off
                    if len(comp) > space or saf.lzss_decompress(comp) != bytes(dec):
                        print(f"  [失败] SCRIPT.B: 压缩/空间校验失败")
                        total_fail += 1
                    else:
                        saf_data[off:off + len(comp)] = comp
                        for q in range(off + len(comp), off + e.clen):
                            saf_data[q] = 0
                        struct.pack_into('<H', saf_data, e.dir_off + 16, len(comp))
                        dirty = True
                        print(f"  [OK] SCRIPT.B: 字体补丁, clen {e.clen}->{len(comp)}")

        if dirty and not dry_run:
            saf.iso_write_bytes(f, lbn, 0, bytes(saf_data))
            print(f"  -> 已写回 ISO (LBN {lbn})")

    print()
    print("=" * 60)
    mode = "校验" if dry_run else "导入"
    print(f"{mode}完成: {total_ok} 条成功, {total_skip} 条跳过, {total_fail} 条失败")
    print("=" * 60)
    return 0 if total_fail == 0 else 1


def main():
    check_only = '--check' in sys.argv
    bin_path = None
    if '--bin' in sys.argv:
        bin_path = sys.argv[sys.argv.index('--bin') + 1]
    if bin_path is None:
        bin_path = os.path.join(config.BUILD_DIR, "Deep Freeze (Japan) patched.bin")

    if not check_only and not os.path.exists(bin_path):
        print(f"[错误] 目标 BIN 不存在: {bin_path}")
        print("       请先运行 python build_iso.py 构建镜像, 或用 --bin 指定路径。")
        return 1

    if check_only:
        # 纯校验模式: 不需要 BIN
        plan, ccm = build_edit_plan()
        print(f"待导入: {sum(len(v) for fs in plan.values() for v in fs.values())} 条译文, "
              f"涉及 {len(plan)} 个 SAF")
        f = open(bin_path, 'rb') if os.path.exists(bin_path) else None
        if f:
            ret = import_all(f, dry_run=True)
            f.close()
        else:
            print(f"(目标 BIN 不存在, 跳过镜像级校验)")
            ret = 0
        return ret

    f = open(bin_path, 'r+b')
    ret = import_all(f, dry_run=False)
    f.close()
    if ret == 0:
        print(f"\n镜像已更新: {bin_path}")
    return ret


if __name__ == '__main__':
    sys.exit(main())
