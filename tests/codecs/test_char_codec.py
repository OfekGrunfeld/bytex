from typing import Any

import pytest

from bytex import BitBuffer
from bytex.bits import Bits, string_to_bits, to_bits
from bytex.codecs.basic.char_codec import CharCodec
from bytex.endianness import Endianness
from bytex.errors import ValidationError


@pytest.mark.parametrize("value", ["A", "z", "0", " ", "\n"])
def test_char_validate_success(value: str) -> None:
    codec = CharCodec()
    codec.validate(value)


@pytest.mark.parametrize("value", [None, "", "AB", 5, True, [], {}])
def test_char_validate_failure(value: Any) -> None:
    codec = CharCodec()
    with pytest.raises(ValidationError):
        codec.validate(value)


@pytest.mark.parametrize(
    "char, expected_bits",
    [
        ("A", string_to_bits("01000001")),
        ("a", string_to_bits("01100001")),
        ("0", string_to_bits("00110000")),
        (" ", string_to_bits("00100000")),
    ],
)
def test_char_serialize(char: str, expected_bits: Bits) -> None:
    codec = CharCodec()

    assert codec.serialize(char, endianness=Endianness.BIG) == expected_bits


@pytest.mark.parametrize(
    "bits, char",
    [
        (string_to_bits("01000001"), "A"),
        (string_to_bits("01100001"), "a"),
        (string_to_bits("00110000"), "0"),
        (string_to_bits("00100000"), " "),
    ],
)
def test_char_deserialize(bits: Bits, char: str) -> None:
    codec = CharCodec()
    buffer = BitBuffer()
    buffer.write(bits)
    result = codec.deserialize(buffer, endianness=Endianness.LITTLE)
    assert result == char


@pytest.mark.parametrize("char", ["A", "a", "0", " ", "\n"])
def test_char_roundtrip(char: str) -> None:
    codec = CharCodec()
    bits = codec.serialize(char, endianness=Endianness.BIG)

    buffer = BitBuffer()
    buffer.write(bits)
    result = codec.deserialize(buffer, endianness=Endianness.LITTLE)

    assert result == char


@pytest.mark.parametrize("char", ["A", "é", "€", "𝄞", "🧪"])
def test_utf8_roundtrip(char: str) -> None:
    codec = CharCodec()
    codec.validate(char)

    bits = codec.serialize(char, endianness=Endianness.BIG)  # endianness irrelevant for UTF-8
    buf = BitBuffer()
    buf.write(bits)
    out = codec.deserialize(buf, endianness=Endianness.LITTLE)

    assert out == char


@pytest.mark.parametrize(
    "char, expected_bytes",
    [
        ("A", "41"),
        ("é", "C3A9"),       # 0xC3 0xA9
        ("€", "E282AC"),     # 0xE2 0x82 0xAC
        ("𝄞", "F09D849E"),   # 0xF0 0x9D 0x84 0x9E (U+1D11E)
        ("🧪", "F09FA7AA"),  # U+1F9EA
    ],
)
def test_utf8_serialize_exact_bytes(char: str, expected_bytes: str) -> None:
    codec = CharCodec()
    expected = bytes.fromhex(expected_bytes)
    bits = codec.serialize(char, endianness=Endianness.BIG)
    assert bits == to_bits(expected)


def test_utf8_deserialize_invalid_lead_byte() -> None:
    """0xFF is an invalid UTF-8 leading byte"""
    codec = CharCodec()
    buf = BitBuffer()
    buf.write(to_bits(bytes([0xFF])))
    with pytest.raises(ValidationError):
        _ = codec.deserialize(buf, endianness=Endianness.BIG)


def test_utf8_deserialize_invalid_continuation() -> None:
    """0xC3 expects one continuation byte; 0x20 is not a continuation."""
    codec = CharCodec()
    bad = bytes([0xC3, 0x20])
    buf = BitBuffer()
    buf.write(to_bits(bad))
    with pytest.raises(ValidationError):
        _ = codec.deserialize(buf, endianness=Endianness.BIG)
