"""
tests/test_glyph_steg.py
Run with:  python -m pytest tests/
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from glyph_steg import (
    GlyphGrid, Encoder, Decoder, encode, decode, capacity,
    _text_to_bits, _bits_to_text, _whitespace_slots, _get_glyph,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

class TestHelpers:
    def test_text_to_bits_roundtrip(self):
        for msg in ["A", "Hi", "Hello, World!", "🙂"]:
            bits = _text_to_bits(msg, "utf-8")
            assert _bits_to_text(bits, "utf-8") == msg

    def test_bits_length(self):
        assert len(_text_to_bits("A")) == 8
        assert len(_text_to_bits("AB")) == 16

    def test_whitespace_slots_no_ink(self):
        blank = [[0]*8 for _ in range(8)]
        slots = _whitespace_slots(blank)
        assert len(slots) == 64

    def test_whitespace_slots_all_ink(self):
        full = [[1]*8 for _ in range(8)]
        assert _whitespace_slots(full) == []

    def test_whitespace_slots_reading_order(self):
        glyph = _get_glyph("a")
        slots = _whitespace_slots(glyph)
        # Must be in row-major order
        for i in range(len(slots) - 1):
            r0, c0 = slots[i]
            r1, c1 = slots[i+1]
            assert (r0, c0) < (r1, c1)


# ── GlyphGrid ────────────────────────────────────────────────────────────────

class TestGlyphGrid:
    def test_single_char_only(self):
        with pytest.raises(ValueError):
            GlyphGrid("ab")

    def test_capacity_positive(self):
        g = GlyphGrid("a")
        assert g.payload_capacity > 0

    def test_payload_defaults_zero(self):
        g = GlyphGrid("a")
        assert all(b == 0 for b in g.payload_bits)

    def test_payload_stored_correctly(self):
        bits = [1, 0, 1, 1, 0, 0, 1, 0]
        g = GlyphGrid("a", bits)
        assert g.payload_bits[:8] == bits

    def test_extra_bits_ignored(self):
        g = GlyphGrid("a", [1] * 1000)
        assert len(g.payload_bits) == g.payload_capacity

    def test_missing_bits_padded(self):
        g = GlyphGrid("a", [1])
        assert g.payload_bits[0] == 1
        assert all(b == 0 for b in g.payload_bits[1:])

    def test_ink_cells_return_none(self):
        glyph = _get_glyph("a")
        g = GlyphGrid("a")
        for r in range(8):
            for c in range(8):
                if glyph[r][c] == 1:
                    assert g.bit_at(r, c) is None
                else:
                    assert g.bit_at(r, c) is not None

    def test_render_ascii_shape(self):
        g = GlyphGrid("a")
        lines = g.render_ascii().split("\n")
        assert len(lines) == 8
        assert all(len(l) == 8 for l in lines)

    def test_full_matrix_shape(self):
        g = GlyphGrid("a")
        m = g.full_matrix()
        assert len(m) == 8
        assert all(len(row) == 8 for row in m)

    def test_space_glyph_all_whitespace(self):
        g = GlyphGrid(" ")
        assert g.payload_capacity == 64


# ── Encoder ───────────────────────────────────────────────────────────────────

class TestEncoder:
    def test_basic_encode(self):
        enc = encode("HI", "a")
        assert len(enc.grids) == 2

    def test_capacity_calculation(self):
        enc = encode("HI", "a")
        assert enc.capacity() == sum(g.payload_capacity for g in enc.grids)

    def test_utilisation_range(self):
        enc = encode("HI", "a")
        assert 0.0 < enc.utilisation() <= 1.0

    def test_to_dict_keys(self):
        enc = encode("HI", "a")
        d = enc.to_dict()
        for key in ("cover_text", "encoding", "capacity_bits", "payload_bits", "utilisation", "glyphs"):
            assert key in d

    def test_to_json_valid(self):
        enc = encode("HI", "a")
        parsed = json.loads(enc.to_json())
        assert parsed["cover_text"] == "HI"

    def test_cover_too_short(self):
        with pytest.raises(ValueError, match="Cover text too short"):
            encode("a", "This secret is way too long for one glyph")

    def test_glyph_count_matches_cover(self):
        cover = "Hello"
        enc = encode(cover, "Hi")
        assert len(enc.grids) == len(cover)


# ── Decoder ───────────────────────────────────────────────────────────────────

class TestDecoder:
    def _roundtrip(self, cover: str, secret: str) -> str:
        enc = encode(cover, secret)
        return decode(enc.to_dict())

    def test_roundtrip_ascii(self):
        assert self._roundtrip("HI", "a") == "a"

    def test_roundtrip_multi_char(self):
        assert self._roundtrip("HI", "ab") == "ab"

    def test_roundtrip_json_string(self):
        enc = encode("HI", "ab")
        assert decode(enc.to_json()) == "ab"

    def test_roundtrip_space_cover(self):
        # Space glyph = 64 bits capacity → easily fits 4 chars
        assert self._roundtrip("    ", "Hi!") == "Hi!"

    def test_empty_secret(self):
        enc = encode("HI", "")
        recovered = decode(enc.to_dict())
        assert recovered == ""

    def test_from_json_classmethod(self):
        enc = encode("HI", "ab")
        dec = Decoder.from_json(enc.to_json())
        assert dec.decode() == "ab"


# ── capacity() helper ─────────────────────────────────────────────────────────

class TestCapacity:
    def test_empty_string(self):
        assert capacity("") == 0

    def test_space_only(self):
        assert capacity(" ") == 64

    def test_longer_text(self):
        c = capacity("HI")
        assert c > 0
        assert c == sum(len(_whitespace_slots(_get_glyph(ch))) for ch in "HI")
