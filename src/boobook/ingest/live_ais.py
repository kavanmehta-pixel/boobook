"""Optional live AIS utilities.

This is intentionally minimal. For v0.3 the investor MVP is public/source CSV
validation. Live RF capture should be added after legal/compliance review and
hardware testing. When using RTL-SDR, `rtl_ais` can output AIVDM/AIVDO NMEA
sentences over UDP/stdout; `pyais` can decode those sentences if installed.
"""
from __future__ import annotations


def decode_nmea_sentence(sentence: str) -> dict:
    try:
        from pyais import decode  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Install hardware extra first: pip install -e '.[hardware]'") from exc
    msg = decode(sentence)
    return msg.asdict()
