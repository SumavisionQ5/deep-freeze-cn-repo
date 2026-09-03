# -*- coding: utf-8 -*-
"""
dump_exe.py - 从原版镜像解出主程序 EXE (SLPS_018.17)

用法:
  python dump_exe.py --bin "D:\\...\\Deep Freeze (Japan).bin" -o "D:\\...\\image file\\SLPS_018.17"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import saf

sys.stdout.reconfigure(encoding='utf-8')


def main():
    args = sys.argv[1:]
    if '--bin' not in args or '-o' not in args:
        print(__doc__)
        return 1
    bin_path = args[args.index('--bin') + 1]
    out_path = args[args.index('-o') + 1]
    if not os.path.exists(bin_path):
        print(f"[错误] 找不到镜像: {bin_path}")
        return 1

    bin_data = open(bin_path, 'rb').read()
    exe_lbn = saf.find_exe_lbn(bin_data)
    if exe_lbn is None:
        print("[错误] 找不到 'PS-X EXE' 魔数")
        return 1

    # EXE 大小: 读头部 u32 (0x18 处, 文件大小), 向上取整到扇区
    f = open(bin_path, 'rb')
    head = saf.iso_read_bytes(f, exe_lbn, 0, 2048)
    exe_size = struct_unpack(head)
    data = saf.iso_read_bytes(f, exe_lbn, 0, exe_size)
    f.close()

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    open(out_path, 'wb').write(data)
    print(f"EXE LBN {exe_lbn}, {exe_size:,} bytes -> {out_path}")
    return 0


def struct_unpack(head):
    import struct as _s
    t_size = _s.unpack_from('<I', head, 0x1C)[0]   # t_size = 加载大小
    # 文件实际大小一般等于 0x800 + t_size, 但 SLPS_018.17 头部 0x800 后即代码
    return 0x800 + t_size if t_size else len(head)


if __name__ == '__main__':
    sys.exit(main())
