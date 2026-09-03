# -*- coding: utf-8 -*-
"""
saf.py - Deep Freeze (SLPS-018.17) 资源包格式与 ISO 底层操作库

发布于 https://github.com/<user>/deep-freeze-cn (tools/saf.py)
本文件是汉化工具链的公共底层库，提供:
  * LZSS 压缩/解压 (与游戏内实现字节兼容)
  * SAF 资源包目录解析 (20 字节定长目录项)
  * MODE2/2352 原始镜像的扇区读写 (用户数据位于 +24)

所有偏移/扇区号均针对日版原盘 (TRACK 01 MODE2/2352, 2352 字节/扇区,
用户数据 2048 字节, 偏移 +24)。游戏资源包 SAF 目录项结构 (20 字节):
  [0..10]  文件名 (NUL 终止, 可能带 '*' 前缀)
  [11]     解压大小高位字节 (与 entry[15], entry[19] 组成 24bit 大小)
  [12..13] 数据起始扇区 (u16, 单位 2048B, 相对 SAF 起始)
  [14..15] 解压大小低 16bit (u16 LE)
  [16..17] 压缩数据长度 clen (u16 LE)
  [18]     保留
  [19]     解压大小最低字节
游戏按 entry[11]<<16 | entry[15]<<8 | entry[19] 计算解压大小 (详见 docs/HACKING.md)
"""
import struct

SECTOR = 2352          # 原始扇区大小
USER_OFF = 24          # MODE2 用户数据偏移
USER_SIZE = 2048       # 用户数据大小


# ---------------------------------------------------------------- LZSS ----
def lzss_decompress(src: bytes) -> bytes:
    """游戏同款 LZSS 变体解压 (4KB 环形缓冲, 初始写位置 0xFEE, 匹配长 3-18)"""
    ring = bytearray(4096)
    w = 0xFEE
    out = bytearray()
    pos = 0
    n = len(src)
    while pos < n:
        flag = src[pos]
        pos += 1
        for b in range(8):
            if pos >= n:
                break
            if (flag >> b) & 1:
                c = src[pos]
                pos += 1
                out.append(c)
                ring[w] = c
                w = (w + 1) & 0xFFF
            else:
                if pos + 1 >= n:
                    break
                t0, t1 = src[pos], src[pos + 1]
                pos += 2
                r = t0 | ((t1 & 0xF0) << 4)
                length = (t1 & 0xF) + 3
                for i in range(length):
                    c = ring[(r + i) & 0xFFF]
                    out.append(c)
                    ring[w] = c
                    w = (w + 1) & 0xFFF
    return bytes(out)


def lzss_compress(data: bytes) -> bytes:
    """与游戏解压器字节兼容的 LZSS 压缩器 (贪婪匹配, 512 深度候选链)"""
    from collections import defaultdict, deque

    n = len(data)
    out = bytearray()
    idx = defaultdict(deque)
    i = 0
    cur_flag = 0
    cur_units = []
    bitpos = 0

    def flush_group():
        nonlocal cur_flag, cur_units, bitpos
        out.append(cur_flag)
        for u in cur_units:
            if u[0]:
                out.append(u[1])
            else:
                r, length = u[1], u[2]
                out.append(r & 0xFF)
                out.append(((r >> 4) & 0xF0) | (length - 3))
        cur_flag = 0
        cur_units = []
        bitpos = 0

    while i < n:
        best_len = 0
        best_j = -1
        if i + 3 <= n:
            cands = idx.get(data[i])
            if cands:
                tried = 0
                for j in reversed(cands):
                    if tried > 512:
                        break
                    tried += 1
                    if i - j > 4093:
                        break
                    length = 0
                    while length < 18 and i + length < n:
                        if data[j + length] == data[i + length]:
                            length += 1
                        else:
                            break
                    if length > best_len:
                        best_len = length
                        best_j = j
                        if length == 18:
                            break
        if best_len >= 3:
            r = (0xFEE + best_j) & 0xFFF
            cur_units.append((False, r, best_len))
            cur_flag |= (0 << bitpos)
            for k in range(best_len):
                idx[data[i + k]].append(i + k)
            i += best_len
        else:
            c = data[i]
            cur_units.append((True, c))
            cur_flag |= (1 << bitpos)
            idx[c].append(i)
            i += 1
        bitpos += 1
        if bitpos == 8:
            flush_group()
    if bitpos > 0:
        flush_group()
    return bytes(out)


