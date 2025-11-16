import ieee754  # always prefer ieee754 first
from bitsfunc import leftpad

# IEEE 754 Floating Point Representation Utilities for float32
# Helpers: split/pack/classify/round and FPU operations

BIAS = 127

class Class:
    NAN = "NaN"
    INF = "Inf"
    ZERO = "Zero"
    SUBNORMAL = "Subnormal"
    NORMAL = "Normal"

# --------------------------------------------------------------------
# bit manipulation helpers
# --------------------------------------------------------------------
def split_float32(x_bits):
    """Expect x_bits as iterable/list of 32 bits [b31(sign), b30..b23(exp), b22..b0(frac)]"""
    if len(x_bits) != 32:
        raise ValueError("split_float32 expects 32 bits")
    sign = x_bits[0]
    exp = x_bits[1:9]
    frac = x_bits[9:32]
    return sign, exp, frac

def _bits_to_uint(bits):
    x = 0
    for b in bits:
        x = (x << 1) | (1 if b else 0)
    return x

def _uint_to_bits(x, width):
    return [(x >> i) & 1 for i in range(width-1, -1, -1)]

# --------------------------------------------------------------------
# Main FPU class using ieee754 as reference for packing/unpacking
# --------------------------------------------------------------------
class FPU:
    def __init__(self):
        self.flags = {"inexact": False, "overflow": False, "underflow": False}
        # Always prefer ieee754 for pack/unpack
        self.unpack = getattr(ieee754, "f32_unpack", None)
        self.pack = getattr(ieee754, "f32_pack", None)
        if self.unpack is None or self.pack is None:
            # fallback to local definitions if ieee754 not found
            from fpu import f32_unpack, f32_pack
            self.unpack = f32_unpack
            self.pack = f32_pack

    def f32_unpack(self, bits32):
        return self.unpack(bits32)

    def f32_pack(self, sign, exp_unbs, sig_24):
        self.flags = {"inexact": False, "overflow": False, "underflow": False}
        out = self.pack(sign, exp_unbs, sig_24, self.flags)
        return out, self.flags

    # ----------------------------------------------------------------
    # IEEE 754 Arithmetic (round-to-nearest, ties-to-even)
    # ----------------------------------------------------------------
    def f32_add(self, a_bits, b_bits):
        ca, sa, ea, ma = self.f32_unpack(a_bits)
        cb, sb, eb, mb = self.f32_unpack(b_bits)

        # Handle NaN, Inf, Zero
        if ca == Class.NAN: return (a_bits, {"inexact": True})
        if cb == Class.NAN: return (b_bits, {"inexact": True})
        if ca == Class.INF and cb == Class.INF and sa != sb:
            # +Inf + -Inf = NaN
            return ([0,1,1,1,1,1,1,1,1]+[1]+[0]*22, {"inexact": True})
        if ca == Class.INF: return (a_bits, {"inexact": False})
        if cb == Class.INF: return (b_bits, {"inexact": False})
        if ca == Class.ZERO: return (b_bits, {"inexact": False})
        if cb == Class.ZERO: return (a_bits, {"inexact": False})

        # Convert mantissas to integers
        ia = _bits_to_uint(ma)
        ib = _bits_to_uint(mb)
        sgn = sa
        e = ea

        # Align exponents
        if ea > eb:
            shift = ea - eb
            ib >>= min(shift, 31)
            e = ea
        elif eb > ea:
            shift = eb - ea
            ia >>= min(shift, 31)
            e = eb

        # Add/Sub based on sign
        if sa == sb:
            sig = ia + ib
            sgn = sa
            if sig >= (1 << 24):
                sig >>= 1
                e += 1
        else:
            if ia >= ib:
                sig = ia - ib
                sgn = sa
            else:
                sig = ib - ia
                sgn = sb
            while sig and sig < (1 << 23):
                sig <<= 1
                e -= 1

        if sig == 0:
            return ([sgn]+[0]*8+[0]*23, {"inexact": False})

        sig_bits = _uint_to_bits(sig, 24)
        out, flags = self.f32_pack(sgn, e, sig_bits)
        return out, flags

    def f32_sub(self, a_bits, b_bits):
        bb = b_bits[:]
        bb[0] ^= 1
        return self.f32_add(a_bits, bb)

    def f32_mul(self, a_bits, b_bits):
        ca, sa, ea, ma = self.f32_unpack(a_bits)
        cb, sb, eb, mb = self.f32_unpack(b_bits)
        if ca == Class.NAN: return (a_bits, {"inexact": True})
        if cb == Class.NAN: return (b_bits, {"inexact": True})
        if (ca == Class.INF and cb == Class.ZERO) or (cb == Class.INF and ca == Class.ZERO):
            return ([0,1,1,1,1,1,1,1,1]+[1]+[0]*22, {"inexact": True})
        if ca == Class.INF or cb == Class.INF:
            sgn = sa ^ sb
            return ([sgn]+[1]*8+[0]*23, {"overflow": True})
        if ca == Class.ZERO or cb == Class.ZERO:
            sgn = sa ^ sb
            return ([sgn]+[0]*8+[0]*23, {"underflow": True})

        sgn = sa ^ sb
        ia = _bits_to_uint(ma)
        ib = _bits_to_uint(mb)
        e = ea + eb

        prod = ia * ib
        if (prod >> 47) == 1:
            prod >>= 1
            e += 1
        frac = (prod >> 23) & ((1 << 24) - 1)
        out, flags = self.f32_pack(sgn, e, _uint_to_bits(frac, 24))
        return out, flags

    def f32_div(self, a_bits, b_bits):
        ca, sa, ea, ma = self.f32_unpack(a_bits)
        cb, sb, eb, mb = self.f32_unpack(b_bits)
        if ca == Class.NAN: return (a_bits, {"inexact": True})
        if cb == Class.NAN: return (b_bits, {"inexact": True})
        if (ca == Class.INF and cb == Class.INF) or (ca == Class.ZERO and cb == Class.ZERO):
            return ([0,1,1,1,1,1,1,1,1]+[1]+[0]*22, {"inexact": True})
        if ca == Class.INF:
            sgn = sa ^ sb
            return ([sgn]+[1]*8+[0]*23, {"overflow": True})
        if cb == Class.INF:
            sgn = sa ^ sb
            return ([sgn]+[0]*8+[0]*23, {"underflow": True})
        if cb == Class.ZERO:
            sgn = sa ^ sb
            return ([sgn]+[1]*8+[0]*23, {"overflow": True})
        if ca == Class.ZERO:
            sgn = sa ^ sb
            return ([sgn]+[0]*8+[0]*23, {"underflow": True})

        sgn = sa ^ sb
        ia = _bits_to_uint(ma)
        ib = _bits_to_uint(mb)
        e = ea - eb
        quo = (ia << 23) // ib
        frac = quo & ((1 << 24) - 1)
        out, flags = self.f32_pack(sgn, e, _uint_to_bits(frac, 24))
        return out, flags
