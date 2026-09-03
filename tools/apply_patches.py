# -*- coding: utf-8 -*-
"""
apply_patches.py - 对原版 PS-X EXE (SLPS_018.17) 应用 12 处 MIPS 补丁

补丁内容 (详见 docs/HACKING.md 第 6 节):
  1.  TBL 查找上限 slti 0x400 → 0x4CC (支持 1228 字)
  2-3. KPX 字形步长 sll 4→3 / subu→addu (60B/字形 → 36B/字形)
  4.  字库外层循环上限 0x78 → 0x48 (120 → 72 半字)
  5-6. VRAM 搬运宽 4→3 / 高 15→12 (半字)
  7.  对话框全角字步进 14 → 12
  8-10. 行高 15 → 13 (三处) / 精灵尺寸 15 → 12
  11. 行高第三处 (延迟槽内)
  12. pool[6] TBL 加载数据字 0x801FB000 → 0x801EC000

用法:
  python apply_patches.py            # 读取原版 EXE → 输出 build/SLPS_018.17.patched
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

AD = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8')


def off_of(va):
    return va - config.BASE_LOAD


# (va, old_bytes, new_bytes, 说明); va==0 时为数据字补丁, 用 data_patch
PATCHES = [
    (0x80030318, b'\x00\x04\x62\x28', b'\xCC\x04\x62\x28',
     "slti $v0,$v1,0x400 -> 0x4CC (TBL limit 1024->1228)"),
    (0x800301FC, b'\x00\x11\x05\x00', b'\xC0\x10\x05\x00',
     "sll $v0,$a1,4 -> sll 3 (KPX stride 60B->36B step1)"),
    (0x80030200, b'\x23\x10\x45\x00', b'\x21\x10\x45\x00',
     "subu -> addu (KPX stride step2)"),
    (0x800301F8, b'\x78\x00\xE9\x24', b'\x48\x00\xE9\x24',
     "addiu $t1,$a3,0x78 -> 0x48 (loop 120->72 halfwords)"),
    (0x80030280, b'\x04\x00\x02\x24', b'\x03\x00\x02\x24',
     "addiu $v0,$zero,4 -> 3 (VRAM width halfwords)"),
    (0x80030288, b'\x0F\x00\x02\x24', b'\x0C\x00\x02\x24',
     "addiu $v0,$zero,0xF -> 0xC (VRAM height)"),
    (0x80030624, b'\x0E\x00\x73\x26', b'\x0C\x00\x73\x26',
     "addiu $s3,$s3,0xE -> 0xC (dialog fullwidth step)"),
    (0x80030650, b'\x0F\x00\xB5\x26', b'\x0D\x00\xB5\x26',
     "addiu $s5,$s5,0xF -> 0xD (line height 1)"),
    (0x80030744, b'\x0F\x00\xB5\x26', b'\x0D\x00\xB5\x26',
     "addiu $s5,$s5,0xF -> 0xD (line height 2)"),
    (0x800305DC, b'\x0F\x00\x03\x24', b'\x0C\x00\x03\x24',
     "addiu $v1,$zero,0xF -> 0xC (sprite size)"),
    (0x8003069C, b'\x0F\x00\xB5\x26', b'\x0D\x00\xB5\x26',
     "addiu $s5,$s5,0xF -> 0xD (line height 3, delay slot)"),
]

DATA_PATCHES = [
    (0x65840, 0x801FB000, 0x801EC000, "pool[6] TBL address"),
]


def main():
    src_exe = config.SRC_EXE
    if not os.path.exists(src_exe):
        print(f"[错误] 找不到原版 EXE: {src_exe}")
        print("       请将原版 SLPS_018.17 放到游戏目录的 'image file' 子目录,")
        print("       或修改 tools/config.py 中的 SRC_EXE 路径。")
        return 1

    d = bytearray(open(src_exe, 'rb').read())
    print(f"原版 EXE: {src_exe} ({len(d)} bytes)")

    ok = fail = 0
    for va, old, new, desc in PATCHES:
        off = off_of(va)
        actual = bytes(d[off:off + 4])
        if actual == old:
            d[off:off + 4] = new
            print(f"  [OK]   0x{va:08X}: {desc}")
            ok += 1
        elif actual == new:
            print(f"  [SKIP] 0x{va:08X}: 已是补丁值 ({desc})")
            ok += 1
        else:
            print(f"  [FAIL] 0x{va:08X}: 期望 {old.hex(' ')} 实际 {actual.hex(' ')}")
            print(f"         {desc}")
            fail += 1

    for foff, old_val, new_val, desc in DATA_PATCHES:
        cur = struct.unpack_from('<I', d, foff)[0]
        if cur == old_val:
            struct.pack_into('<I', d, foff, new_val)
            print(f"  [OK]   file 0x{foff:X}: 0x{old_val:08X} -> 0x{new_val:08X} ({desc})")
            ok += 1
        elif cur == new_val:
            print(f"  [SKIP] file 0x{foff:X}: 已是补丁值 ({desc})")
            ok += 1
        else:
            print(f"  [FAIL] file 0x{foff:X}: 期望 0x{old_val:08X} 实际 0x{cur:08X} ({desc})")
            fail += 1

    print(f"\n合计: {ok} 成功, {fail} 失败")
    if fail:
        return 1

    os.makedirs(config.BUILD_DIR, exist_ok=True)
    out = os.path.join(config.BUILD_DIR, "SLPS_018.17.patched")
    open(out, 'wb').write(d)
    print(f"\n补丁 EXE: {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
