# -*- coding: utf-8 -*-
"""
verify.py - 汉化镜像全量校验

对构建/应用补丁得到的镜像执行:
  1. EXE 12 处补丁点字节确认
  2. SYSTEM.SAF: KPX 解压大小 = 游戏计算值 (256 倍数), TBL clen
  3. SCRIPT.B 字体路径字符串 (*KANJI.KPX / KANJI.TBL)
  4. 全部 1272 条译文从镜像读回解码比对

用法:
  python verify.py --bin "path/to/Deep Freeze (Japan) patched.bin"
"""
import importlib.util
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import saf
import codepage
import translations
import import_text

sys.stdout.reconfigure(encoding='utf-8')

EXE_CHECKS = [
    (0x20B18, b'\xCC\x04\x62\x28', 'TBL limit 0x4CC'),
    (0x209F8, b'\x48\x00\xE9\x24', 'loop bound 0x48'),
    (0x209FC, b'\xC0\x10\x05\x00', 'sll 3 (stride1)'),
    (0x20A00, b'\x21\x10\x45\x00', 'addu (stride2)'),
    (0x20A80, b'\x03\x00\x02\x24', 'VRAM width 3'),
    (0x20A88, b'\x0C\x00\x02\x24', 'VRAM height 0xC'),
    (0x20E24, b'\x0C\x00\x73\x26', 'dialog step 0xC'),
    (0x20E50, b'\x0D\x00\xB5\x26', 'line height 1 0xD'),
    (0x20E9C, b'\x0D\x00\xB5\x26', 'line height 2 0xD'),
    (0x20F44, b'\x0D\x00\xB5\x26', 'line height 3 0xD'),
    (0x20DDC, b'\x0C\x00\x03\x24', 'sprite size 0xC'),
    (0x65840, b'\x00\xC0\x1E\x80', 'pool[6] TBL addr 0x801EC000'),
]


def main():
    bin_path = None
    if '--bin' in sys.argv:
        bin_path = sys.argv[sys.argv.index('--bin') + 1]
    if not bin_path:
        bin_path = os.path.join(config.BUILD_DIR, "Deep Freeze (Japan) patched.bin")
    if not os.path.exists(bin_path):
        print(f"[错误] 找不到镜像: {bin_path}")
        return 1

    f = open(bin_path, 'rb')
    allok = True

    # ---- 1. EXE 补丁 ----
    bin_data = open(bin_path, 'rb').read()
    exe_lbn = saf.find_exe_lbn(bin_data)
    print(f"EXE LBN: {exe_lbn}")
    for off, exp, desc in EXE_CHECKS:
        got = saf.iso_read_bytes(f, exe_lbn, off, 4)
        ok = got == exp
        if not ok:
            allok = False
        print(f"  {desc}: {'PASS' if ok else 'FAIL got ' + got.hex(' ')}")

    # ---- 2. SYSTEM.SAF 字库 ----
    lbn, size = config.SAF_LBNS['SYSTEM.SAF']
    saf_data = saf.iso_read_bytes(f, lbn, 0, size)
    es = saf.saf_entries(saf_data)
    kpx = saf.find_entry(es, config.KPX_NAME)
    tbl = saf.find_entry(es, config.TBL_NAME)
    dec = saf.lzss_decompress(saf_data[kpx.sector * saf.USER_SIZE:
                                       kpx.sector * saf.USER_SIZE + kpx.clen])
    ok1 = kpx.game_size() == len(dec)
    ok2 = len(dec) % 256 == 0
    ok3 = tbl.clen == 2456
    print(f"  KPX 解压 {len(dec)}B, 游戏计算 {kpx.game_size():#x}: "
          f"{'PASS' if ok1 else 'FAIL'}")
    print(f"  KPX 大小 256 倍数: {'PASS' if ok2 else 'FAIL'}")
    print(f"  TBL clen {tbl.clen} (期望 2456): {'PASS' if ok3 else 'FAIL'}")
    allok = allok and ok1 and ok2 and ok3

    # ---- 3. SCRIPT.B 字体路径 ----
    lbn, size = config.SAF_LBNS['OVERLAY.SAF']
    ovl = saf.iso_read_bytes(f, lbn, 0, size)
    oes = saf.saf_entries(ovl)
    se = saf.find_entry(oes, 'SCRIPT.B')
    sdec = saf.lzss_decompress(ovl[se.sector * saf.USER_SIZE:
                                   se.sector * saf.USER_SIZE + se.clen])
    ok4 = bytes(sdec[0x24:0x30]) == b'*KANJI.KPX\x00\x00'
    ok5 = bytes(sdec[0x30:0x3C]) == b'KANJI.TBL\x00\x00\x00'
    print(f"  SCRIPT.B 字体路径 KPX: {'PASS' if ok4 else 'FAIL ' + repr(bytes(sdec[0x24:0x30]))}")
    print(f"  SCRIPT.B 字体路径 TBL: {'PASS' if ok5 else 'FAIL ' + repr(bytes(sdec[0x30:0x3C]))}")
    allok = allok and ok4 and ok5

    # ---- 4. 译文回读 ----
    ccm = codepage.load_codepage()
    rev = {(v[0], v[1]): k for k, v in ccm.items()}
    all_tr = translations.load_translations()
    skel = import_text.load_skeleton()
    csv_hex = import_text.load_csv_hex()

    groups = {}
    for k, trans in all_tr.items():
        s = skel[k]
        tag, fname = s['file'].split('__', 1)
        groups.setdefault(tag + '.SAF', {}).setdefault(fname, []).append((k, s, trans))

    n_ok = n_fail = 0
    errs = []
    for safn, files in sorted(groups.items()):
        lbn, size = config.SAF_LBNS[safn]
        sd = saf.iso_read_bytes(f, lbn, 0, size)
        ses = saf.saf_entries(sd)
        for fname, items in sorted(files.items()):
            e = saf.find_entry(ses, fname)
            if e is None:
                for k, _, _ in items:
                    n_fail += 1
                    errs.append((k, 'entry missing'))
                continue
            off = e.sector * saf.USER_SIZE
            fdec = saf.lzss_decompress(sd[off:off + e.clen])
            for k, s, trans in items:
                toff = int(s['off'], 16)
                orig_len = len(csv_hex.get((s['file'], s['off'].lower()), '')) // 2
                decoded = codepage.decode_text(fdec, toff, orig_len + 64, rev)
                if decoded == trans:
                    n_ok += 1
                else:
                    n_fail += 1
                    if len(errs) <= 20:
                        errs.append((k, f"exp[{trans[:40]}] got[{decoded[:40]}]"))

    print(f"  译文回读: {n_ok}/{n_ok + n_fail}")
    for k, msg in errs[:20]:
        print(f"    L{k}: {msg}")
    if n_fail:
        allok = False

    f.close()
    print()
    print("=" * 40)
    print("VERIFY:", "ALL PASS" if allok else "FAILED")
    print("=" * 40)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
