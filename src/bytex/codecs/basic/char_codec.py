from dataclasses import dataclass
from functools import reduce

from bytex.bits import BitBuffer, Bits
from bytex.codecs.base_codec import BaseCodec
from bytex.codecs.basic.integer_codec import IntegerCodec
from bytex.endianness import Endianness
from bytex.errors import ValidationError
from bytex.sign import Sign

U8_CODEC = IntegerCodec(bit_count=8, sign=Sign.UNSIGNED)


@dataclass(frozen=True)
class CharCodec(BaseCodec[str]):
    """Encodes a single Unicode code point using UTF-8 (1–4 bytes)."""

    def validate(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValidationError(
                f"Invalid value, a {self.__class__.__name__}'s value must be of type '{str(str)}'"
            )

        if len(value) != 1:
            raise ValidationError(
                f"Invalid value, a {self.__class__.__name__}'s must be of length 1"
            )
        try:
            b = value.encode("utf-8")
        except UnicodeEncodeError as e:
            raise ValidationError(f"UTF-8 encode failed: {e}")
        if not (1 <= len(b) <= 4):
            raise ValidationError("Invalid UTF-8 length")

    def serialize(self, value: str, endianness: Endianness) -> Bits:
        b = value.encode("utf-8") # 1-4 bytes
        parts = [U8_CODEC.serialize(byte, endianness=endianness) for byte in b]
        return reduce(lambda a, b: a + b, parts)

    def deserialize(self, bit_buffer: BitBuffer, endianness: Endianness) -> str:
        # Read first byte to determine how many total bytes to read (UTF-8 rule)
        first = U8_CODEC.deserialize(bit_buffer, endianness=endianness)
        if (first & 0b1000_0000) == 0:
            need = 1
        elif (first & 0b1110_0000) == 0b1100_0000:
            need = 2
        elif (first & 0b1111_0000) == 0b1110_0000:
            need = 3
        elif (first & 0b1111_1000) == 0b1111_0000:
            need = 4
        else:
            raise ValidationError(f"Invalid UTF-8 leading byte: 0x{first:02x}")

        buf = [first]
        for _ in range(need - 1):
            cont = U8_CODEC.deserialize(bit_buffer, endianness=endianness)
            if (cont & 0b1100_0000) != 0b1000_0000:
                raise ValidationError(f"Invalid UTF-8 continuation byte: 0x{cont:02x}")
            buf.append(cont)

        try:
            s = bytes(buf).decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValidationError(f"UTF-8 decode failed: {e}")

        if len(s) != 1:
            raise ValidationError("Decoded to multiple code points")
        return s
