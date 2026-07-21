# Glyph-level-bitmap-steganography
Hide data in the whitespace pixels of a bitmap font. 

# glyph-steg

**Glyph-level bitmap steganography** — hide data in the whitespace pixels of a bitmap font.

Every visible letter sits inside a fixed invisible box made of pixels. The ink cells define the letter shape. The empty cells around the shape are a second channel: each one holds a single bit of a hidden message. A reader sees ordinary text; a decoder with the shared font map reads the payload back mechanically.

```
Cover text:  "HI"       Visible to everyone
Secret:      "ab"       Hidden in whitespace bits
Capacity:    ~80 bits   Across 2 glyphs at 8×8
```

---

## How it works

```
┌──────────────────────────────────────────────────────────────┐
│  Fixed 8×8 glyph box for the letter "a"                      │
│                                                              │
│  █ = ink  (defines the letter shape, read by human eye)      │
│  1 = hidden bit 1  (whitespace cell carrying payload)        │
│  · = hidden bit 0  (whitespace cell, empty payload)          │
│                                                              │
│    · · █ █ █ █ · ·                                           │
│    · █ · · · · █ ·                                           │
│    · · · · · · █ ·                                           │
│    · · █ █ █ █ █ ·                                           │
│    · █ · · · █ █ ·                                           │
│    · █ · · · █ █ ·                                           │
│    · · █ █ █ · █ ·                                           │
│    · · · · · · · ·                                           │
└──────────────────────────────────────────────────────────────┘
```

**Encoding pipeline**

1. Render each character of the cover text into its 8×8 bitmap.
2. Identify every non-ink cell — these are the payload slots.
3. Walk the secret message as a bitstream (UTF-8 by default).
4. Write one bit per slot in reading order (left→right, top→bottom).
5. Transmit or store the full grid document.

**Decoding pipeline**

1. Apply the same font map to extract ink vs whitespace.
2. Read every whitespace cell value in reading order.
3. Group bits into bytes and decode to text.

**Why the text looks normal**  
Human letter recognition depends on the outline silhouette of a glyph, not the state of surrounding whitespace. At any normal reading size those cells are perceptually invisible. Only a decoder with the shared font map can extract the payload.

---

## Installation

No dependencies beyond the Python standard library.

```bash
git clone https://github.com/68756d616e/glyph-steg.git
cd glyph-steg
```

Python 3.9+ required. To run tests:

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Quick start

```python
from src.glyph_steg import encode, decode, capacity

# How many bits can a string carry?
print(capacity("Hello"))   # e.g. 200

# Encode a secret into cover text
enc = encode("HI", "ab")
print(enc.utilisation())   # fraction of payload slots used
doc = enc.to_json()        # serialise to JSON for transmission

# Decode on the other end
secret = decode(doc)       # → "ab"
```

---

## API reference

### `encode(cover_text, secret) → Encoder`

Embed `secret` into the whitespace pixels of `cover_text`.  
Raises `ValueError` if the cover text does not have enough capacity.

### `decode(document) → str`

Recover the hidden message from a document dict or JSON string produced by `Encoder.to_json()`.

### `capacity(text) → int`

Return the total number of hidden bits available in a given string.

---

### `GlyphGrid(char, payload_bits=None)`

Represents a single 8×8 glyph box.

| Attribute / method | Description |
|---|---|
| `.payload_capacity` | Total whitespace bits in this glyph |
| `.payload_bits` | List of bits stored in whitespace cells |
| `.ink_at(r, c)` | True if cell is ink |
| `.bit_at(r, c)` | Payload bit at cell, or None if ink |
| `.render_ascii()` | Human-readable grid (█ / 1 / ·) |
| `.full_matrix()` | 8×8 list of strings ("1", "P0", "P1") |

---

### `Encoder(cover_text, secret, encoding="utf-8")`

| Attribute / method | Description |
|---|---|
| `.grids` | List of `GlyphGrid` objects, one per character |
| `.capacity()` | Total payload bits across all glyphs |
| `.utilisation()` | Fraction of capacity used |
| `.to_dict()` | Serialisable document dict |
| `.to_json(indent=2)` | JSON string |

---

### `Decoder(document)` / `Decoder.from_json(json_str)` / `Decoder.from_file(path)`

| Method | Description |
|---|---|
| `.decode()` | Return the recovered hidden string |

---

## Capacity table

Capacity per glyph depends on how much of the 8×8 box the letter actually fills.

| Character | Ink cells | Whitespace cells (payload bits) |
|:---------:|:---------:|:-------------------------------:|
| space     | 0         | 64                              |
| a         | 24        | 40                              |
| b         | 20        | 44                              |
| H         | 22        | 42                              |
| I         | 20        | 44                              |

A 100-character cover text typically carries 3,500–4,000 bits (~430–500 bytes) of hidden data.

---

## Limitations

- **Lossless transmission only.** JPEG compression destroys individual pixel values. Use PNG, direct bitmap, or the JSON document format.
- **Shared font map required.** Both encoder and decoder must use the same glyph definitions. The built-in set covers a limited ASCII subset; extend `_GLYPHS_8X8` in `src/glyph_steg.py` for full coverage.
- **No encryption built in.** The payload is stored as raw bits. Encrypt your secret before encoding if confidentiality matters.
- **No error correction.** A single flipped bit corrupts the byte it belongs to. Add a Reed–Solomon layer over the payload bits for robustness.

---

## Extending the glyph set

Add entries to `_GLYPHS_8X8` in `src/glyph_steg.py`:

```python
_GLYPHS_8X8["c"] = [
    [0,0,1,1,1,1,0,0],
    [0,1,0,0,0,0,1,0],
    [0,1,0,0,0,0,0,0],
    [0,1,0,0,0,0,0,0],
    [0,1,0,0,0,0,0,0],
    [0,1,0,0,0,0,1,0],
    [0,0,1,1,1,1,0,0],
    [0,0,0,0,0,0,0,0],
]
```

Each row is a list of 8 integers: `1` = ink, `0` = whitespace.

---

## Project structure

```
glyph-steg/
├── src/
│   └── glyph_steg.py      # Core library (no dependencies)
├── examples/
│   └── basic_usage.py     # Walkthrough: encode → inspect → decode
├── tests/
│   └── test_glyph_steg.py # 31 unit tests (pytest)
├── docs/
│   └── concept.md         # Technical deep-dive
├── .gitignore
└── README.md
```

---

## Background

This project implements the concept described in the [glyph bitmap steganography explainer](#) — a system where each character in a bitmap font acts as a tiny container for a second message. The visible letter shape occupies some fraction of the fixed pixel box; the remaining cells carry hidden bits that are statistically indistinguishable from ordinary whitespace to a human reader.

The approach is related to:
- **Font steganography** (hiding data in typographic variation)
- **Whitespace steganography** (unused space as a covert channel)
- **Least-significant-bit (LSB) image steganography** (same bit-per-cell principle)

---

## Licence By Zia a Human
