from .adderfunc import addripple
from .bitsfunc import leftpad
from .shifter_func import shiftleftl, shiftright1

def _twos_to_sign_mag(bits32):
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


def _sign_mag_to_twos(sign, mag_bits):
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

def mdu_mul(rs1_bits, rs2_bits, trace_enabled=True):
 # Decode signs and magnitudes
    s1, mag1 = _twos_to_sign_mag(rs1_bits)
    s2, mag2 = _twos_to_sign_mag(rs2_bits)
    sign_res = s1 ^ s2   # result sign

    # Setup internal registers
    acc = [0] * 64               # 64-bit accumulator
    mcand = leftpad(mag1, 64)    # multiplicand (in low 32 bits)
    mplier = leftpad(mag2, 32)   # multiplier

    count = 32
    step = 0
    trace = []

    # Shift-add loop
    while count > 0:
        if trace_enabled:
            trace.append({
                "step": step,
                "acc": acc[:],
                "mcand": mcand[:],
                "mplier": mplier[:],
            })

        # if multiplier LSB is 1 → acc += mcand
        if mplier[-1] == 1:
            acc, _ = addripple(acc, mcand, cin=0, width=64)

        # left shift multiplicand (multiply by 2)
        mcand = shiftleftl(mcand, 1)

        # right shift multiplier (logical)
        mplier = shiftrightl(mplier, 1)

        count -= 1
        step += 1

    if trace_enabled:
        trace.append({
            "step": step,
            "acc": acc[:],
            "mcand": mcand[:],
            "mplier": mplier[:],
        })

    # Unsigned 64-bit product is now in acc
    prod = acc[:]  # 64 bits

    # Apply sign if needed to get signed 64-bit product
    if sign_res == 1:
        inv = [1 - x for x in prod]
        plus_one_64 = [0] * 63 + [1]
        prod, _ = addripple(inv, plus_one_64, cin=0, width=64)

    # Split into high and low 32 bits
    hi32 = prod[0:32]     # top 32
    lo32 = prod[32:64]    # bottom 32

    # Overflow flag: does it fit in signed 32?
    # for no overflow, all upper 32 bits must equal the sign bit of lo32
    sign_bit = lo32[0]
    overflow = 0
    for b in prod[0:32]:
        if b != sign_bit:
            overflow = 1
            break

    return {
        "lo": lo32,
        "hi": hi32,
        "overflow": overflow,
        "trace": trace,
    }


