# -*- coding: utf-8 -*-
"""
gen_font.py - 从 Windows GDI 宋体生成 12×12 2bpp 点阵字库 (参考脚本)

仅 Windows 可用 (ctypes + GDI)。输入 data/font/charset_used.txt,
输出 (默认写入 data/font/, 本参考版输出到当前目录以免覆盖仓库成品):
  KANJI.KPX   1228 字形 × 36B (12 行 × 3 字节, 2bpp)
  KANJI.TBL   1228 项 × 2B 自定义升序码 (lead 0x81-0x9F/0xE0-0xEF,
              trail 0x40-0x7E/0x80-0xFC, 排除 0x7F)
  char_code_map.json  字符 → [lead, trail]

流程: GDI GetGlyphOutlineW(GGO_BITMAP) 单色点阵 → 基线 y=10 对齐 →
水平居中 → 右下偏移阴影 (value 2) → 2bpp 打包。

重新生成字库前必须确认 charset_used.txt 与译文一致 (先跑
data/README.md 的"新增字符"流程)。输出注意: KPX 需补齐 256 倍数
才能进 SAF (build_saf.py 已自动处理)。

用法:  python reference/gen_font.py [--chars 字符集文件] [--out 输出目录]
"""
import ctypes
import json
import os
import struct
import sys
from ctypes import wintypes

sys.stdout.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------- 参数 ----------
CHARSET = os.path.join(REPO, "data", "font", "charset_used.txt")
OUT_DIR = "."
if '--chars' in sys.argv:
    CHARSET = sys.argv[sys.argv.index('--chars') + 1]
if '--out' in sys.argv:
    OUT_DIR = sys.argv[sys.argv.index('--out') + 1]
os.makedirs(OUT_DIR, exist_ok=True)

FONT_NAME = "宋体"        # SimSun
PP_EM = 12                # 字号
GLYPH = 12                # 画布
GLYPH_BYTES = 36          # 12 行 × 3 字节
BASELINE_Y = 10           # 12px 宋体基线经验值

# ---------- GDI ----------
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
GGO_BITMAP = 1