# ------------------------------------------------------------- SAF 目录 ----
class SafEntry:
    """SAF 目录中的一个文件条目"""
    __slots__ = ('index', 'name', 'raw_name', 'sector', 'decomp_size', 'clen', 'dir_off')

    def __init__(self, index, raw):
        self.index = index
        self.dir_off = 4 + index * 20
        self.raw_name = raw[:11]
        self.name = raw[:11].split(b'\x00')[0].split(b' ')[0].decode('ascii', 'replace')
        self.sector = raw[12] | (raw[13] << 8)
        self.decomp_size = (raw[11] << 16) | (raw[15] << 8) | raw[19]
        self.clen = raw[16] | (raw[17] << 8)

    def game_size(self):
        """游戏实际计算的解压大小 (entry[11]<<16|entry[15]<<8|entry[19])"""
        return self.decomp_size

    def __repr__(self):
        return f"<SafEntry {self.name!r} sector={self.sector} clen={self.clen} dsz={self.decomp_size:#x}>"


def saf_entries(data: bytes):
    """解析 SAF 目录, 返回 [SafEntry]"""
    cnt = struct.unpack_from('<I', data, 0)[0]
    es = []
    for k in range(cnt):
        es.append(SafEntry(k, data[4 + k * 20:4 + k * 20 + 20]))
    return es


def find_entry(es, name: str):
    """按文件名查找条目 (忽略 '*' 前缀)"""
    want = name.lstrip('*').upper()
    for e in es:
        if e.name.lstrip('*').upper() == want:
            return e
    return None


# ------------------------------------------------------------- ISO I/O ----
def iso_write_bytes(f, start_lbn: int, file_offset: int, data: bytes):
    """向 BIN 中 start_lbn 起的连续逻辑文件区域写入数据 (跨扇区, MODE2/2352)"""
    nsec = (len(data) + USER_SIZE - 1) // USER_SIZE
    for i in range(nsec):
        chunk = data[i * USER_SIZE:(i + 1) * USER_SIZE]
        if len(chunk) < USER_SIZE:
            chunk = chunk + b'\x00' * (USER_SIZE - len(chunk))
        f.seek((start_lbn + i) * SECTOR + USER_OFF)
        f.write(chunk)


def iso_read_bytes(f, start_lbn: int, file_offset: int, length: int) -> bytes:
    """从 BIN 中 start_lbn 起的连续逻辑文件区域读取数据 (跨扇区, MODE2/2352)"""
    data = b''
    remaining = length
    cur_off = file_offset
    while remaining > 0:
        sec_idx = cur_off // USER_SIZE
        in_sec = cur_off % USER_SIZE
        chunk_len = min(USER_SIZE - in_sec, remaining)
        f.seek((start_lbn + sec_idx) * SECTOR + USER_OFF + in_sec)
        data += f.read(chunk_len)
        cur_off += chunk_len
        remaining -= chunk_len
    return data


def find_exe_lbn(bin_data: bytes):
    """在 BIN 中搜索 'PS-X EXE' 扇区定位主程序 (返回 LBN)"""
    magic = b'PS-X EXE'
    for s in range(len(bin_data) // SECTOR + 1):
        off = s * SECTOR + USER_OFF
        if off + 8 > len(bin_data):
            break
        if bin_data[off:off + 8] == magic:
            return s
    return None
