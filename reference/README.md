---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '157a468f-c7af-4e4a-b077-efda70508d3a'
  PropagateID: '157a468f-c7af-4e4a-b077-efda70508d3a'
  ReservedCode1: 'fcb152fd-bd77-408d-b5f8-c5e8da269aa8'
  ReservedCode2: 'fcb152fd-bd77-408d-b5f8-c5e8da269aa8'
---

# reference/ 目录说明

非必需的参考脚本 — 工具链日常构建不需要它们，但在特定场景有用：

| 文件 | 用途 |
|------|------|
| `gen_font.py` | 从 Windows GDI 宋体重新生成点阵字库 (12×12 2bpp)。只有**新增汉字**时才需要：编辑 `data/font/charset_used.txt` → 运行本脚本 → 用新字库走 build_saf。需要 Windows + 中易宋体，输出默认到当前目录避免覆盖仓库成品。 |

## 何时需要重新生成字库

1. 译文引入了 `char_code_map.json` 中没有的新字符；
2. 想更换字体或调整点阵效果（改 `FONT_NAME` / `PP_EM` / `BASELINE_Y`）。

流程 (详见 docs/HACKING.md 第 5、7 节)：

```bash
# 1. 补字符集: 把新字符加入 data/font/charset_used.txt (保持排序)
# 2. 重新生成字库/码表/码表 JSON
python reference/gen_font.py --out .temp_font
# 3. 核对输出无误后替换 data/font/{KANJI.KPX, KANJI.TBL, char_code_map.json}
# 4. 走完整构建
python tools/build_all.py
```

注意：

- 码点由 `generate_codes()` 按字符集顺序升序分配；**在中间插入字符
  会改变后续所有码位**，使已写盘译文失效。新字符一律追加到文件末尾。
- trail 0x7F 永远不可用 (游戏判定非法)。
- 字库 KPX 需 256 字节对齐才能进 SAF —— `tools/build_saf.py` 已自动
  补齐，无需手动处理。

> AI生成