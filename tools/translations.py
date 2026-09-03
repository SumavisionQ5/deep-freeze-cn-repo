# -*- coding: utf-8 -*-
"""
translations.py - 译文加载 (TR1+TR2+TR3+TR4 合并)

译文以 Python 字典模块存放在 data/translation/，键为 skel_all.tsv 的行号。
新增/修改译文只需编辑对应 trans_pN.py 文件。
"""
import importlib.util
import os

TRANS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "translation")

_FP_LINES = {442, 1191}   # 假阳性行 (原文为乱码, 保留日文不翻译)


def load_translations():
    """加载全部译文, 返回 {行号: 译文}; 行号重复时报错"""
    mods = []
    for i in (1, 2, 3, 4):
        p = os.path.join(TRANS_DIR, f"trans_p{i}.py")
        spec = importlib.util.spec_from_file_location(f"df_trans_p{i}", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        mods.append(getattr(m, f"TR{i}"))
    all_tr = {}
    for tr in mods:
        for k, v in tr.items():
            if k in all_tr:
                raise ValueError(f"译文行号重复: {k}")
            all_tr[k] = v
    return all_tr


def false_positive_lines():
    return set(_FP_LINES)
