from .adderfunc import addripple
from .bitsfunc import leftpad

def twos_to_sign_mag(bits32):
    """
    Take a 32-bit two's complement number (list of 0/1)
    and return (sign, magnitude_bits).

    sign = 0 (non-negative), 1 (negative)
    magnitude_bits = |value| as unsigned 32-bit bits.
    """
    b = leftpad(bits32, 32)
    sign = b[0]

    if sign == 0:
        # positive or zero: magnitude is just the same bits
        return 0, b[:]
    else:
        # negative: magnitude = two's complement of b = invert + 1
        inv = [1 - x for x in b]                 # invert each bit
        plus_one = leftpad([0] * 31 + [1], 32)   # 000...0001 as 32 bits
        mag, _ = addripple(inv, plus_one, cin=0, width=32)
        return 1, mag


def sign_mag_to_twos(sign, mag_bits):
    """
    Take (sign, magnitude_bits) and return 32-bit two's-complement bits.

    If sign == 0 → just zero-extend the magnitude.
    If sign == 1 → return -magnitude in two's complement (invert + 1).
    """
    mag32 = leftpad(mag_bits, 32)

    if sign == 0:
        return mag32
    else:
        inv = [1 - x for x in mag32]
        plus_one = leftpad([0] * 31 + [1], 32)
        neg, _ = addripple(inv, plus_one, cin=0, width=32)
        return neg
