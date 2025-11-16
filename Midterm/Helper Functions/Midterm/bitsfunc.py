# bits.py
# functions for manipulating bit lists

def zbits(n):
    return [0] * n

def clone(b):
    return b[:]

def trim_msb(b):
    i = 0
    while i < len(b) - 1 and b[i] == 0:
        i += 1
    return b[i:]

def leftpad(b, n):
    if len(b) >= n:
        return b
    return [0] * (n - len(b)) + b

def rightpad(b, n):
    if len(b) >= n:
        return b
    return b + [0] * (n - len(b))

def equal_bits(a , b):
    n = max(len(a), len(b))
    a_padded = leftpad(a, n)
    b_padded = leftpad(b, n)
    for x, y in zip(a_padded, b_padded):
        if x != y:
            return False
    return True

def bits_or_func(a,b):
    n = max (len(a),len(b))
    a= leftpad(a,n)
    b= leftpad(b,n)
    return [(1 if (x or y)else 0) for x,y in zip(a,b)]

def bits_and_func(a,b):
    n = max (len(a),len(b))
    a= leftpad(a,n)
    b= leftpad(b,n)
    return [(1 if (x and y)else 0) for x,y in zip(a,b)]

def bits_xor_func(a,b):
    n = max (len(a),len(b))
    a= leftpad(a,n)
    b= leftpad(b,n)
    return [(x ^ y) for x,y in zip(a,b)]  
def bits_not_func(a):
    return [(1-x) for x in a]

def unsignedcmp(a,b):
    n = max (len(a),len(b))
    a= leftpad(a,n)
    b= leftpad(b,n)
    for x,y in zip(a,b):
        if x != y:
            return -1 if x < y else 1
    return 0

def groupof4(b):
    b = leftpad(b, ((len(b)+3)//4)*4)
    out = []
    HEX_CHARS = "0123456789ABCDEF"
    for i in range(0,len(b),4):
        nib = b[i:i+4]
        v = (nib[0]<<3) | (nib[1]<<2) | (nib[2]<<1) | nib[3]
        out.append(HEX_CHARS[v])
    return out

def bin(b, group = 4):
    s ="".join(str(x) for x in leftpad(b, ((len(b)+group-1)//group)*group))
    out = []
    for i,ch in enumerate(s):
        out.append(ch)
        if (i+1) % group == 0 and i+1 < len(s):
            out.append("_")
    return "".join(out)

def hex(b, width_chars=None):
    g = groupof4(b)
    if width_chars and len(g) < width_chars:
        g = ["0"] * (width_chars - len(g)) + g
    return "0x" + "".join(g)

def decimal_absstr(s):
    return s[1:] if s.startswith("-") else s

def zero_dec(ds):
    for ch in ds:
        if ch != "0": return False
    return True

def div2_dec(ds):
    q = []
    carry = 0
    for ch in ds:
        d = ord(ch) - ord('0')
        cur = carry + d
        qd = cur // 2
        rem = cur % 2
        q.append(chr(qd + ord('0')))
        carry = rem * 10
    qs = "".join(q).lstrip("0")
    if qs == "": qs = "0"
    remainder = carry // 10 
    return qs, remainder

def string_to_bits(ds):
    ds = ds.strip()
    if ds == "":
        return [0], False
    if ds == "+":
        ds = "0"
    neg = ds.startswith("-")
    mag = decimal_absstr(ds)
    bits_rev = []
    while not zero_dec(mag):
        mag, r = div2_dec(mag)
        bits_rev.append(r)
    if not bits_rev: bits_rev = [0]
    bits = list(reversed(bits_rev))
    return bits, neg