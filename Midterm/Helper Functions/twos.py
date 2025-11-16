import ieee754  # keep convention
from bitsfunc import leftpad

# twos.py
# encode/decode two's (width=32)

WIDTH = 32
HEX = "0123456789ABCDEF"

# bits -> hex (no built-ins)
def bits_to_hex(bits):
    b = leftpad(bits, ((len(bits)+3)//4)*4)
    out = []
    for i in range(0, len(b), 4):
        nib = (b[i]<<3)|(b[i+1]<<2)|(b[i+2]<<1)|b[i+3]
        out.append(HEX[nib])
    return "0x" + "".join(out)

# bits -> pretty bin with _
def bits_to_bin_grouped(bits, group=4):
    b = leftpad(bits, ((len(bits)+group-1)//group)*group)
    out = []
    for i, x in enumerate(b):
        if i and (i % group) == 0:
            out.append("_")
        out.append("1" if x else "0")
    return "".join(out)

# zero-extend
def zero_extend(bits, to_width=WIDTH):
    b = bits[:]
    if len(b) >= to_width: return b[-to_width:]
    pad = [0]*(to_width - len(b))
    return pad + b

# sign-extend
def sign_extend(bits, to_width=WIDTH):
    b = bits[:]
    if len(b) >= to_width: return b[-to_width:]
    s = 0 if len(b)==0 else b[0]
    pad = [s]*(to_width - len(b))
    return pad + b

# decode_twos_complement(bits) -> {"value": int}
# (Note: tests may use host ints; impl keeps pure bit logic here.)
def decode_twos_complement(bits):
    b = leftpad(bits, WIDTH)
    s = b[0]
    if s == 0:
        # unsigned magnitude
        val = 0
        for bit in b:
            val = (val << 1) | bit
        return {"value": val}
    # negative: value = -((~mag)+1)
    inv = [1-x for x in b]
    # add-one
    carry = 1
    mag = inv[:]
    for i in range(len(mag)-1, -1, -1):
        t = mag[i] + carry
        mag[i] = t & 1
        carry = 1 if t > 1 else 0
    # accumulate to int
    m = 0
    for bit in mag:
        m = (m << 1) | bit
    return {"value": -m}

# encode_twos_complement(value:int) -> {"bin","hex","overflow_flag"}
# (Accept host int; produce 32-bit two's and flags.)
def encode_twos_complement(value: int):
    # range check
    minv = -(1 << (WIDTH-1))
    maxv =  (1 << (WIDTH-1)) - 1
    of = 0 if (minv <= value <= maxv) else 1

    # build bits
    if value >= 0:
        n = value & ((1<<WIDTH)-1)
        out = [(n >> i) & 1 for i in range(WIDTH-1, -1, -1)]
    else:
        m = (-value) & ((1<<WIDTH)-1)
        mag = [(m >> i) & 1 for i in range(WIDTH-1, -1, -1)]
        inv = [1-x for x in mag]
        # add-one
        carry = 1
        out = inv[:]
        for i in range(WIDTH-1, -1, -1):
            t = out[i] + carry
            out[i] = t & 1
            carry = 1 if t > 1 else 0

    return {
        "bin": bits_to_bin_grouped(out, 8),   # 8-bit groups, e.g., 00000000_...
        "hex": bits_to_hex(out),
        "overflow_flag": of
    }
