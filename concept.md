# Technical concept: glyph-level bitmap steganography

## The core idea

A bitmap font stores each character as a fixed-size pixel grid — commonly 8×8, 16×16, or 12×24. When the letter "a" is rendered, only some of those cells are marked as ink. The rest are structurally empty; the rendering pipeline ignores them. This system treats those empty cells as a writable channel and assigns one hidden bit to each one.

The visible text remains unchanged. A reader perceives only the ink silhouette. A decoder with the shared font map reads the whitespace layer back as a bitstream.

---

## Bit assignment

Each cell in an N×N glyph box has one of two roles:

```
ink cell      → always 1 in the font definition
               → carries no payload, never modified

whitespace cell → 0 in the font definition (the letter does not touch it)
               → assigned a payload bit: 0 or 1
               → contributes to the hidden bitstream
```

Reading order is left→right, top→bottom (standard raster scan). The encoder walks the secret message as a flat bitstream and writes one bit per whitespace cell in this order. The decoder applies the same mask and reads the same cells in the same order.

---

## Capacity formula

For a single glyph in an N×N box:

```
capacity_bits = N² − ink_cells
```

For a cover text of length L characters:

```
total_capacity = Σ (N² − ink_cells_i)   for i = 1..L
```

Denser letters (like "W" or "M") have fewer whitespace cells and lower capacity per glyph. Open letters (like "i", "l", or space) carry more.

At 8×8 with a typical Latin alphabet, most glyphs yield 35–50 payload bits. A 100-character cover text therefore carries roughly 4,000 bits (500 bytes) of hidden data.

---

## Encoding algorithm

```
Input:  cover_text  (string visible to reader)
        secret      (string to hide)
        font_map    (dict: char → 8×8 binary grid)

1.  payload_bits  ← bits(secret, encoding=UTF-8)
2.  cursor        ← 0
3.  for each char c in cover_text:
        glyph    ← font_map[c]
        slots    ← [(r,col) for r,col in 8×8 if glyph[r][col] == 0]
        chunk    ← payload_bits[cursor : cursor + len(slots)]
        cursor   ← cursor + len(chunk)
        assign chunk[i] → slot[i] for each i
        pad remaining slots with 0
4.  if cursor < len(payload_bits):
        raise CapacityError
5.  output: list of annotated glyph grids
```

The output is a list of 8×8 matrices per character, each cell tagged as ink, payload-0, or payload-1.

---

## Decoding algorithm

```
Input:  encoded_document  (list of annotated glyph grids)
        font_map          (same dict used at encode time)

1.  all_bits ← []
2.  for each annotated grid g:
        glyph ← font_map[g.char]
        slots ← [(r,c) for r,c in 8×8 if glyph[r][c] == 0]
        for slot in slots:
            all_bits.append(g.cell_value[slot])
3.  bytes ← group all_bits into 8-bit chunks
4.  secret ← decode(bytes, encoding=UTF-8)
5.  strip trailing null bytes
6.  return secret
```

No statistical analysis. No image processing. Just a binary read against a known template.

---

## Why the text looks unchanged

Human letter recognition operates on the overall outline silhouette of a glyph — the contrast boundary between ink and background. Studies in visual cognition consistently show that readers do not examine individual pixels; they pattern-match the global shape at a glance.

At normal display or print sizes, the whitespace cells around a letter are either:

- sub-pixel (smaller than the eye can resolve at reading distance), or
- perceptually grouped with the surrounding background.

Even at enlarged sizes (where individual pixels become visible), a person looking at the document is not performing a pixel-level audit. They are reading. The whitespace cells read as "not letter" — which is exactly correct.

---

## Security properties

| Property | Status |
|---|---|
| Visible text unchanged | ✓ |
| Robust to human inspection | ✓ |
| Requires shared font map to decode | ✓ |
| Confidential payload | ✗ — bits are raw, add encryption separately |
| Robust to lossy compression | ✗ — JPEG destroys pixel values |
| Robust to lossless formats (PNG, BMP) | ✓ |
| Error-correcting | ✗ — one flipped bit corrupts a byte |
| Detectable by statistical steganalysis | Depends on payload density |

For adversarial settings, encrypt the secret before encoding (AES-GCM or ChaCha20-Poly1305) and consider adding error-correction bits (Reed–Solomon) to a reserved portion of each glyph's whitespace.

---

## Relationship to existing techniques

**Font steganography** alters the kerning, weight, or baseline of visible characters in imperceptible ways. This system does not alter the rendered character at all — it exploits structure that is present but unused.

**Whitespace steganography** encodes data in tabs, spaces, and line endings in source code or plain text files. The principle is similar: exploit invisible structure. The glyph approach extends this to the sub-character level.

**LSB image steganography** replaces the least-significant bit of each pixel's colour value with a payload bit. The glyph approach is analogous but uses a binary (1-bit-per-cell) font rather than a continuous-tone image, which makes both the encoding and the detection simpler.

---

## Extending to 16×16 grids

Scaling up to a 16×16 glyph box increases capacity fourfold (256 cells per glyph vs 64). The algorithm is identical — only `N` changes. A 16×16 grid with ~80 ink cells leaves ~176 payload bits per character, giving a 100-character cover text a capacity of roughly 2,200 bytes.

At larger grid sizes, glyphs also have more structural variation (serifs, stroke contrast, diacritics) that a steganalyst could potentially exploit as a fingerprint. Binary 8×8 grids are the most conservative starting point.

---

## Future directions

- Full ASCII glyph set (printable 32–126)
- Unicode / extended Latin support
- Error-correction layer (Reed–Solomon over payload bits)
- Encryption wrapper (AES-GCM, key exchanged out-of-band)
- PNG export: render annotated glyph boxes as a viewable bitmap
- Variable grid size (8×8 / 12×16 / 16×16) with auto-detection
- Statistical capacity planner: given a secret length, find the shortest sufficient cover text
