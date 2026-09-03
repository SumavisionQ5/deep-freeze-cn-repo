---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '97af09ee-08ff-434f-bc41-82eadc5138c0'
  PropagateID: '97af09ee-08ff-434f-bc41-82eadc5138c0'
  ReservedCode1: '2e858306-6a60-4f09-9031-c6db97d1b21b'
  ReservedCode2: '2e858306-6a60-4f09-9031-c6db97d1b21b'
---

# tools/ 目录说明 — 汉化工具链

全部工具为 Python 3 脚本 (仅标准库，无第三方依赖)，Windows 下开发测试
(Python 3.12)，理论上跨平台。

```
tools/
├── config.py          全局路径与游戏格式常量 (用户唯一需要修改的文件)
├── saf.py             底层库: LZSS 压缩/解压 + SAF 目录解析 + ISO 扇区读写
├── codepage.py        自定义码页编解码 (1228 字)
├── translations.py    译文加载 (trans_p1-4 合并)
│
├── dump_exe.py        从原版 BIN 解出主程序 SLPS_018.17
├── dump_safs.py       从原版 BIN 解出全部 SAF 资源包
├── gen_data.py        从原盘重新提取全部文本 (复现 data/original/)
├── gen_bilingual.py   生成中日对照总表 translation_all.tsv (浏览/审校用)
│
├── apply_patches.py   EXE 12 处 MIPS 补丁 (原版 EXE → 补丁 EXE)
├── build_saf.py       生成补丁 SYSTEM.SAF (替换字库/码表)
├── import_text.py     文本一键导入器 (译文 → ISO, 核心工具)
├── build_iso.py       一键组装镜像 (复制原版 → 写 EXE/SAF → 导文本 → CUE)
├── build_all.py       一键构建全流程 (依次执行上述三步 + verify)
├── verify.py          全量校验 (EXE 补丁/字库/SCRIPT.B/1272 条译文回读)
│
├── make_patch.py      生成 .bpatch 差异补丁 (原版 BIN → 汉化 BIN)
└── apply_patch.py     应用 .bpatch 差异补丁 (玩家用)
```

## 典型工作流

### A. 玩家：直接打补丁 (无需完整构建环境)

```bash
python tools/apply_patch.py patches/deep-freeze-cn.bpatch ^
       --src "原版\Deep Freeze (Japan).bin" ^
       -o "Deep Freeze (Japan) patched.bin"
```

### B. 汉化者：修改译文后重建

```bash
# 1. 编辑 data/translation/trans_pN.py
cd tools
python import_text.py --check      # 校验
python build_iso.py                # 重建镜像
python verify.py                   # 校验
python gen_bilingual.py            # 同步更新中日对照总表 (可选)
```

### C. 从零复现 (要求原版镜像 + 解包资源)

```bash
python tools/dump_exe.py  --bin 原版.bin -o "game/image file/SLPS_018.17"
python tools/dump_safs.py --bin 原版.bin -o "game/image file/ARCHIVE"
# 修改 tools/config.py 的 GAME_DIR 后:
python tools/build_all.py
```

## 依赖

- Python 3.8+（开发环境 3.12, Windows）
- 无第三方库（LZSS/码表/SAF/ISO 处理全部内建实现）
- 仅 `gen_font` 类字形生成需 Windows GDI (见 reference/ 说明)

> AI生成