from bitsfunc import leftpad

# /Users/csuftitan/Numeric-Ops-Simulator-440/fpu.py
# IEEE 754 Floating Point Representation Utilities for float32
# Helpers: split/pack/classify/round and a small FPU wrapper

BIAS = 127

class Class:
    NAN = "NaN"
    INF = "Inf"
    ZERO = "Zero"
    SUBNORMAL = "Subnormal"
    NORMAL = "Normal"

def split_float32(x_bits):
    """Expect x_bits as iterable/list of 32 bits [b31(sign), b30..b23(exp), b22..b0(frac)]"""
    if len(x_bits) != 32:
        raise ValueError("split_float32 expects 32 bits")
    sign = x_bits[0]
    exp = x_bits[1:9]
    frac = x_bits[9:32]
    return sign, exp, frac

def f32_unpack(x_bits):
    """
    Turn raw 32 bits into (class, sign, unbiased_exponent, significand_24)
    significand_24: list of 24 bits including implicit leading 1 for normals,
                    or leading 0 for subnormals/zero.
    For special classes we still return a 24-bit pattern for convenience.
    """
    sign, exp_bits, frac_bits = split_float32(x_bits)

    all_ones = all(b == 1 for b in exp_bits)
    all_zeros = all(b == 0 for b in exp_bits)

    if all_ones:
        # Infinity or NaN
        if any(frac_bits):
            # Quiet NaN canonicalized to sign-preserving pattern
            return (Class.NAN, sign, None, [1] + [0]*23)
        else:
            return (Class.INF, sign, None, [1] + [0]*23)

    if all_zeros:
        if any(frac_bits):
            # subnormal: exponent is -126 (unbiased for smallest normal would be -126),
            # but subnormals use exponent field 0. Represent significand with leading 0.
            return (Class.SUBNORMAL, sign, -126, [0] + list(frac_bits))
        else:
            return (Class.ZERO, sign, -126, [0] + [0]*23)

    # normal case: convert exp bits to integer then subtract bias
    exp_val = 0
    for b in exp_bits:
        exp_val = (exp_val << 1) | (1 if b else 0)
    unbiased = exp_val - BIAS
    sig_24 = [1] + list(frac_bits)
    return (Class.NORMAL, sign, unbiased, sig_24)

def int_to_exp(w):
    """Clamp w to [0,255] and return 8-bit list MSB..LSB"""
    if w < 0:
        w = 0
    elif w > 255:
        w = 255
    out = [0] * 8
    for i in range(7, -1, -1):
        out[i] = w & 1
        w >>= 1
    return out

def _add_one_to_bits(bits):
    """Add 1 to a list of bits (MSB..LSB). Returns (result_bits, carry_out)"""
    out = bits[:]  # copy
    carry = 1
    for i in range(len(out)-1, -1, -1):
        total = out[i] + carry
        out[i] = total & 1
        carry = 1 if total > 1 else 0
        if carry == 0:
            break
    return out, carry

def f32_pack(sign, exp_unbs, sig_24, f):
    """
    Pack sign, unbiased exponent, and a significand (list of bits, at least 24 bits)
    into a 32-bit float bit-pattern list [sign] + [8 exp bits] + [23 frac bits].
    Rounding is round-to-nearest-even. f is a dict for flags: 'inexact','overflow','underflow'
    """
    # normalize inputs
    sig = list(sig_24[:])  # copy
    if len(sig) < 24:
        sig += [0] * (24 - len(sig))

    rest = sig[24:] if len(sig) > 24 else []
    kept = sig[:24]

    # derive guard/round/sticky from rest
    g = rest[0] if len(rest) >= 1 else 0
    r = rest[1] if len(rest) >= 2 else 0
    sticky = 1 if any(rest[2:]) else 0

    # inexact if any dropped bits are 1
    if any(rest):
        f["inexact"] = True

    # round-to-nearest-even
    increment = 0
    if g == 1 and (r == 1 or sticky == 1 or kept[-1] == 1):
        increment = 1

    if increment:
        kept, carry = _add_one_to_bits(kept)
        if carry:
            # overflowed the 24-bit significand: produce a new leading 1 and drop LSB
            kept = [1] + kept[:-1]
            exp_unbs += 1
        f["inexact"] = True

    exp_biased = exp_unbs + BIAS

    # overflow -> infinity
    if exp_biased >= 255:
        f["overflow"] = True
        f["inexact"] = True
        return [sign] + [1]*8 + [0]*23

    # handle subnormal/zero when biased exponent <= 0
    if exp_biased <= 0:
        # need to shift the (implicit-1-included) kept right by (1 - exp_biased)
        shift = 1 - exp_biased
        # create an extended significand to shift (kept + any following bits)
        ext = kept[:] + rest[:]  # ext contains all low-order bits that can create sticky
        # perform logical right shift by 'shift' positions, collecting sticky
        if shift >= len(ext):
            shifted = [0] * len(ext)
            sticky2 = 1 if any(ext) else 0
        else:
            # bits that will remain after shifting
            shifted = ext[:len(ext)-shift]
            dropped = ext[len(ext)-shift:]
            sticky2 = 1 if any(dropped) else 0

        # Now shifted contains the top bits (MSB..LSB) of the adjusted significand.
        # We need top 24 bits to form rounding guard/round/sticky for subnormal result.
        top24 = shifted[:24] if len(shifted) >= 24 else ([0]*(24 - len(shifted)) + shifted)
        tail = shifted[24:] if len(shifted) > 24 else []
        # derive guard/round/sticky for final rounding
        g2 = tail[0] if len(tail) >= 1 else 0
        r2 = tail[1] if len(tail) >= 2 else 0
        sticky_final = 1 if sticky2 or any(tail[2:]) else 0

        # round to nearest even for subnormal
        inc2 = 0
        if g2 == 1 and (r2 == 1 or sticky_final == 1 or top24[-1] == 1):
            inc2 = 1

        if inc2:
            top24, carry2 = _add_one_to_bits(top24)
            if carry2:
                # Rare case where rounding a subnormal produces a non-subnormal normal;
                # this means exponent becomes 1 (biased), and significand must be normalized.
                exp_biased = 1
                frac23 = top24[1:24]
                f["inexact"] = True
                return [sign] + int_to_exp(exp_biased) + frac23
            f["inexact"] = True

        f["underflow"] = True
        # subnormal encoding uses exponent bits = 0
        frac23 = top24[1:24]
        return [sign] + [0]*8 + frac23

    # normal case
    exp_bits = int_to_exp(exp_biased)
    frac23 = kept[1:24]
    return [sign] + exp_bits + frac23

# Small FPU wrapper that will prefer functions from .ieee754 if available.
class FPU:
    def __init__(self):
        self.flags = {"inexact": False, "overflow": False, "underflow": False}
        # try to import external implementations if present
        try:
            from . import ieee754  # optional module in same package
            # prefer their implementations if available
            self.unpack = getattr(ieee754, "f32_unpack", f32_unpack)
            self.pack = getattr(ieee754, "f32_pack", f32_pack)
        except Exception:
            self.unpack = f32_unpack
            self.pack = f32_pack

    def f32_unpack(self, bits32):
        return self.unpack(bits32)

    def f32_pack(self, sign, exp_unbs, sig_24):
        # reset flags per operation
        self.flags = {"inexact": False, "overflow": False, "underflow": False}
        out = self.pack(sign, exp_unbs, sig_24, self.flags)
        return out, self.flags