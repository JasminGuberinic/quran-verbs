"""Decoded sound as numbers: read and write 32-bit float WAV, measure and scale its peak.

Pure — bytes in, bytes or numbers out — so the audio gate (fil.audio_qa) and the peak
turn-down (fil.audio) are unit-testable without a decoder. Float, not 16-bit, because an
AAC clip can decode past full scale, and only a float decode shows that it would clip.
"""

from __future__ import annotations

import math
import struct
from array import array
from dataclasses import dataclass

_RIFF_HEADER = struct.Struct("<4sI4s")
_CHUNK_HEADER = struct.Struct("<4sI")
_FORMAT_CHUNK = struct.Struct("<HHIIHH")
_IEEE_FLOAT = 3
_EXTENSIBLE = 0xFFFE    # afconvert's choice of header for float samples
_SAMPLE_BYTES = 4

# A peak that reaches full scale clips: the sound is cut flat where it would go higher.
FULL_SCALE_DB = 0.0


class NotFloatWave(ValueError):
    """Bytes that are not a 32-bit float WAV with sound in it."""


@dataclass(frozen=True)
class FloatWave:
    samples: tuple[float, ...]    # interleaved, full scale is ±1.0
    channels: int
    sample_rate: int

    @property
    def duration_s(self) -> float:
        return len(self.samples) / self.channels / self.sample_rate

    @property
    def peak_db(self) -> float:
        """The sample peak in dBFS; digital silence is minus infinity."""
        return decibels(max(max(self.samples), -min(self.samples)))


def decibels(linear: float) -> float:
    return 20 * math.log10(linear) if linear > 0 else -math.inf


def read_float_wave(wave: bytes) -> FloatWave:
    chunks = _chunks(wave)
    if b"fmt " not in chunks or b"data" not in chunks:
        raise NotFloatWave("a WAV needs a format and a data chunk")
    format_tag, channels, sample_rate, _, _, bits = _FORMAT_CHUNK.unpack_from(chunks[b"fmt "])
    if format_tag not in (_IEEE_FLOAT, _EXTENSIBLE) or bits != 8 * _SAMPLE_BYTES or not channels or not sample_rate:
        raise NotFloatWave(f"expected 32-bit float samples, not format {format_tag} at {bits} bits")
    data = chunks[b"data"]
    samples = array("f")
    samples.frombytes(data[: len(data) // _SAMPLE_BYTES * _SAMPLE_BYTES])
    if not samples:
        raise NotFloatWave("the WAV holds no samples")
    return FloatWave(tuple(samples), channels, sample_rate)


def write_float_wave(sound: FloatWave) -> bytes:
    data = array("f", sound.samples).tobytes()
    block = sound.channels * _SAMPLE_BYTES
    format_chunk = _FORMAT_CHUNK.pack(_IEEE_FLOAT, sound.channels, sound.sample_rate,
                                      sound.sample_rate * block, block, 8 * _SAMPLE_BYTES)
    body = (b"WAVE" + _CHUNK_HEADER.pack(b"fmt ", len(format_chunk)) + format_chunk
            + _CHUNK_HEADER.pack(b"data", len(data)) + data)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def scaled(sound: FloatWave, gain_db: float) -> FloatWave:
    factor = 10 ** (gain_db / 20)
    return FloatWave(tuple(sample * factor for sample in sound.samples), sound.channels, sound.sample_rate)


def _chunks(wave: bytes) -> dict[bytes, bytes]:
    """The RIFF file's chunks by id (the first of each)."""
    if len(wave) < _RIFF_HEADER.size or _RIFF_HEADER.unpack_from(wave)[::2] != (b"RIFF", b"WAVE"):
        raise NotFloatWave("not a RIFF/WAVE file")
    chunks: dict[bytes, bytes] = {}
    offset = _RIFF_HEADER.size
    while offset + _CHUNK_HEADER.size <= len(wave):
        chunk_id, size = _CHUNK_HEADER.unpack_from(wave, offset)
        start = offset + _CHUNK_HEADER.size
        chunks.setdefault(chunk_id, wave[start:start + size])
        offset = start + size + size % 2    # chunks are word-aligned
    return chunks
