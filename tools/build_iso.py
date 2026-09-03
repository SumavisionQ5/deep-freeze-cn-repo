# -*- coding: utf-8 -*-
"""
build_iso.py - 组装汉化镜像 (原版 BIN + 补丁 EXE + 补丁 SYSTEM.SAF + 译文 SAF)

步骤:
  1. 复制原版 BIN → build/Deep Freeze (Japan) patched.bin
  2. 写入补丁 EXE (扇区搜索 'PS-X EXE' 定位)
  3. 写入补丁 SYSTEM.SAF (字库/码表)
  4. 调用 import_text 将 1272 条译文写入 MENU1-5/OVERLAY 六个 SAF
  5. 生成配套 .cue

用法:
  python build_iso.py    # 一键构建完整汉化镜像
"""
import os
import re
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import saf
import import_text

sys.stdout.reconfigure(encoding='utf-8')


def main():
    if not os.path.exists(config.SRC_BIN):
        print(f"[错误] 找不到原版镜像: {config.SRC_BIN}")
        print("       请修改 tools/config.py 中 GAME_DIR 指向原版游戏目录。")
        return 1
    patched_exe = os.path.join(config.BUILD_DIR, "SLPS_018.17.patched")
    new_saf = os.path.join(config.BUILD_DIR, "SYSTEM.NEW.SAF")
    for p in (patched_exe, new_saf):
        if not os.path.exists(p):
            print(f"[错误] 缺少中间产物 {p}")
            print("       请先运行: python apply_patches.py && python build_saf.py")
            return 1

    out_bin = os.path.join(config.BUILD_DIR, "Deep Freeze (Japan) patched.bin")

    print("=" * 60)
    print("[1/5] 复制原版镜像")
    print("=" * 60)
    shutil.copyfile(config.SRC_BIN, out_bin)
    print(f"  {config.SRC_BIN} -> {out_bin}")

    bin_data = open(config.SRC_BIN, 'rb').read()
    exe_lbn = saf.find_exe_lbn(bin_data)
    assert exe_lbn is not None, "在原版 BIN 中找不到 'PS-X EXE'"
    print(f"  EXE 位于 LBN {exe_lbn} (搜索确认)")

    f = open(out_bin, 'r+b')

    print("=" * 60)
    print("[2/5] 写入补丁 EXE")
    print("=" * 60)
    exe_data = open(patched_exe, 'rb').read()
    saf.iso_write_bytes(f, exe_lbn, 0, exe_data)
    print(f"  {len(exe_data)} bytes ({(len(exe_data)+2047)//2048} 扇区) -> LBN {exe_lbn}")

    print("=" * 60)
    print("[3/5] 写入补丁 SYSTEM.SAF (字库/码表)")
    print("=" * 60)
    saf_data = open(new_saf, 'rb').read()
    lbn, size = config.SAF_LBNS['SYSTEM.SAF']
    assert len(saf_data) == size, f"SYSTEM.SAF 大小 {len(saf_data)} != {size}"
    saf.iso_write_bytes(f, lbn, 0, saf_data)
    print(f"  {len(saf_data)} bytes -> LBN {lbn}")

    print("=" * 60)
    print("[4/5] 导入 1272 条译文 (MENU1-5/OVERLAY)")
    print("=" * 60)
    ret = import_text.import_all(f)
    if ret != 0:
        f.close()
        return ret

    f.close()

    print("=" * 60)
    print("[5/5] 生成 CUE")
    print("=" * 60)
    cue_src = os.path.join(os.path.dirname(config.SRC_BIN),
                           os.path.splitext(os.path.basename(config.SRC_BIN))[0] + ".cue")
    cue_dst = os.path.join(config.BUILD_DIR, "Deep Freeze (Japan) patched.cue")
    if os.path.exists(cue_src):
        content = open(cue_src, 'r').read()
        content = re.sub(r'"[^"]*\.bin"', f'"{os.path.basename(out_bin)}"', content)
        open(cue_dst, 'w').write(content)
        print(f"  {cue_dst}")

    import hashlib
    md5 = hashlib.md5(open(out_bin, 'rb').read()).hexdigest().upper()
    print()
    print("=" * 60)
    print(f"构建完成: {out_bin}")
    print(f"MD5: {md5}")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
