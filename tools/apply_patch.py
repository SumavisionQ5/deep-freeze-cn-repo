# -*- coding: utf-8 -*-
"""
apply_patch.py - 应用 deep-freeze-cn.bpatch 差异补丁到原版镜像

用法:
  python apply_patch.py deep-freeze-cn.bpatch --src 原版.bin -o 输出.bin
  python apply_patch.py patches/deep-freeze-cn.bpatch --src "D:\\...\\Deep Freeze (Japan).bin" -o patched.bin
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')

MAGIC = b"DFCNPATCH001"


def main():
    args = sys.argv[1:]
    if len(args) < 4 or '--src' not in args or '-o' not in args:
        print(__doc__)
        return 1
    patch_path = args[0]
    src_path = args[args.index('--src') + 1]
    out_path = args[args.index('-o') + 1]

    patch = open(patch_path, 'rb').read()
    if patch[:12] != MAGIC:
        print(f"[错误] 补丁文件格式不正确 (magic {patch[:12]!r})")
        return 1
    src_size, dst_size = struct.unpack_from('<II', patch, 12)

    src_size_actual = os.path.getsize(src_path)
    if src_size_actual != src_size:
        print(f"[错误] 原版镜像大小不符: 期望 {src_size:,} 实际 {src_size_actual:,}")
        print("       本补丁仅适用于日版 Deep Freeze (SLPS-018.17) 原始镜像。")
        return 1

    data = bytearray(open(src_path, 'rb').read())
    pos = 20
    n_rec = 0
    while pos < len(patch):
        off, length = struct.unpack_from('<II', patch, pos)
        pos += 8
        data[off:off + length] = patch[pos:pos + length]
        pos += length
        n_rec += 1

    assert len(data) == dst_size, "输出大小校验失败"
    open(out_path, 'wb').write(bytes(data))
    print(f"已应用 {n_rec} 条差异记录 -> {out_path} ({len(data):,} bytes)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
