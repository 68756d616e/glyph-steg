"""
glyph_steg.py — Glyph-level bitmap steganography
Hides binary data in the whitespace pixels of a bitmap font glyph grid.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Union


# ---------------------------------------------------------------------------
# Built-in 8x8 reference glyphs (printable ASCII 32–126)
# Each glyph is a flat 64-bit integer; bit 63 = cell [0,0], bit 0 = cell [7,7]
# 1 = ink  0 = whitespace (payload carrier)
# ---------------------------------------------------------------------------

_GLYPHS_8X8: dict[str, list[list[int]]] = {
    "a": [
        [0,0,1,1,1,1,0,0],
        [0,1,0,0,0,0,1,0],
        [0,0,0,0,0,0,1,0],
        [0,0,1,1,1,1,1,0],
        [0,1,0,0,0,1,1,0],
        [0,1,0,0,0,1,1,0],
        [0,0,1,1,1,0,1,0],
        [0,0,0,0,0,0,0,0],
    ],
    "b": [
        [0,1,0,0,0,0,0,0],
        [0,1,0,0,0,0,0,0],
        [0,1,1,1,1,0,0,0],
        [0,1,0,0,0,1,0,0],
        [0,1,0,0,0,1,0,0],
        [0,1,0,0,0,1,0,0],
        [0,1,1,1,1,0,0,0],
        [0,0,0,0,0,0,0,0],
    ],
    "H": [
        [0,1,0,0,0,1,0,0],
        [0,1,0,0,0,1,0,0],
        [0,1,0,0,0,1,0,0],
        [0,1,1,1,1,1,0,0],
        [0,1,0,0,0,1,0,0],
        [0,1,0,0,0,1,0,0],
        [0,1,0,0,0,1,0,0],
        [0,0,0,0,0,0,0,0],
    ],
    "I": [
        [0,0,1,1,1,1,0,0],
        [0,0,0,1,1,0,0,0],
        [0,0,0,1,1,0,0,0],
        [0,0,0,1,1,0,0,0],
        [0,0,0,1,1,0,0,0],
        [0,0,0,1,1,0,0,0],
        [0,0,1,1,1,1,0,0],
        [0,0,0,0,0,0,0,0],
    ],
    " ": [
        [0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0],
    ],
}

# Fallback: any unknown character gets a full-whitespace box (64 payload bits)
_BLANK_GLYPH: list[list[int]] = [[0]*8 for _ in range(8)]


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _get_glyph(char: str) -> list[list[int]]:
    """Return the 8x8 bitmap for a character, falling back to blank."""
    return _GLYPHS_8X8.get(char, _BLANK_GLYPH)


def _whitespace_slots(glyph: list[list[int]]) -> list[tuple[int, int]]:
    """Return (row, col) coordinates of every non-ink cell in reading order."""
    return [
        (r, c)
        for r in range(8)
        for c in range(8)
        if glyph[r][c] == 0
    ]


def _text_to_bits(text: str, encoding: str = "utf-8") -> list[int]:
    bits: list[int] = []
    for byte in text.encode(encoding):
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _bits_to_text(bits: list[int], encoding: str = "utf-8") -> str:
    # Trim to a multiple of 8
    bits = bits[: (len(bits) // 8) * 8]
    byte_vals = [
        int("".join(str(b) for b in bits[i : i + 8]), 2)
        for i in range(0, len(bits), 8)
    ]
    # Strip null padding
    while byte_vals and byte_vals[-1] == 0:
        byte_vals.pop()
    return bytes(byte_vals).decode(encoding, errors="replace")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class GlyphGrid:
    """
    A single 8×8 glyph box, combining visible ink and a hidden payload layer.

    Parameters
    ----------
    char : str
        The visible character (one character).
    payload_bits : list[int]
        Bits to write into the whitespace cells.  Extra bits are silently
        ignored; missing bits are padded with 0.
    """

    SIZE = 8

    def __init__(self, char: str, payload_bits: list[int] | None = None):
        if len(char) != 1:
            raise ValueError("char must be exactly one character")
        self.char = char
        self._ink = _get_glyph(char)
        self._slots = _whitespace_slots(self._ink)
        n = len(self._slots)
        bits = (payload_bits or [])[:n]
        bits += [0] * (n - len(bits))
        self._payload: dict[tuple[int, int], int] = {
            slot: bit for slot, bit in zip(self._slots, bits)
        }

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def payload_capacity(self) -> int:
        """Total bits available in this glyph's whitespace."""
        return len(self._slots)

    @property
    def payload_bits(self) -> list[int]:
        """Bits stored in whitespace cells, in reading order."""
        return [self._payload[s] for s in self._slots]

    # ------------------------------------------------------------------
    # Grid accessors
    # ------------------------------------------------------------------

    def ink_at(self, row: int, col: int) -> bool:
        return bool(self._ink[row][col])

    def bit_at(self, row: int, col: int) -> int | None:
        """Return payload bit at (row, col), or None if the cell is ink."""
        if self._ink[row][col]:
            return None
        return self._payload[(row, col)]

    def full_matrix(self) -> list[list[str]]:
        """
        Return the 8×8 grid as strings:
          '1' = ink cell
          'P0' / 'P1' = payload cell containing 0 or 1
        """
        grid = []
        for r in range(self.SIZE):
            row = []
            for c in range(self.SIZE):
                if self._ink[r][c]:
                    row.append("1")
                else:
                    row.append(f"P{self._payload[(r,c)]}")
            grid.append(row)
        return grid

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def render_ascii(self, ink: str = "█", zero: str = "·", one: str = "1") -> str:
        """Render the glyph as a human-readable ASCII block."""
        lines = []
        for r in range(self.SIZE):
            row_str = ""
            for c in range(self.SIZE):
                if self._ink[r][c]:
                    row_str += ink
                elif self._payload[(r, c)]:
                    row_str += one
                else:
                    row_str += zero
            lines.append(row_str)
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"GlyphGrid({self.char!r}, "
            f"capacity={self.payload_capacity} bits, "
            f"payload={self.payload_bits[:8]}{'...' if self.payload_capacity > 8 else ''})"
        )


