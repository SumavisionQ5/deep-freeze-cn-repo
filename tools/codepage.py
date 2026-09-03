# -*- coding: utf-8 -*-
"""
codepage.py - 自定义码页 (1228 字) 编解码

码表由 data/font/char_code_map.json (字符 → [lead, trail]) 定义:
  * lead:  0x81-0x9F, 0xE0-0xEF  (与游戏 lead 合法性判定兼容)
  * trail: 0x40-0x7E, 0x80-0xFC  (排除 0x7F, 与 SJIS trail 合法性判定兼容)
  * '|'    → 0x7C 单字节 (游戏内为换行符)
码点按 TBL 升序分配, 前 1221 个码位自项目早期保持稳定。
"""
import json
import os

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "font")
CCM_PATH = os.path.join(FONT_DIR, "char_code_map.json")


def load_codepage():
    """返回 {字符: (lead, trail)}"""
    ccm = json.load(open(CCM_PATH, encoding='utf-8'))
    return {ch: (codes[0], codes[1]) for ch, codes in ccm.items()}


def encode_text(text: str, ccm: dict) -> bytes:
    """用自定义码页编码译文; '|' → 0x7C (1 字节), 其余每字 2 字节"""
    out = bytearray()
    for ch in text:
        if ch == '|':
            out.append(0x7C)
        elif ch in ccm:
            lead, trail = ccm[ch]
            out.append(lead)
            out.append(trail)
        else:
            raise ValueError(f"字符不在码表中: U+{ord(ch):04X} '{ch}'")
    return bytes(out)


def decode_text(data: bytes, offset: int, max_len: int, rev_ccm: dict) -> str:
    """从 data[offset:] 解码文本直到 0x00; rev_ccm 为 {(lead,trail): 字符}"""
    out = []
    i = offset
    end = min(offset + max_len, len(data))
    while i < end:
        b0 = data[i]
        if b0 == 0:
            break
        if b0 in (0x7C, 0x0A):
            out.append('|')
            i += 1
        elif 0x20 <= b0 <= 0x7E:
            out.append(chr(b0))
            i += 1
        elif i + 1 < end:
            ch = rev_ccm.get((b0, data[i + 1]))
            out.append(ch if ch else f'[?{b0:02X}{data[i + 1]:02X}]')
            i += 2
        else:
            break
    return ''.join(out)
