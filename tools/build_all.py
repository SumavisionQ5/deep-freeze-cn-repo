# -*- coding: utf-8 -*-
"""
build_all.py - 一键构建完整汉化镜像

等价于依次执行:
  1. python apply_patches.py   # EXE 12 处 MIPS 补丁
  2. python build_saf.py       # 生成补丁 SYSTEM.SAF (字库/码表)
  3. python build_iso.py       # 组装镜像 + 导入全部译文 + 生成 CUE
  4. python verify.py          # 全量校验 (EXE/字库/SCRIPT.B/译文回读)

前置条件 (见 README.md「环境准备」):
  * Windows + Python 3.8+
  * tools/config.py 中 GAME_DIR 指向原版日版游戏目录
  * 原版 SAF 已解包到 GAME_DIR/image file/ARCHIVE/ (或已设置好路径)

用法:
  python build_all.py
"""
import subprocess
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
AD = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ("apply_patches.py", "EXE MIPS 补丁"),
    ("build_saf.py", "SYSTEM.SAF 字库构建"),
    ("build_iso.py", "镜像组装与译文导入"),
    ("verify.py", "全量校验"),
]


def main():
    for script, desc in STEPS:
        print("#" * 60)
        print(f"# STEP: {desc} ({script})")
        print("#" * 60)
        r = subprocess.call([sys.executable, os.path.join(AD, script)])
        if r != 0:
            print(f"\n[失败] {desc} 返回 {r}, 构建中止")
            return r
        print()
    print("全部步骤完成。镜像位于 build/ 目录。")
    return 0


if __name__ == '__main__':
    sys.exit(main())
