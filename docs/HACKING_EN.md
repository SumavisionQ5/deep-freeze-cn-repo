---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'a3a3341a-6cee-4eb6-a34b-eb54dda61142'
  PropagateID: 'a3a3341a-6cee-4eb6-a34b-eb54dda61142'
  ReservedCode1: '216dfd09-6d88-4e40-b0bf-a02f8e954fca'
  ReservedCode2: '216dfd09-6d88-4e40-b0bf-a02f8e954fca'
---

# Deep Freeze (SLPS-018.17) Hacking Notes

> Technical documentation for the Simplified Chinese fan-translation of
> *Deep Freeze* (SLPS-018.17, Japan, 1996, Microcabin). Companion to the
> Chinese version: [docs/HACKING.md](HACKING.md) (more detailed).
> 1272 translated strings · 1228-glyph custom font.

---

## 1. Disc layout

| Item | Value |
|------|-------|
| Track 1 | MODE2/2352, user data 2048 B at sector offset **+24** |
| Image | 495,531,120 bytes |
| Main EXE | `SLPS_018.17` at **LBN 24**, 417,792 B |
| Resources | 18 custom `.SAF` archives (see `data/original/saf_lbn.json`) |
| Text-bearing | `OVERLAY.SAF` (dialogue/tutorial), `MENU1-5.SAF` (menus/briefings), `SYSTEM.SAF` (font/codepage) |

> **Golden rule:** always read a 2352-byte raw image sector-by-sector at
> +24. Treating the whole file as a continuous user-data stream yields
> garbage on decompression — this cost us days of misdiagnosis early on.

## 2. SAF archive format

```
u32 LE   entry count N
20B × N  directory entries
...      data area, addressed by 2048-byte sectors relative to header
```

Directory entry (20 bytes):

```
[0..10]  file name, NUL-terminated, optional '*' prefix
[11]     decompressed size bits 16-23
[12..13] u16 LE start sector
[14..15] u16 LE decompressed size bits 0-15
[16..17] u16 LE clen (compressed length)
[18]     reserved
[19]     decompressed size bits 8-15 (see below)
```

**The game computes decompressed size as
`entry[11]<<16 | entry[15]<<8 | entry[19]`.** Since `entry[19]` is
always 0 in the original, **every file the game reads must have a
decompressed size that is a multiple of 256**. Our v5 build black-screened
because 43956 = 0xABB4 was read as 0xAB00 (180 bytes short). Fix: pad the
decompressed font to 0xAD00 with trailing blanks.

Data is LZSS (OKUMURA variant): 4 KB ring buffer, write pos starts 0xFEE,
match length 3-18, flag byte LSB-first (1 = literal, 0 = 2-byte match
`r = t0 | ((t1 & 0xF0) << 4)`, `len = (t1 & 0xF) + 3`).

## 3. .B data files

After decompression a `.B` file is `u32 count + u32 offsets[]` block
table followed by blocks containing string pools / numeric tables /
bytecode. Strings are SJIS, NUL-terminated, with `0x7C` as in-string
newline. **All edits are done in place** — the block table and string
positions never move; we only overwrite bytes and zero-fill leftovers.

Two "strings" (rows 442/1191) are actually graphics data misdetected as
text; they stay untouched (`FP_LINES` in the toolchain).

## 4. Text extraction heuristics

Distinguishing real text from binary that happens to look like SJIS:

1. Content: kana / full-width alnum / full-width punctuation → REAL;
   pure-kanji strings matched against a **bootstrap dictionary** (553
   chars harvested from known-good dialogue files) with ≥75-90% coverage;
2. Structure: 4-byte aligned offset + zero padding after the NUL;
3. Isolation filter: lone "REAL" strings surrounded by no other reals,
   ≤3 chars, or containing Cyrillic/box-drawing → FAKE.

1274 REAL strings out of 5459 raw candidates entered the translation
pipeline. 36 additional strings were found late (tutorial instructions +
mission-intro terms) by searching PSX RAM from savestates; they are
translated in `trans_p4.py`.

## 5. Font: KPX / TBL

`SYSTEM.SAF` contains `*KANJI.KPX` (16×15 px, 60 B/glyph, 1024 glyphs,
SJIS order), `KANJI.TBL` (1024 × 2 B LE SJIS codes), plus a legacy
`*KANJI2.KPX`/`KANJI2.TBL` pair (JIS order) — see §8.

Glyph layout (2bpp packed rows):

```
pixel(x,y) = (byte[y*4 + x>>2] >> (2*(x&3))) & 3     # original 16×15
0 = transparent, 1 = stroke, 2 = (+1,+1) drop shadow
```

The EXE looks a (lead,trail) pair up **linearly in TBL** to get a glyph
index, then reads `KPX + index × stride`. The index bound is a hardcoded
`slti 0x400` in the EXE.

### Our replacement font

- 12×12 px, 36 B/glyph (3 bytes/row), **1228 glyphs**;
- Rendered from SimSun 12 px via Windows GDI `GetGlyphOutlineW`
  (GGO_BITMAP), baseline y=10, horizontally centered, programmatic
  drop shadow;
- Charset = all unique chars in the translation (1228), sorted by
  codepoint order, see `data/font/charset_used.txt`;
- Generator: `reference/gen_font.py` (Windows-only, uses GDI).