class POINTL(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class FIXED(ctypes.Structure):
    _fields_ = [("fract", wintypes.WORD), ("value", ctypes.c_short)]


class LOGFONTW(ctypes.Structure):
    _fields_ = [("lfHeight", ctypes.c_long), ("lfWidth", ctypes.c_long),
                ("lfEscapement", ctypes.c_long), ("lfOrientation", ctypes.c_long),
                ("lfWeight", ctypes.c_long), ("lfItalic", ctypes.c_byte),
                ("lfUnderline", ctypes.c_byte), ("lfStrikeOut", ctypes.c_byte),
                ("lfCharSet", ctypes.c_byte), ("lfOutPrecision", ctypes.c_byte),
                ("lfClipPrecision", ctypes.c_byte), ("lfQuality", ctypes.c_byte),
                ("lfPitchAndFamily", ctypes.c_byte),
                ("lfFaceName", ctypes.c_wchar * 32)]


class MAT2(ctypes.Structure):
    _fields_ = [("eM11", FIXED), ("eM12", FIXED),
                ("eM21", FIXED), ("eM22", FIXED)]


class GLYPHMETRICS(ctypes.Structure):
    _fields_ = [("gmBlackBoxX", ctypes.c_uint), ("gmBlackBoxY", ctypes.c_uint),
                ("gmptGlyphOrigin", POINTL),
                ("gmCellIncX", ctypes.c_short), ("gmCellIncY", ctypes.c_short)]


def _fixed(v):
    f = FIXED()
    f.value = v
    return f


def get_dc(ppem):
    hdc = user32.GetDC(0)
    lf = LOGFONTW()
    lf.lfHeight = -ppem
    lf.lfWeight = 400
    lf.lfCharSet = 1
    lf.lfFaceName = FONT_NAME
    hfont = gdi32.CreateFontIndirectW(ctypes.byref(lf))
    old = gdi32.SelectObject(hdc, hfont)
    return hdc, hfont, old


def glyph_mono(hdc, ch):
    """GDI 单色点阵 → (rows 0/1 二维数组, origin_x, origin_y)"""
    mat = MAT2(_fixed(1), _fixed(0), _fixed(0), _fixed(1))
    gm = GLYPHMETRICS()
    size = gdi32.GetGlyphOutlineW(hdc, ord(ch), GGO_BITMAP,
                                  ctypes.byref(gm), 0, None, ctypes.byref(mat))
    if size in (0xFFFFFFFF, 0, -1):
        return None, 0, 0
    buf = ctypes.create_string_buffer(size)
    if gdi32.GetGlyphOutlineW(hdc, ord(ch), GGO_BITMAP, ctypes.byref(gm),
                              size, buf, ctypes.byref(mat)) == 0xFFFFFFFF:
        return None, 0, 0
    rowbytes = (gm.gmBlackBoxX + 31) // 32 * 4
    rows = []
    for y in range(gm.gmBlackBoxY):
        row = []
        for x in range(gm.gmBlackBoxX):
            b = buf[y * rowbytes + (x >> 3)]
            b = b[0] if isinstance(b, bytes) else b
            row.append((b >> (7 - (x & 7))) & 1)
        rows.append(row)
    return rows, gm.gmptGlyphOrigin.x, gm.gmptGlyphOrigin.y


def place_glyph(rows, org_x, org_y):
    """放置到 12×12 画布 (基线对齐 + 水平居中)"""
    h = len(rows)
    w = len(rows[0]) if h else 0
    top = BASELINE_Y - org_y
    left = org_x
    if w < GLYPH:
        left = (GLYPH - w) // 2
    elif w > GLYPH:
        w = GLYPH
    grid = [[0] * GLYPH for _ in range(GLYPH)]
    for y in range(h):
        gy = top + y
        if not (0 <= gy < GLYPH):
            continue
        for x in range(min(w, len(rows[y]))):
            gx = left + x
            if 0 <= gx < GLYPH and rows[y][x]:
                grid[gy][gx] = 1
    return grid


def add_shadow(grid):
    """右下偏移阴影 (value 2)"""
    res = [row[:] for row in grid]
    for y in range(GLYPH):
        for x in range(GLYPH):
            if grid[y][x] == 1:
                sx, sy = x + 1, y + 1
                if 0 <= sx < GLYPH and 0 <= sy < GLYPH \
                        and grid[sy][sx] == 0 and res[sy][sx] == 0:
                    res[sy][sx] = 2
    return res


def grid_to_bytes(grid):
    data = bytearray(GLYPH_BYTES)
    for y in range(GLYPH):
        for x in range(GLYPH):
            data[y * 3 + (x >> 2)] |= grid[y][x] << (2 * (x & 3))
    return bytes(data)


def generate_codes(n):
    leads = list(range(0x81, 0xA0)) + list(range(0xE0, 0xF0))
    trails = list(range(0x40, 0x7F)) + list(range(0x80, 0xFD))   # 无 0x7F
    codes = []
    for lead in leads:
        for trail in trails:
            codes.append((lead, trail))
            if len(codes) >= n:
                return codes
    return codes


def main():
    chars = open(CHARSET, encoding='utf-8').read().strip()
    print(f"字符集: {len(chars)} 字 ({CHARSET})")
    codes = generate_codes(len(chars))
    assert len(codes) == len(chars), "码点空间不足"

    hdc, hfont, old = get_dc(PP_EM)
    kpx = bytearray()
    tbl = bytearray()
    ok = 0
    fail = []
    for i, ch in enumerate(chars):
        lead, trail = codes[i]
        tbl += struct.pack('<H', lead | (trail << 8))
        rows, ox, oy = glyph_mono(hdc, ch)
        if rows:
            ok += 1
            grid = place_glyph(rows, ox, oy)
        else:
            fail.append((i, ch, f"U+{ord(ch):04X}"))
            grid = [[0] * GLYPH for _ in range(GLYPH)]
        kpx += grid_to_bytes(add_shadow(grid))
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(chars)}")
    gdi32.SelectObject(hdc, old)
    gdi32.DeleteObject(hfont)
    user32.ReleaseDC(0, hdc)

    open(os.path.join(OUT_DIR, "KANJI.KPX"), 'wb').write(bytes(kpx))
    open(os.path.join(OUT_DIR, "KANJI.TBL"), 'wb').write(bytes(tbl))
    mapping = {ch: list(codes[i]) for i, ch in enumerate(chars)}
    json.dump(mapping, open(os.path.join(OUT_DIR, "char_code_map.json"), 'w',
                            encoding='utf-8'), ensure_ascii=False)

    print(f"KPX: {len(kpx)} B ({len(kpx)//GLYPH_BYTES} 字形)")
    print(f"TBL: {len(tbl)} B ({len(tbl)//2} 项)")
    print(f"GDI 成功: {ok}/{len(chars)}")
    if fail:
        print(f"失败 (空白字形兜底): {fail[:10]} ...")
    print(f"\n输出目录: {os.path.abspath(OUT_DIR)}")


if __name__ == '__main__':
    main()
