"""
basic_usage.py — walkthrough of glyph_steg encode → inspect → decode
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from glyph_steg import encode, decode, capacity, GlyphGrid

# ── 1. How much can a string carry? ─────────────────────────────────────────
cover = "Hello"
print(f"Cover text : {cover!r}")
print(f"Capacity   : {capacity(cover)} bits  ({capacity(cover)//8} bytes)\n")

# ── 2. Inspect a single glyph ───────────────────────────────────────────────
g = GlyphGrid("a", payload_bits=[1,0,1,1,0,0,1,0])
print("GlyphGrid for 'a' with payload 10110010:")
print(g.render_ascii())
print(f"\nPayload bits (first 8): {g.payload_bits[:8]}")
print(f"Capacity             : {g.payload_capacity} bits\n")

# ── 3. Encode a secret ──────────────────────────────────────────────────────
cover  = "HI"          # visible text
secret = "ab"          # hidden message (2 bytes = 16 bits)

enc = encode(cover, secret)
print(f"Encoded '{secret!r}' into cover text '{cover}'")
print(f"Utilisation: {enc.utilisation():.1%}  ({len(secret)*8} / {enc.capacity()} bits used)\n")

# Show the payload grid for the first glyph
first = enc.grids[0]
print(f"Glyph '{first.char}' pixel map (█=ink  1=hidden-1  ·=hidden-0):")
print(first.render_ascii())
print()

# ── 4. Serialise ────────────────────────────────────────────────────────────
json_doc = enc.to_json()
print("JSON document (first 300 chars):")
print(json_doc[:300], "...\n")

# ── 5. Decode ───────────────────────────────────────────────────────────────
recovered = decode(json_doc)
print(f"Recovered secret: {recovered!r}")
assert recovered == secret, "Round-trip failed!"
print("✓ Round-trip verified")