# ---------------------------------------------------------------------------

class Encoder:
    """
    Encode a secret message into a cover text using glyph-level steganography.

    The cover text must contain enough whitespace capacity across all its
    glyphs to hold every bit of the secret.

    Parameters
    ----------
    cover_text : str
        The visible text that will carry the hidden payload.
    secret : str
        The message to hide.
    encoding : str
        Character encoding for the secret (default utf-8).
    """

    def __init__(self, cover_text: str, secret: str, encoding: str = "utf-8"):
        self.cover_text = cover_text
        self.secret = secret
        self.encoding = encoding
        self._grids: list[GlyphGrid] = []
        self._encode()

    def _encode(self) -> None:
        payload = _text_to_bits(self.secret, self.encoding)
        cursor = 0
        for char in self.cover_text:
            glyph = _get_glyph(char)
            capacity = len(_whitespace_slots(glyph))
            chunk = payload[cursor : cursor + capacity]
            cursor += len(chunk)
            self._grids.append(GlyphGrid(char, chunk))

        if cursor < len(payload):
            raise ValueError(
                f"Cover text too short: needs {len(payload)} payload bits "
                f"but only {cursor} slots available across {len(self.cover_text)} glyphs."
            )

    @property
    def grids(self) -> list[GlyphGrid]:
        return self._grids

    def capacity(self) -> int:
        """Total whitespace bits available in the cover text."""
        return sum(g.payload_capacity for g in self._grids)

    def utilisation(self) -> float:
        """Fraction of payload slots that carry secret bits."""
        used = len(_text_to_bits(self.secret, self.encoding))
        return used / self.capacity() if self.capacity() else 0.0

    def to_dict(self) -> dict:
        """Serialisable representation of the encoded document."""
        return {
            "cover_text": self.cover_text,
            "encoding": self.encoding,
            "capacity_bits": self.capacity(),
            "payload_bits": len(_text_to_bits(self.secret, self.encoding)),
            "utilisation": round(self.utilisation(), 4),
            "glyphs": [
                {
                    "char": g.char,
                    "payload_bits": g.payload_bits,
                    "capacity": g.payload_capacity,
                }
                for g in self._grids
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------

class Decoder:
    """
    Recover a hidden message from an encoded document dictionary.

    Parameters
    ----------
    document : dict
        A dictionary produced by ``Encoder.to_dict()``.
    """

    def __init__(self, document: dict):
        self._doc = document

    def decode(self) -> str:
        all_bits: list[int] = []
        for glyph_entry in self._doc["glyphs"]:
            all_bits.extend(glyph_entry["payload_bits"])
        return _bits_to_text(all_bits, self._doc.get("encoding", "utf-8"))

    @classmethod
    def from_json(cls, json_str: str) -> "Decoder":
        return cls(json.loads(json_str))

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "Decoder":
        return cls(json.loads(Path(path).read_text()))


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def encode(cover_text: str, secret: str) -> Encoder:
    """Shorthand: encode *secret* into *cover_text* and return an Encoder."""
    return Encoder(cover_text, secret)


def decode(document: dict | str) -> str:
    """
    Shorthand: recover hidden text from a document dict or JSON string.
    """
    if isinstance(document, str):
        return Decoder.from_json(document).decode()
    return Decoder(document).decode()


def capacity(text: str) -> int:
    """Return total hidden-bit capacity for a given cover text string."""
    return sum(len(_whitespace_slots(_get_glyph(c))) for c in text)
