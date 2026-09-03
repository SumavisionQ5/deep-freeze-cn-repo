---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'a39fc8ab-2fe5-4b34-ad4a-6df2c2cd6a6e'
  PropagateID: 'a39fc8ab-2fe5-4b34-ad4a-6df2c2cd6a6e'
  ReservedCode1: '176624a4-82fb-4429-8ea7-ddaafdc87790'
  ReservedCode2: '176624a4-82fb-4429-8ea7-ddaafdc87790'
---

# Deep Freeze 简体中文汉化项目 (SLPS-018.17)

[English](README_EN.md) | 简体中文

对 Microcabin 1996 年 PS1 救援动作游戏《**Deep Freeze**》(ディープフリーズ，
日版 SLPS-018.17) 的**完整简体中文汉化**。

- **1272 条译文**：任务简报、武器/道具说明、全部剧情对话、电脑终端、
  教学模式、排行榜、结局制作人员名单等，覆盖游戏全部可提取文本
- **1228 字自制字库**：宋体 12px 点阵 (12×12, 2bpp)，替换原版 16×15 日文字库
- **12 处 MIPS 补丁**：适配新字体渲染，无代码注入，不移动任何资源
- **全链路校验**：EXE 补丁、字库、码表、全部译文回读比对通过

> ⚠️ 本仓库**不包含**任何游戏原始资源 (镜像/EXE/SAF 资源包)。
> 使用需自备合法获得的原版日版镜像。游戏版权归 Microcabin 所有。

---

## 快速开始 (玩家)

### 方式一：应用差异补丁 (推荐)

补丁文件 [`patches/deep-freeze-cn.bpatch`](patches/) 仅 **425 KB**，
将原版镜像逐字节转换为汉化镜像：

```bash
python tools/apply_patch.py patches/deep-freeze-cn.bpatch ^
    --src "你的路径\Deep Freeze (Japan).bin" ^
    -o   "Deep Freeze (Japan) patched.bin"
```

### 方式二：下载成品镜像

见 Release 页 (如已发布)。成品镜像 MD5 校验值随版本记录于 CHANGELOG。

### 运行

用 ePSXe / DuckStation / Mednafen / PocketStation 等加载生成的
`patched.bin` + `patched.cue` (含 6 条音轨，请用 .cue 加载)。

**原版镜像校验**：仅支持未修改日版原盘
(MD5 `DF51A6E8BEF1055A22AC2FAED9D9E015`，495,531,120 字节)。

---

## 从源码构建 (汉化者)

### 环境准备

1. Windows + Python 3.8+ (无第三方依赖)
2. 原版日版镜像 `Deep Freeze (Japan).bin/.cue`
3. 修改 `tools/config.py` 中 `GAME_DIR` 指向游戏目录

### 一键构建

```bash
# 解出原版 EXE 与 SAF 资源包 (一次性)
python tools/dump_exe.py  --bin "D:\你的游戏目录\Deep Freeze (Japan).bin" ^
    -o "D:\你的游戏目录\image file\SLPS_018.17"
python tools/dump_safs.py --bin "D:\你的游戏目录\Deep Freeze (Japan).bin" ^
    -o "D:\你的游戏目录\image file\ARCHIVE"

# 构建 + 导入译文 + 校验
cd tools
python build_all.py
```

产出 `build/Deep Freeze (Japan) patched.bin` + `.cue`，并自动执行全量
校验 (EXE 12 补丁点、字库 256 对齐、SCRIPT.B 字体路径、1272 条译文回读)。

### 修改译文

译文位于 [`data/translation/`](data/translation/)，按行号对应
[`data/original/skel_all.tsv`](data/original/) 的日文原文。
编辑后：

```bash
python tools/import_text.py --check   # 校验 (不写盘)
python tools/build_iso.py             # 重建镜像
python tools/verify.py                # 全量校验
```

翻译规范 (导入器强制执行)：译文不超过原文 1.2 倍、`|` 分段数一致、
行首缩进保留、字符必须在码表中。详见 [data/README.md](data/README.md)。

---

## 仓库结构

```
deep-freeze-cn/
├── README.md / README_EN.md      本文件
├── CHANGELOG.md                  版本历史 (v1-v8)
├── LICENSE                       许可证 (代码/文档/译文分开授权)
├── tools/                        全套工具链 (Python, 见 tools/README.md)
│   ├── config.py                 路径与常量配置
│   ├── saf.py                    LZSS + SAF + ISO 底层库
│   ├── import_text.py            文本一键导入器 (核心)
│   ├── build_all.py              一键构建
│   ├── verify.py                 全量校验
│   ├── make_patch.py / apply_patch.py  差异补丁生成/应用
│   └── ...
├── data/
│   ├── original/                 日文原文提取结果 (text_extract.csv / skel_all.tsv)
│   ├── translation/              中文译文 trans_p1-p4.py
│   └── font/                     自制字库 KPX/TBL + 码表 + 字符集
├── patches/
│   └── deep-freeze-cn.bpatch     原版 → 汉化 差异补丁 (425 KB)
├── docs/
│   ├── HACKING.md                破解技术文档 (中文, 详细)
│   └── HACKING_EN.md             技术文档 (English)
└── reference/                    字形生成器等参考脚本 (Windows GDI)
```

---

## 文档

| 文档 | 内容 |
|------|------|
| [docs/HACKING.md](docs/HACKING.md) | 完整破解文档：镜像/SAF/字库格式、码页设计、12 处 MIPS 补丁、空间管理、三大坑 (黑屏/缺字/空白) 与调试方法 |
| [docs/HACKING_EN.md](docs/HACKING_EN.md) | English version |
| [tools/README.md](tools/README.md) | 工具链用法 |
| [data/README.md](data/README.md) | 数据文件格式与翻译规范 |
| [CHANGELOG.md](CHANGELOG.md) | v1→v8 修复史 (黑屏/缺字/tutorial 空白/空格) |

---

## 技术亮点 (速览)

- **SAF 目录的 256 对齐陷阱**：游戏按 `entry[11]<<16|entry[15]<<8|entry[19]`
  计算解压大小，低字节恒为 0 → 所有被读文件必须 256 字节对齐，否则开机黑屏
- **0x7F 码位陷阱**：SJIS trail 0x7F 非法，v7 的 7 个码位踩雷导致整字丢失
- **双字体加载路径**：教学模式走 SCRIPT.B 硬编码的 KANJI2 路径，
  必须等长替换字符串补丁 (`*KANJI2.KPX`→`*KANJI.KPX`)
- **16×15→12×12 渲染适配**：stride、VRAM 搬运、行高、精灵尺寸等
  12 处硬编码的系统性修改
- 完整过程与调试方法见 HACKING.md

## 致谢

- 字形：Windows GDI + 中易宋体 (SimSun) 点阵提取
- 调试：ePSXe 1.6/savestate、capstone 反汇编
- 感谢所有 PS1 同人汉化先驱者的公开资料

## 许可

见 [LICENSE](LICENSE)：工具与文档 MIT / 译文与字库 CC BY-NC-SA 4.0 /
补丁文件仅限合法持有原版者使用。

> AI生成