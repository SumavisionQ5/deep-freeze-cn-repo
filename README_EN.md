---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '1b694be0-8690-48bf-8933-2542d42ee552'
  PropagateID: '1b694be0-8690-48bf-8933-2542d42ee552'
  ReservedCode1: 'bb1fdb27-e130-4681-944d-e4bcbd25c4c0'
  ReservedCode2: 'bb1fdb27-e130-4681-944d-e4bcbd25c4c0'
---

# Deep Freeze Simplified Chinese Translation (SLPS-018.17)

English | [简体中文](README.md)

A **complete Simplified Chinese fan translation** of *Deep Freeze*
(ディープフリーズ), the 1996 PS1 rescue-action game by Microcabin
(Japanese release, SLPS-018.17).

- **1272 translated strings** — mission briefings, weapon/item
  descriptions, all story dialogue, computer terminals, tutorial,
  rankings, ending credits: every extractable text in the game
- **1228-glyph custom font** — SimSun 12 px bitmap (12×12, 2bpp)
  replacing the original 16×15 Japanese font
- **12 MIPS patches** — render-pipeline adaptation only; no code
  injection, no moved resources
- **Fully verified** — EXE patch points, font, codepage, and all 1272
  strings read back from the final image and compared

> ⚠️ This repository contains **no original game assets** (image, EXE,
> SAF archives). You need a legally obtained copy of the original
> Japanese disc. All rights belong to Microcabin.

---

## Quick start (players)

### Option 1: apply the diff patch (recommended)

[`patches/deep-freeze-cn.bpatch`](patches/) is only **425 KB** and
byte-exactly transforms an original image into the translated one:

```bash
python tools/apply_patch.py patches/deep-freeze-cn.bpatch ^
    --src "your path\Deep Freeze (Japan).bin" ^
    -o   "Deep Freeze (Japan) patched.bin"
```

### Option 2: download a ready-made image

Check the Releases page if published. MD5 checksums are recorded in
CHANGELOG.

### Running

Load the generated `patched.bin` + `patched.cue` (6 audio tracks — use
the .cue) with ePSXe / DuckStation / Mednafen etc.

**Original image check**: untouched Japanese retail only —
MD5 `DF51A6E8BEF1055A22AC2FAED9D9E015`, 495,531,120 bytes.

---

## Building from source (translators)

### Prerequisites

1. Windows + Python 3.8+ (standard library only)
2. Original Japanese image `Deep Freeze (Japan).bin/.cue`
3. Point `GAME_DIR` in `tools/config.py` at your game directory

### One-shot build

```bash
# Extract EXE and SAF archives (once)
python tools/dump_exe.py  --bin "D:\game\Deep Freeze (Japan).bin" ^
    -o "D:\game\image file\SLPS_018.17"
python tools/dump_safs.py --bin "D:\game\Deep Freeze (Japan).bin" ^
    -o "D:\game\image file\ARCHIVE"

# Build + import translations + verify
cd tools
python build_all.py
```

Output: `build/Deep Freeze (Japan) patched.bin` + `.cue`, followed by
full verification (12 EXE patch points, 256-aligned font, SCRIPT.B font
paths, 1272-string read-back).

### Editing translations

Translations live in [`data/translation/`](data/translation/), keyed to
the Japanese source lines in
[`data/original/skel_all.tsv`](data/original/).
`translation_all.tsv` is a human-readable JA↔ZH side-by-side table
generated from the modules (for review only; the importer reads the
`.py` modules). After editing:

```bash
python tools/import_text.py --check   # validate (no write)
python tools/build_iso.py             # rebuild image
python tools/verify.py                # verify
```

Constraints enforced by the importer: ≤1.2× source length, matching `|`
segment count, keep leading indentation, charset membership. See
[data/README.md](data/README.md).

---

## Repository layout

```
deep-freeze-cn/
├── README.md / README_EN.md      this file
├── CHANGELOG.md                  version history (v1-v8)
├── LICENSE                       licensing (code/doc vs translation/font)
├── tools/                        full toolchain (see tools/README.md)
├── data/
│   ├── original/                 extracted Japanese text (CSV/TSV/JSON)
│   ├── translation/              Chinese translations trans_p1-p4.py
│   │                             + bilingual table translation_all.tsv
│   └── font/                     custom KPX/TBL font + codepage + charset
├── patches/
│   └── deep-freeze-cn.bpatch     original → translated diff patch (425 KB)
├── docs/
│   ├── HACKING.md                full hacking documentation (Chinese)
│   └── HACKING_EN.md             hacking documentation (English)
└── reference/                    reference scripts (GDI glyph generator)
```

---

## Documentation

| Doc | Content |
|-----|---------|
| [docs/HACKING_EN.md](docs/HACKING_EN.md) | disc/SAF/font formats, codepage design, 12 MIPS patches, space management, pitfalls (black screen / missing glyphs / blank tutorial), debugging |
| [docs/HACKING.md](docs/HACKING.md) | Chinese version (more detail) |
| [tools/README.md](tools/README.md) | toolchain usage |
| [data/README.md](data/README.md) | data formats & translation rules |
| [CHANGELOG.md](CHANGELOG.md) | v1→v8 fix history |

## Technical highlights (TL;DR)

- **256-alignment trap**: the game computes decompressed sizes as
  `entry[11]<<16|entry[15]<<8|entry[19]` (low byte always 0) → every
  file it reads must be 256-byte aligned or the console black-screens
- **0x7F trail trap**: SJIS trail 0x7F is invalid; v7 assigned 7 codes
  there and the characters silently vanished
- **Dual font paths**: the tutorial loader in SCRIPT.B is hardcoded to
  the legacy `KANJI2` font; fixed with equal-length string patches
- **16×15→12×12 adaptation**: stride, VRAM blit, line height, sprite
  size — 12 systematic hardcoded-value edits

Details in [docs/HACKING_EN.md](docs/HACKING_EN.md).

## Credits

- Glyphs: Windows GDI + SimSun bitmap extraction
- Debugging: ePSXe savestates, capstone disassembly

## License

See [LICENSE](LICENSE): tools & docs MIT; translation & font
CC BY-NC-SA 4.0; patch file for owners of the original game only.

> AI生成