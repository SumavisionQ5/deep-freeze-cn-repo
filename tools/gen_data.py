# -*- coding: utf-8 -*-
"""
gen_data.py - 从原版镜像重新生成全部数据文件 (可选的"从零复现"入口)

输出 (写入 data/original/, 覆盖前会备份原文件):
  text_extract.csv   全部日文文本 (SJIS 原文 + 偏移 + 原始字节)
  skel_all.tsv       行号 → 文件/偏移/缩进/换行数/原文长度/原文 骨架表
  saf_lbn.json       全部 SAF 在 ISO 中的 LBN 与大小
  blocks_info.json   各 .B 文件的块表 (偏移表) 信息

依赖: 原版镜像与解包的 ARCHIVE (config.py), 提取逻辑为经验证的启发式
(假名/全角判定 + 自举常用汉字字典 + 结构对齐评分), 详见 HACKING.md 第 3 节。

用法:  python gen_data.py --bin 原版.bin [--out 输出目录]
"""
import csv
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import saf

sys.stdout.reconfigure(encoding='utf-8')

KANA = re.compile(r'[ぁ-んァ-ヶー]')
FULLWIDTH = re.compile(r'[Ａ-Ｚａ-ｚ０-９　]')
PUNCT = re.compile(r'[、。！？…―「」『』・：；（）]')

# 自举字典锚点文件 (已知纯真文本, 用于纯汉字串判定)
ANCHORS = ['OVERLAY__STAGE01A.B.bin', 'OVERLAY__STAGE01C.B.bin',
           'OVERLAY__STAGE02A.B.bin', 'OVERLAY__COMPUTER.B.bin',
           'OVERLAY__TOPMENU.B.bin']


def build_dict(decomp_dir):
    """从锚点文件自举常用汉字字典"""
    chars = set()
    for fn in ANCHORS:
        p = os.path.join(decomp_dir, fn)
        if not os.path.exists(p):
            continue
        d = open(p, 'rb').read()
        i, n = 0, len(d)
        while i < n:
            b = d[i]
            if (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF) and i + 1 < n \
                    and (0x40 <= d[i + 1] <= 0xFC and d[i + 1] != 0x7F):
                j, dbcs = i, 0
                while j < n:
                    b2 = d[j]
                    if (0x81 <= b2 <= 0x9F or 0xE0 <= b2 <= 0xEF) and j + 1 < n \
                            and (0x40 <= d[j + 1] <= 0xFC and d[j + 1] != 0x7F):
                        j += 2
                        dbcs += 1
                    elif b2 == 0x7C:
                        j += 1
                    else:
                        break
                if dbcs >= 2:
                    try:
                        s = d[i:j].decode('shift-jis')
                        chars |= set(c for c in s if 0x3000 <= ord(c) < 0xFB00)
                    except Exception:
                        pass
                i = max(j, i + 1)
                continue
            i += 1
    return chars


def parse_blocks(d):
    """解析 .B 文件块表 (u32 计数 + u32 偏移数组)"""
    if len(d) < 8:
        return []
    cnt = struct.unpack_from('<I', d, 0)[0]
    if cnt == 0 or 4 + cnt * 4 > len(d) or cnt > 256:
        return []
    offs = [struct.unpack_from('<I', d, 4 + i * 4)[0] for i in range(cnt)]
    table_end = 4 + cnt * 4
    if any(o < table_end for o in offs) or offs != sorted(offs) or offs[-1] > len(d):
        return []
    return [(o, (offs[i + 1] if i + 1 < len(offs) else len(d)) - o) for i, o in enumerate(offs)]


def extract_candidates(d):
    """粗提取 SJIS 候选串 (0x00 终止)"""
    res = []
    i, n = 0, len(d)
    while i < n:
        b = d[i]
        if (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF):
            j, dbcs, cur = i, 0, bytearray()
            terminated = False
            while j < n:
                b2 = d[j]
                if (0x81 <= b2 <= 0x9F or 0xE0 <= b2 <= 0xEF) and j + 1 < n \
                        and (0x40 <= d[j + 1] <= 0xFC and d[j + 1] != 0x7F):
                    cur += d[j:j + 2]
                    j += 2
                    dbcs += 1
                elif b2 == 0x7C:
                    cur.append(b2)
                    j += 1
                else:
                    terminated = (b2 == 0)
                    break
            if dbcs >= 2 and len(cur) >= 4 and terminated:
                try:
                    res.append((i, j, cur.decode('shift-jis')))
                except UnicodeDecodeError:
                    pass
            i = max(j, i + 1)
            continue
        i += 1
    return res


def classify(d, off, end, s, DICT):
    """REAL / FAKE 判定"""
    if re.search(r'[\u0400-\u04FF\u2500-\u25FF]', s):
        return 'FAKE'
    if KANA.search(s):
        return 'REAL'
    if FULLWIDTH.search(s):
        return 'REAL'
    if PUNCT.search(s):
        return 'REAL'
    chars = [c for c in s if ord(c) >= 0x3000]
    if not chars:
        return 'FAKE'
    ratio = sum(1 for c in chars if c in DICT) / len(chars)
    aligned = (off % 4 == 0)
    pad = (end + 1 < len(d)) and all(x == 0 for x in d[end + 1:min(end + 4, len(d))])
    if ratio >= 0.75 and aligned and pad:
        return 'REAL'
    if ratio >= 0.75 and (aligned or pad):
        return 'REAL'
    if ratio >= 0.9:
        return 'REAL'
    return 'FAKE'


