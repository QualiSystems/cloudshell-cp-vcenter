from __future__ import annotations

import pytest

from cloudshell.cp.vcenter.utils.units_converter import (
    PREFIX_B,
    PREFIX_GB,
    PREFIX_HZ,
    PREFIX_KB,
    PREFIX_KHZ,
    PREFIX_MB,
    PREFIX_MHZ,
    PREFIX_TB,
    format_bytes,
    format_hertz,
)


@pytest.mark.parametrize(
    ("size", "prefix", "expected"),
    [
        (0, PREFIX_B, "0 B"),
        (1, PREFIX_B, "1 B"),
        (1034, PREFIX_B, "1.01 KB"),
        (2**10 + 310, PREFIX_B, "1.3 KB"),
        (1, PREFIX_KB, "1 KB"),
        (2**10 + 100, PREFIX_KB, "1.1 MB"),
        (2**20, PREFIX_KB, "1 GB"),
        (2**30 + 100, PREFIX_KB, "1 TB"),
        (2**40, PREFIX_KB, "1024 TB"),
        (20.01, PREFIX_MB, "20.01 MB"),
        (20.20, PREFIX_GB, "20.2 GB"),
        (20, PREFIX_TB, "20 TB"),
    ],
)
def test_format_bytes(size: int, prefix: str, expected: str):
    assert format_bytes(size, prefix) == expected


@pytest.mark.parametrize(
    ("size", "prefix", "expected"),
    [
        (0, PREFIX_HZ, "0 Hz"),
        (1, PREFIX_HZ, "1 Hz"),
        (1034, PREFIX_HZ, "1.03 kHz"),
        (1310, PREFIX_HZ, "1.31 kHz"),
        (1, PREFIX_KHZ, "1 kHz"),
        (1100, PREFIX_KHZ, "1.1 MHz"),
        (10**6, PREFIX_KHZ, "1 GHz"),
        (102, PREFIX_MHZ, "102 MHz"),
    ],
)
def test_format_hertz(size: int, prefix: str, expected: str):
    assert format_hertz(size, prefix) == expected
