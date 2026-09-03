# -*- coding: utf-8 -*-
"""
make_patch.py - 生成二进制差异补丁文件 (原版 BIN → 汉化 BIN)

逐 2352 字节原始扇区比对原版与汉化镜像, 输出 RLE 风格的差异记录:
  header  "DFCNPATCH001" (12B) + u32 原版大小 + u32 汉化大小
  记录    u32 偏移 + u32 数据长度 + 数据本体 (只记录差异扇区内差异段落,
          差异段落先按 32B 块聚簇以减少记录数)

汉化镜像中变化的用户数据集中在: EXE 扇区、SYSTEM.SAF、MENU1-5/OVERLAY 六个
SAF 的修改文件扇区; 音轨 (TRACK 02+) 与图形资源不变化。
 BIN 与 BIN 比对可跨轨道直接按字节进行 (音频轨原样保留)。

用法:
  python make_patch.py --src 原版.bin --dst 汉化.bin -o deep-freeze-cn.bpatch
  python apply_patch.py deep-freeze-cn.bpatch --src 原版.bin -o 汉化.bin
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

sys.stdout.reconfigure(encoding='utf-8')

MAGIC = b"DFCNPATCH001"
CLUSTER = 32          # 差异聚簇粒度 (字节)
MAX_RUN = 0xFFFF      # 单条记录最大数据长度


def diff_records(src: bytes, dst: bytes):
    """生成差异记录 [(offset, bytes)]"""
    assert len(src) == len(dst), f"镜像大小不一致: {len(src)} vs {len(dst)}"
    recs = []
    i = 0
    n = len(src)
    while i < n:
        if src[i] != dst[i]:
            # 向前扩展到 CLUSTER 边界, 向后聚簇
            start = i - (i % CLUSTER)
            j = i
            last_diff = i
            while j < n and (j - start) < MAX_RUN:
                if src[j] != dst[j]:
                    last_diff = j
                j += 1
                # 找到一段 >=64B 的连续相同区即可提前收尾
                if j - last_diff >= 64:
                    break
            end = min(n, last_diff + 1)
            end += (-end % CLUSTER) if (end % CLUSTER) else 0
            end = min(end, n)
            recs.append((start, dst[start:end]))
            i = end
        else:
            i += 1
    return recs


def write_patch(recs, src_size, dst_size, path):
    with open(path, 'wb') as f:
        f.write(MAGIC)
        f.write(struct.pack('<II', src_size, dst_size))
        for off, data in recs:
            f.write(struct.pack('<II', off, len(data)))
            f.write(data)


def main():
    args = sys.argv[1:]
    if '-o' not in args or '--src' not in args or '--dst' not in args:
        print(__doc__)
        return 1
    src = open(args[args.index('--src') + 1], 'rb').read()
    dst = open(args[args.index('--dst') + 1], 'rb').read()
    out = args[args.index('-o') + 1]

    recs = diff_records(src, dst)
    write_patch(recs, len(src), len(dst), out)
    size = os.path.getsize(out)
    print(f"差异记录: {len(recs)} 条")
    print(f"补丁文件: {out} ({size:,} bytes = {size/1024/1024:.1f} MB)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