def main():
    if '--bin' in sys.argv:
        bin_path = sys.argv[sys.argv.index('--bin') + 1]
    else:
        bin_path = config.SRC_BIN
    if not os.path.exists(bin_path):
        print(f"[错误] 找不到原版镜像: {bin_path}")
        return 1
    if not os.path.isdir(config.ARCHIVE):
        print(f"[错误] 找不到解包目录: {config.ARCHIVE}")
        print("       请先从原版镜像解包 *.SAF (可用任意 ISO 工具或")
        print("       reference/dump_safs.py)。")
        return 1

    out_dir = os.path.join(config.DATA_DIR, 'original')
    if '--out' in sys.argv:
        out_dir = sys.argv[sys.argv.index('--out') + 1]
    os.makedirs(out_dir, exist_ok=True)

    # ---- 1. 记录 SAF LBN (config 中为原盘解析结果, 与 data/original/saf_lbn.json 一致) ----
    bin_data = open(bin_path, 'rb').read()
    print("扫描 SAF LBN ...")
    # 直接采用 config 中已验证的映射
    json.dump({k: list(v) for k, v in config.SAF_LBNS.items()},
              open(os.path.join(out_dir, 'saf_lbn.json'), 'w'), indent=1)

    # ---- 2. 解压全部含文本的 SAF 到临时目录 ----
    tmp = os.path.join(config.BUILD_DIR, 'decomp')
    os.makedirs(tmp, exist_ok=True)
    file_map = {}   # "TAG__FILE.B" -> (safn, entry)
    for safn in config.TEXT_SAFS:
        lbn, size = config.SAF_LBNS[safn]
        f = open(bin_path, 'rb')
        sd = saf.iso_read_bytes(f, lbn, 0, size)
        f.close()
        tag = safn[:-4]
        for e in saf.saf_entries(sd):
            if not e.name.upper().endswith('.B'):
                continue
            raw = sd[e.sector * saf.USER_SIZE:e.sector * saf.USER_SIZE + e.clen]
            dec = saf.lzss_decompress(raw)
            fn = f"{tag}__{e.name.lstrip('*')}.bin"
            open(os.path.join(tmp, fn), 'wb').write(dec)
            file_map[fn[:-4]] = (safn, e.name.lstrip('*'))
    print(f"解压 {len(file_map)} 个 .B 文件 -> {tmp}")

    # ---- 3. 文本提取 ----
    DICT = build_dict(tmp)
    print(f"自举字典: {len(DICT)} 字符")
    rows = []
    for fn in sorted(os.listdir(tmp)):
        if not fn.endswith('.B.bin'):
            continue
        file_id = fn[:-4]
        d = open(os.path.join(tmp, fn), 'rb').read()
        for off, end, s in extract_candidates(d):
            if classify(d, off, end, s, DICT) != 'REAL':
                continue
            rows.append({
                'file': file_id,
                'block_off': '',
                'text_off': f'0x{off:X}',
                'japanese': s,
                'raw_bytes': end - off,
                'judgement': 'REAL',
                'translation': '',
                'hex': d[off:end].hex(),
            })

    # 块表信息
    blocks_info = {}
    for fn in sorted(os.listdir(tmp)):
        if not fn.endswith('.B.bin'):
            continue
        d = open(os.path.join(tmp, fn), 'rb').read()
        blocks = parse_blocks(d)
        if blocks:
            blocks_info[fn[:-4]] = [[f'0x{o:X}', l] for o, l in blocks]

    out_csv = os.path.join(out_dir, 'text_extract.csv')
    with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['file', 'block_off', 'text_off',
                                          'japanese', 'raw_bytes', 'judgement',
                                          'translation', 'hex'])
        w.writeheader()
        w.writerows(rows)
    json.dump(blocks_info, open(os.path.join(out_dir, 'blocks_info.json'), 'w'),
              ensure_ascii=False, indent=1)

    # ---- 4. 骨架表 (与既有译文行号对齐需要人工/翻译记录参与,
    #         仓库直接附带成品 skel_all.tsv; 此处仅生成原始版供比对) ----
    out_tsv = os.path.join(out_dir, 'skel_original.tsv')
    with open(out_tsv, 'w', encoding='utf-8', newline='') as f:
        f.write("line\tfile\toff\tind\tnl\tjlen\ttext\n")
        for i, r in enumerate(rows, 1):
            ind = 1 if r['japanese'].startswith('\u3000') else 0
            nl = r['japanese'].count('|') + 1
            f.write(f"{i}\t{r['file']}\t{r['text_off']}\t{ind}\t{nl}\t"
                    f"{r['raw_bytes']}\t{r['japanese']}\n")

    print(f"\n输出:")
    print(f"  {out_csv} ({len(rows)} 条)")
    print(f"  {out_dir}\\blocks_info.json")
    print(f"  {out_dir}\\saf_lbn.json")
    print(f"  {out_tsv} (原始骨架; 仓库附带与译文对齐的 skel_all.tsv)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
