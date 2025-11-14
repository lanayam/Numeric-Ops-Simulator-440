# Work on

# IEEE 754 Floating Point Representation Utilities
# Helpers for float32: split/pack/classify/round

from .bitsfunc import leftpad, zbits, unsignedcmp

BITS = 127      # sign bit position: 0-127 for float128
                # exponent (8bits, bias 127) & fraction (23 bits)

class Class:
    NAN = "NaN";    # Not a Number
    INF = "Inf";    # Infinity
    ZERO = "Zero";  # Zero
    SUBNORMAL = "Subnormal";  # Subnormal number
    NORMAL = "Normal";        # Normalized number

def _split_float32(x_bits):
    s = f[0]
    e = f[1:9]
    f = f[9:32]
    return s, e, f

def f32_unpack(x_bits):
    """
    Turning raw bits into a classifiable tuple
    (class, sign, unbiased exponent, significand_24)

    Here: 

    class: (Class.NAN, Class.INF, Class.ZERO, Class.SUBNORMAL, Class.NORMAL)
    sign: (0 = +, 1 = -)
    unbiased exponent: 127 (for normal) or -126 (for subnormal)
    significand_24: 24-bit significand including the implicit leading 1 for normal numbers
        - normals: [1] + fraction23 (which represents 1.00000)
        - subnormals: [0] + fraction23 (which represents 0.00000)
    """
    x, y, z = _split(x_bits)

    # Helper flags to see if the number is zero, subnormal, normal, infinity, or NaN
    all_ones = all(bit == '1' for bit in y)
    all_zeros = all(bit == '0' for bit in y)

    if all_ones:
        if any(z):          # here: if the fraction bits are not all zero, it's a NaN
            return (Class.NAN, x, 0, [1] + [0]*23)
        else:               # if the fraction bits are all zero, it's an infinity
            return (Class.INF, x, 0, [1], [0]*23)
        
    if all_zeros:
        if any(z):
            return (Class.SUBNORMAL, x, -126, [0] + z)
        else:
            return (Class.ZERO, x, -126, [0], [0]*23)
        

    # If it's a normal number, we need to convert the exponent to an 8-bit binary representation
    exp_conv = 0

    for bit in y:
        exp_conv = (exp_conv << 1) | bit      # left shifting then adding current bit

    return (Class.NORMAL, x, exp_conv - BITS, [1] + z)     # Return unbiased exponent and significand with the implicit leading 1

def int_to_exp(w):
    # Turn a small integer to an 8-bit binary exponent
    w = max(0, min(w, 255))  # Clamp to 8-bit range
    out = [0] * 8
    for i in range(7, -1, -1):
        out[i] = w & 1         # take lowest bit
        w >>= 1                # shift right by 1 to process the next bit
    return out

def bit32_pack(sign, exp_unbs, sig_24, f):
    """
    With a normalized sign, exponent, and significand, pack into 32-bit float representation.
        - a significand of 24 bits (including the implicit leading 1) & an unbiased exponent
        - round to nearest even to 23 fraction bits
        - then handle special cases like zero, infinity, and NaN
        - return the packed 32-bit representation

    With Inputs of 
    - sign: 0 or 1
    - exp_unbs: unbiased exponent (integer)
    - sig_24: a list of 24 bits representing the significand (including the implicit leading 1 for normals)

    With an Output of 
    - a 32-bit integer representing the packed float
        - 32 bit float pattern: [sign] + [8-bit exponent] + [23-bit fraction]
    """

    # 1: keep the top 24 bits (1 + 23) and everything else for rounding

    kept_bits = sig_24[:24]
    rest_bits = sig_24[24:]

    dropped_bits = tail[0] if len(rest_bits) > 0 else 0
    round_up = rest_bits[1] if len(rest_bits) > 1 else 0
    sticky_bit = 1 if any(rest_bits[2:]) else 0

    # 2: round to nearest even
    # if the dropped bit is 1 and either the round up bit is 1 or the sticky bit is 1, we need to round up
    # if the dropped bit is 1 and the round up bit is 0 and the sticky bit is 0, we only round up if the 
    #       last kept bit is 1 (to make it even)

    increment = 1 if dropped_bits == 1 and (round_up == 1 or sticky_bit == 1 or kept_bits[-1] == 1) else 0
    
    if increment:
        # will manually add 1 to the kept bits, handling any carry that may occur
        carry = 1
        for i in range(23, -1, -1):
            sticky_bit = kept_bits[i] + carry
            carry = kept_bits[i] & carry
            kept_bits[i] = sticky_bit

        if carry == 1:
            kept_bits = [1] + kept_bits[:-1]  # Shift right and add leading 1
            exp_unbs += 1  # Increment the exponent for the carry
        # 

    # 3: Add bias to the exponent and check for overflow or underflow
    exp_biased = exp_unbs + BITS

    if exp_biased >= 255:
        f["overflow"] = True
        f["inexact"] = True         # Inexact flag when the result cannot be represented exactly in float32
        return [sign] + [1]*8 + [0]*23  # Return infinity representation
    
    # Now if exponent is less than or equal to 0, we need to handle subnormal numbers or zero
    if exp_biased <= 0:
        k = 1 - exp_biased  # Number of bits to shift for subnormal representation
        m = kept_bits + [0] * k  # Shift the significand to the right by k bits
        sticky_bit = 0
        for _ in range(k):
            dropped_bits = m[-1]
            m = m[:-1]  # Shift right by 1
            if dropped_bits == 1:
                sticky_bit = 1  # Set sticky bit if any dropped bit is 1

        tail = m[24:]  # Get the bits that were shifted out for rounding
        kept = m[:24]  # Get the top 24 bits for the significand

        G = 0
        R = 0
        S = 0

        # if there is at least 1 dropped bit, that bit is Guard
        if len(tail) > 0:
            G = tail[0]

        # if there are at least 2 dropped bits, the second one is Round
        if len(tail) > 1:
            R = tail[1]

        # if there are more dropped bits after that, OR them together → Sticky
        if len(tail) > 2:
            if any(tail[2:]):
                S = 1

        # also include the "sticky" from earlier shifts (k shifts)
        if sticky_bit == 1:
            S = 1

       # 4: Round to nearest even
    increment2 = 0
    if G == 1 and (R == 1 or S == 1 or kept[-1] == 1):
        increment2 = 1

    if increment2 == 1:
        carry = 1
        for i in range(23, -1, -1):
            sticky_bit = kept[i] + carry
            carry = kept[i] & carry
            kept[i] = sticky_bit

        f["underflow"] = True

    # subnormal numbers have an exponent of 0 and a significand that is shifted right by the number of bits needed to represent the subnormal
    return [sign] + [0]*8 + kept[:23]
        