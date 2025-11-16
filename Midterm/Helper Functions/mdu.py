from bitsfunc import leftpad
from adderfunc import addripple
from twos import decode_twos_complement, encode_twos_complement

# mdu.py
# Multiplier/Divider Unit (RISC-V style)

WIDTH = 32

def bits_to_uint(b):
    """Convert bit list to unsigned int"""
    val = 0
    for x in b:
        val = (val << 1) | x
    return val

def bits_to_hex(b):
    """Convert bit list to hex string"""
    b = leftpad(b, ((len(b)+3)//4)*4)
    out = ""
    HEX = "0123456789ABCDEF"
    for i in range(0, len(b), 4):
        nib = (b[i]<<3) | (b[i+1]<<2) | (b[i+2]<<1) | b[i+3]
        out += HEX[nib]
    return "0x" + out

def bits_to_signed(b, width=WIDTH):
    """Convert bit list to signed int"""
    b_padded = leftpad(b, width)
    return decode_twos_complement(b_padded)["value"]

def signed_to_bits(val, width=WIDTH):
    """Convert signed int to bit list"""
    enc = encode_twos_complement(val)
    hex_str = enc["hex"][2:]  # Remove '0x'
    bits = []
    for ch in hex_str:
        nib = int(ch, 16)
        for i in range(3, -1, -1):
            bits.append((nib >> i) & 1)
    return bits[:width]

def mdu_mul(a, b, width=WIDTH):
    """Multiply two numbers (32-bit x 32-bit -> 32-bit lower half)"""
    a = leftpad(a, width)
    b = leftpad(b, width)
    a_val = bits_to_uint(a)
    b_val = bits_to_uint(b)
    result = (a_val * b_val) & ((1 << width) - 1)  # Keep lower 32 bits
    res_bits = [(result >> i) & 1 for i in range(width - 1, -1, -1)]
    z = 1 if result == 0 else 0
    return res_bits, (0, z, 0, 0)

def mdu_div(a, b, width=WIDTH):
    """Divide two signed numbers (signed division)"""
    a = leftpad(a, width)
    b = leftpad(b, width)
    a_signed = bits_to_signed(a, width)
    b_signed = bits_to_signed(b, width)
    
    if b_signed == 0:
        # Division by zero: return all 1s for signed divide
        res_bits = [1] * width
        return res_bits, (1, 0, 0, 1)
    
    result = abs(a_signed) // abs(b_signed)
    if (a_signed < 0) != (b_signed < 0):
        result = -result
    
    res_bits = signed_to_bits(result, width)
    z = 1 if result == 0 else 0
    return res_bits, (0, z, 0, 0)

def mdu_divu(a, b, width=WIDTH):
    """Divide two unsigned numbers"""
    a = leftpad(a, width)
    b = leftpad(b, width)
    a_val = bits_to_uint(a)
    b_val = bits_to_uint(b)
    
    if b_val == 0:
        # Division by zero: return all 1s
        res_bits = [1] * width
        return res_bits, (1, 0, 0, 1)
    
    result = a_val // b_val
    res_bits = [(result >> i) & 1 for i in range(width - 1, -1, -1)]
    z = 1 if result == 0 else 0
    return res_bits, (0, z, 0, 0)

def mdu_rem(a, b, width=WIDTH):
    """Remainder of signed division"""
    a = leftpad(a, width)
    b = leftpad(b, width)
    a_signed = bits_to_signed(a, width)
    b_signed = bits_to_signed(b, width)
    
    if b_signed == 0:
        # Division by zero: return dividend
        return a, (1, 0, 0, 1)
    
    result = a_signed % b_signed
    res_bits = signed_to_bits(result, width)
    z = 1 if result == 0 else 0
    return res_bits, (0, z, 0, 0)

def mdu_remu(a, b, width=WIDTH):
    """Remainder of unsigned division"""
    a = leftpad(a, width)
    b = leftpad(b, width)
    a_val = bits_to_uint(a)
    b_val = bits_to_uint(b)
    
    if b_val == 0:
        # Division by zero: return dividend
        return a, (1, 0, 0, 1)
    
    result = a_val % b_val
    res_bits = [(result >> i) & 1 for i in range(width - 1, -1, -1)]
    z = 1 if result == 0 else 0
    return res_bits, (0, z, 0, 0)

def mdu(op, rs1, rs2, width=WIDTH):
    """Main MDU dispatcher"""
    op = op.upper()
    if op == "MUL": res, f = mdu_mul(rs1, rs2, width)
    elif op == "DIV": res, f = mdu_div(rs1, rs2, width)
    elif op == "DIVU": res, f = mdu_divu(rs1, rs2, width)
    elif op == "REM": res, f = mdu_rem(rs1, rs2, width)
    elif op == "REMU": res, f = mdu_remu(rs1, rs2, width)
    else: raise ValueError(f"Bad MDU op: {op}")
    
    n, z, c, v = f
    return {"bits": res, "hex": bits_to_hex(res), "flags": {"N": n, "Z": z, "C": c, "V": v}}


