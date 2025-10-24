from numsim.bits import *
from numsim.adder import ripple_add, negate_twos

WIDTH = 32

def extend_zero(b, width_to_ex: int = WIDTH):
    b = trim_msb(b)
    if len(b) >= width_to_ex:
        return b[-width_to_ex:]
    return [0] * (width_to_ex - len(b)) + b

def extend_sign(b, width_to_ex: int = WIDTH):
    b = trim_msb(b)
    sign = b[0] if b else 0
    if len(b) >= width_to_ex:
        return b[-width_to_ex:]
    return [sign] * (width_to_ex - len(b)) + b

def encode_twos(value: int):
    mag_bits = int_to_bits(abs(value))
    mag_bits = trim_msb(mag_bits)
    mag_padded = extend_zero(mag_bits, WIDTH)

    if value < 0:
        b = negate_twos(mag_padded)
        b = extend_sign(b, WIDTH)
    else:
        b = extend_zero(mag_bits, WIDTH)

    ov = 1 if (value < -200000 or value > 200000) else 0

    return {
        "bin": bits_to_bin(b),
        "hex": bits_to_hex(b),
        "flagoverflow": ov,
        "bits": b
    }

def decode_twos(bits_in: list[int]):
    b = extend_sign(bits_in, WIDTH)
    sign = 1 if b[0] == 1 else 0
    if sign == 0:
        val = bits_to_uint(b)
    else:
        mag = negate_twos(b)
        val = -bits_to_uint(mag)
    return {"value_bits": b, "sign": sign, "value": val}