## 6. EXE patches (12 MIPS edits)

Code base `0x8000F800` (file offset = va − 0x8000F800). All patches adapt
the 16×15 rendering pipeline to 12×12:

| # | VA | old → new | meaning |
|---|----|-----------|---------|
| 1 | 0x80030318 | `slti $v0,$v1,0x400` → `0x4CC` | TBL bound 1024→1228 |
| 2 | 0x800301FC | `sll $v0,$a1,4` → `sll 3` | KPX stride step 1 |
| 3 | 0x80030200 | `subu $v0,$v0,$a1` → `addu` | stride ×15→×9 (36 B) |
| 4 | 0x800301F8 | `addiu $t1,$a3,0x78` → `0x48` | upload loop 120→72 halfwords |
| 5 | 0x80030280 | `li $v0,4` → `3` | VRAM blit width |
| 6 | 0x80030288 | `li $v0,0xF` → `0xC` | VRAM blit height |
| 7 | 0x80030624 | `addiu $s3,$s3,0xE` → `0xC` | dialog fullwidth advance |
| 8-10 | 0x80030650 / 0x80030744 / 0x8003069C | `addiu $s5,$s5,0xF` → `0xD` | line height ×3 |
| 10 | 0x800305DC | `li $v1,0xF` → `0xC` | glyph sprite size |
| 12 | file 0x65840 | `0x801FB000` → `0x801EC000` | pool[6] TBL address (data word) |

No code injection anywhere — the stock loader decompresses and uploads
our font as long as the format matches.

## 7. Custom codepage

1228 characters mapped to 2-byte codes that pass the game's SJIS
validity checks:

```
lead:  0x81-0x9F, 0xE0-0xEF
trail: 0x40-0x7E, 0x80-0xFC      # 0x7F is INVALID - never use it
```

Codes are assigned ascending from 0x8140. **Codepoints are frozen once
published** — v8 appended 7 new chars (─△□○伏积纸) at 0x879E-0x87A4,
leaving the first 1221 untouched so that already-written data stayed
valid. v7 lost 7 glyphs to the 0x7F trail bug (`0x817F` etc. are
silently skipped by the game).

Three artifacts must stay in sync: `char_code_map.json` (tools),
`KANJI.TBL` (runtime lookup), `KANJI.KPX` (glyph order).

## 8. The KANJI2 trap (tutorial blank screen)

Symptom in v7: menus/dialogue fine, **tutorial screens entirely blank**.

Savestate analysis showed the tutorial's custom-encoded text was in RAM,
but the font pool at `0x801EC000` contained the *original JIS table*.
Root cause: the game has **two font loading paths** — the tutorial
loader inside `SCRIPT.B` (OVERLAY.SAF) is hardcoded to load
`*KANJI2.KPX` / `KANJI2.TBL`, i.e. the legacy JIS codepage, where our
custom codes don't exist.

Fix — 12-byte equal-length string patches inside decompressed SCRIPT.B:

```
+0x24: '*KANJI2.KPX\0'   →  '*KANJI.KPX\0\0'
+0x30: 'KANJI2.TBL\0\0'  →  'KANJI.TBL\0\0\0'
```

Only 3 font-loading sites exist in the whole game (EXE boot, SCRIPT.B,
TOPMENU.B); other overlays load graphics assets (`*ALI.AMD` etc.) and
are irrelevant.

## 9. Text import / space management

`tools/import_text.py` (per string): verify original bytes against the
extracted hex → compute available space (original length + following
zero-fill, keeping 1 NUL) → encode → refuse to write if it doesn't fit
(no silent truncation) → overwrite + zero-fill.
Per file: LZSS recompress → must fit before next file's sector → write
in place, update `clen`. No relocation, no block-table edits. Idempotent.

## 10. Build pipeline

```
original BIN ──dump──> SLPS_018.17 + ARCHIVE/*.SAF
      │ apply_patches (12 MIPS edits)      │ build_saf (font swap, 256-align)
      ▼                                    ▼
patched EXE                        SYSTEM.NEW.SAF
      └──────────── build_iso ────────────┘
                    │  + import_text (1272 strings) + SCRIPT.B font patch
                    ▼
        patched.bin (+cue) ── verify (all pass) ── make_patch ──> .bpatch
```

`patches/deep-freeze-cn.bpatch` (425 KB, custom simple format,
`DFCNPATCH001`) turns an original BIN into the translated BIN via
`tools/apply_patch.py`.

## 11. Key numbers

| Item | Value |
|------|-------|
| Original BIN | MD5 `DF51A6E8BEF1055A22AC2FAED9D9E015` |
| EXE LBN | 24 |
| Font code base | 0x8000F800 |
| Glyph | 12×12 2bpp, 36 B, 1228 glyphs = 44208 B → padded to 44288 (0xAD00) |
| Compressed KPX | 31,848 B (fits original 36,230 B slot) |
| TBL | 2456 B (2 sectors; overflow covers the dead KANJI2.KPX data) |
| Strings | 1272 translated (+2 false positives kept as-is) |

## 12. License / disclaimer

Fan translation for research. The repo contains **no original game
assets** — only format docs, tools, our translation, and a diff patch.
You must own the original Japanese disc/image. All game assets remain
the property of Microcabin and the original publishers.

> AI生成