# -*- coding: utf-8 -*-
"""
dump_safs.py - 从原版镜像解出全部 SAF 资源包 (供 build_saf/import_text 使用)

用法:
  python dump_safs.py --bin "D:\\...\\Deep Freeze (Japan).bin" -o "D:\\...\\image file\\ARCHIVE"
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
    out_dir = args[args.index('-o') + 1]
    if not os.path.exists(bin_path):
        print(f"[错误] 找不到镜像: {bin_path}")
        return 1
    os.makedirs(out_dir, exist_ok=True)

    f = open(bin_path, 'rb')
    for safn, (lbn, size) in sorted(config.SAF_LBNS.items()):
        data = saf.iso_read_bytes(f, lbn, 0, size)
        out = os.path.join(out_dir, safn)
        open(out, 'wb').write(data)
        cnt = int.from_bytes(data[:4], 'little')
        print(f"  {safn:14s} LBN {lbn:>6d} {size:>9,d} bytes, {cnt} entries -> {out}")
    f.close()
    print(f"\n完成: {len(config.SAF_LBNS)} 个 SAF -> {out_dir}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
