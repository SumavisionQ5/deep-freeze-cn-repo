# -*- coding: utf-8 -*-
"""
build_saf.py - 生成补丁版 SYSTEM.SAF (替换字库 KANJI.KPX + 码表 KANJI.TBL)

内容:
  * 新 KPX (12x12 2bpp, 36B/字形, 1228 字 = 44208B) 补齐至 256 倍数后
    LZSS 压缩, 原位覆盖原 *KANJI.KPX 数据
  * 新 TBL (1228 项自定义升序码, 2456B) 原位覆盖, 溢出部分覆盖死文件
    KANJI2.KPX 的扇区 (游戏不加载 KANJI2 字库, 覆盖无害)
  * 更新目录: KPX 的 clen/decomp_size, TBL 的 clen

关键坑 (详见 docs/HACKING.md 第 5 节):
  游戏按 entry[11]<<16|entry[15]<<8|entry[19] 计算解压大小,
  原 19 号字节恒为 0x00, 故解压大小低字节必须为 0 → KPX 必须补齐到 256 倍数,
  否则开机读字库黑屏 (v6 之前的历史教训)。

用法:
  python build_saf.py     # 输出 build/SYSTEM.NEW.SAF
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import saf

sys.stdout.reconfigure(encoding='utf-8')


def main():
    kpx_path = os.path.join(config.FONT_DIR, "KANJI.KPX")
    tbl_path = os.path.join(config.FONT_DIR, "KANJI.TBL")
    for p in (kpx_path, tbl_path):
        if not os.path.exists(p):
            print(f"[错误] 找不到 {p}")
            return 1

    new_kpx = open(kpx_path, 'rb').read()
    # 补齐到 256 倍数 (游戏解压大小低字节必须为 0)
    if len(new_kpx) % 256:
        new_kpx += b'\x00' * (256 - len(new_kpx) % 256)
    new_tbl = open(tbl_path, 'rb').read()

    print(f"新 KPX: {len(new_kpx)} bytes ({len(new_kpx)//config.GLYPH_BYTES} 字形 x 36B, 已补齐 256 倍数)")
    print(f"新 TBL: {len(new_tbl)} bytes ({len(new_tbl)//2} 项)")

    saf_path = os.path.join(config.ARCHIVE, "SYSTEM.SAF")
    if not os.path.exists(saf_path):
        print(f"[错误] 找不到原版 SYSTEM.SAF: {saf_path}")
        print("       需要先从原版镜像解包 ARCHIVE (见 docs/HACKING.md 第 2 节),")
        print("       或修改 tools/config.py 中的 ARCHIVE 路径。")
        return 1

    data = bytearray(open(saf_path, 'rb').read())
    count = struct.unpack_from('<I', data, 0)[0]
    es = saf.saf_entries(bytes(data))
    print(f"原 SYSTEM.SAF: {len(data)} bytes, {count} 条目")

    kpx_e = saf.find_entry(es, config.KPX_NAME)
    tbl_e = saf.find_entry(es, config.TBL_NAME)
    assert kpx_e and tbl_e, "SYSTEM.SAF 中找不到 KPX/TBL 条目"
    print(f"  KPX: sector={kpx_e.sector} clen={kpx_e.clen} decomp={kpx_e.decomp_size:#x}")
    print(f"  TBL: sector={tbl_e.sector} clen={tbl_e.clen}")

    # ---- 压缩 KPX ----
    comp = saf.lzss_compress(bytes(new_kpx))
    assert saf.lzss_decompress(comp) == bytes(new_kpx), "KPX 往返校验失败"
    print(f"KPX 压缩: {len(comp)} bytes (原 clen {kpx_e.clen})")
    if len(comp) > kpx_e.clen:
        print(f"[错误] 新 KPX 压缩后 {len(comp)}B 超过原空间 {kpx_e.clen}B, 无法原位覆盖")
        return 1

    kpx_off = kpx_e.sector * saf.USER_SIZE
    data[kpx_off:kpx_off + len(comp)] = comp
    for q in range(kpx_off + len(comp), kpx_off + kpx_e.clen):
        data[q] = 0
    struct.pack_into('<H', data, kpx_e.dir_off + 14, len(new_kpx))   # decomp_size 低16位
    struct.pack_into('<H', data, kpx_e.dir_off + 16, len(comp))      # clen
    print(f"KPX 目录更新: clen={len(comp)}, decomp_size={len(new_kpx)} (=0x{len(new_kpx):X}, 低字节必须为 0)")

    # ---- 写入 TBL (2 扇区, 溢出覆盖死文件 KANJI2.KPX 扇区) ----
    tbl_off = tbl_e.sector * saf.USER_SIZE
    data[tbl_off:tbl_off + len(new_tbl)] = new_tbl
    struct.pack_into('<H', data, tbl_e.dir_off + 16, len(new_tbl))
    print(f"TBL 目录更新: clen={len(new_tbl)} (sector={tbl_e.sector}, 占 2 扇区, 溢出覆盖死文件 KANJI2.KPX)")

    # ---- 校验 ----
    es2 = saf.saf_entries(bytes(data))
    kpx2 = saf.find_entry(es2, config.KPX_NAME)
    dec = saf.lzss_decompress(bytes(data[kpx2.sector * saf.USER_SIZE:
                                          kpx2.sector * saf.USER_SIZE + kpx2.clen]))
    assert dec == bytes(new_kpx), "KPX 写回校验失败"
    assert kpx2.game_size() == len(new_kpx), \
        f"游戏计算大小 {kpx2.game_size():#x} != 实际 {len(new_kpx):#x}"
    print("写回校验: KPX 解压一致, 游戏计算大小一致")

    os.makedirs(config.BUILD_DIR, exist_ok=True)
    out = os.path.join(config.BUILD_DIR, "SYSTEM.NEW.SAF")
    open(out, 'wb').write(data)
    print(f"\n输出: {out} ({len(data)} bytes)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
