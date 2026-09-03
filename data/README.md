---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '572dffce-20f7-46d7-a93d-5421eddc451c'
  PropagateID: '572dffce-20f7-46d7-a93d-5421eddc451c'
  ReservedCode1: '53b2a4bc-e232-4fb0-8e0f-fecd0161c237'
  ReservedCode2: '53b2a4bc-e232-4fb0-8e0f-fecd0161c237'
---

# data/ 目录说明

本目录存放汉化工程的全部数据资产：从原盘提取的日文文本、全部中文译文、
自制字库与码表。这些文件是工具链的输入/输出，也是翻译工作的核心记录。

```
data/
├── original/            从原版日版镜像提取的原始数据
│   ├── text_extract.csv 全部日文文本 (1274+ 条带原文 hex; 另含
│   │                    STAFFROL/TOPMENU/EXE 等 5459 行粗提取候选)
│   ├── skel_all.tsv     翻译骨架表 (行号 → 文件/偏移/缩进/换行数/原文)
│   ├── saf_lbn.json     全部 SAF 资源包在 ISO 中的 LBN 与大小
│   └── blocks_info.json 各 .B 文件的块表结构
├── translation/         中文译文 (键 = skel_all.tsv 行号)
│   ├── translation_all.tsv 中日对照总表 (line/file/off/原文/译文,
│   │                    浏览与审校用，导入器不读取)
│   ├── trans_p1.py      批 1: 菜单 + 任务简报等 (1-421)
│   ├── trans_p2.py      批 2: 剧情对话 (422-878)
│   ├── trans_p3.py      批 3: 对话 + 系统文本 (879-1238)
│   └── trans_p4.py      批 4: 遗漏补全 (1239-1274)
└── font/                自制字库
    ├── charset_used.txt 项目字符集 (1228 字, 按码点顺序)
    ├── char_code_map.json 字符 → [lead, trail] 码点映射
    ├── KANJI.KPX        12x12 2bpp 点阵字库 (36B/字形, 1228 字形)
    ├── KANJI.TBL        自定义升序码表 (1228 项)
    └── new_font_preview.png 字库预览图 (前 100 字)
```

## 译文文件格式

工具链读取的是 `trans_p1.py` ~ `trans_p4.py` 四个 Python 字典模块；
`translation_all.tsv` 是由它们生成的**中日对照总表** (1274 行)，
适合人工浏览与审校，导入器不读取。如需改译文，请改 `trans_pN.py`
后重新构建镜像；改动后可用 `python tools/gen_bilingual.py`
重新生成总表 (或 `--check` 仅校验覆盖)。

每个 `trans_pN.py` 是一个 Python 字典模块：

```python
TR1 = {
    1: "人质信息",        # 行号 1 ← skel_all.tsv 行号 1 (人質情報)
    2: "人质数量",        # ← 人質の数
    ...
}
```

约束 (导入器会强制校验，违规条目跳过并警告)：

1. **换行**：用 `|` 分段，段数必须与原文一致 (`skel_all.tsv` 的 `nl` 列)
2. **长度**：译文编码后字节数 ≤ 原文字节数 + 其后零填充 (一般即"每字 2 字节、
   不超过原文 SJIS 字节数")
3. **字符**：全部字符必须在 `data/font/char_code_map.json` 码表中
   (新增字符需重新生成字库，见 HACKING.md)
4. **缩进**：原文行首全角空格 (IND=1) 应保留，属排版设计

## 修改译文后重新生成镜像

```bash
cd tools
python import_text.py --check          # 校验译文 (不写盘)
python build_iso.py                    # 重新构建完整镜像
python verify.py --bin ../build/"Deep Freeze (Japan) patched.bin"
```

或者只更新已有镜像 (不重建 EXE/字库部分)：

```bash
python import_text.py --bin "path/to/patched.bin"
```

> AI生成