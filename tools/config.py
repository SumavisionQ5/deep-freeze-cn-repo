# -*- coding: utf-8 -*-
"""
config.py - 工具链路径与关键常量配置

用户配置区: 只需修改 GAME_DIR 指向包含以下文件的原版日版目录:
  Deep Freeze (Japan).bin / .cue          原始镜像 (TRACK 01 MODE2/2352)
  SLPS_018.17                             原版主程序 EXE
  ARCHIVE/*.SAF                           从镜像解包出的资源包 (或保留默认路径)

其余常量为游戏内定值，除非重制补丁否则不要修改。
"""
import os

# ============ 用户配置区 ============
# 原版日版游戏所在目录 (含 .bin/.cue; 若已解包 SAF 则含 ARCHIVE 子目录)
GAME_DIR = r"D:\DeepFreeze汉化"

# 原版 BIN 文件名
SRC_BIN = os.path.join(GAME_DIR, "Deep Freeze (Japan).bin")

# ============ 派生路径 ============
AD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 仓库根
ARCHIVE = os.path.join(GAME_DIR, "image file", "ARCHIVE")          # 原版 SAF 解包目录
SRC_EXE = os.path.join(GAME_DIR, "image file", "SLPS_018.17")      # 原版 EXE
BUILD_DIR = os.path.join(AD, "build")                              # 构建输出 (gitignore)

# 仓库内数据
DATA_DIR = os.path.join(AD, "data")
PATCHES_DIR = os.path.join(AD, "patches")
FONT_DIR = os.path.join(DATA_DIR, "font")
TRANS_DIR = os.path.join(DATA_DIR, "translation")

# ============ 游戏格式常量 (勿改) ============
# 主程序 EXE 装载基址 (t_addr - BASE_LOAD = 文件偏移)
BASE_LOAD = 0x8000F800

# EXE 在 ISO 中的 LBN (原版定值; find_exe_lbn 会复核)
EXE_LBN = 24

# SAF 在 ISO 中的 LBN 与字节数 (来自镜像目录解析, 见 data/original/saf_lbn.json)
SAF_LBNS = {
    'RAF1.SAF':     (229,   18286592),
    'RAF2.SAF':     (9158,  11343872),
    'RAF3.SAF':     (14697,  8828928),
    'RAF4.SAF':     (19008,  7968768),
    'RAF5.SAF':     (22899,  5365760),
    'OVERLAY.SAF':  (25519,  247808),
    'MODEL.SAF':    (25640,  960512),
    'MOTION.SAF':   (26109,  911360),
    'MENU1.SAF':    (26554,  462848),
    'MENU2.SAF':    (26780,  335872),
    'MENU3.SAF':    (26944,  395264),
    'MENU4.SAF':    (27137,  309248),
    'MENU5.SAF':    (27288,  280576),
    'SYSTEM.SAF':   (27425,  505856),
    'COMPUTER.SAF': (27672,  174080),
    'SOUND.SAF':    (27757,  1718272),
    'STAFFROL.SAF': (28596,  1308672),
    'TOPMENU.SAF':  (29235,  266240),
}

# 本汉化涉及的 SAF (其余资源包不含文本)
TEXT_SAFS = ['MENU1.SAF', 'MENU2.SAF', 'MENU3.SAF', 'MENU4.SAF', 'MENU5.SAF', 'OVERLAY.SAF']

# SYSTEM.SAF 内字库条目名
KPX_NAME = '*KANJI.KPX'
TBL_NAME = 'KANJI.TBL'

# 汉化字体规格: 12x12 2bpp, 36B/字形
GLYPH_BYTES = 36
