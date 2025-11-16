import ieee754
from bitsfunc import leftpad
from adderfunc import addripple, twonegation
from shifter_func import shiftleftl, shiftrightl, shiftrighta

# alu.py
# Integer ALU (RISC-V style)

WIDTH = 32

# convert bit list to unsigned int
def bits_to_uint(b):
    val = 0
    for x in b:
        val = (val << 1) | x
    return val

# convert bit list to hex string
def bits_to_hex(b):
    b = leftpad(b, ((len(b)+3)//4)*4)
    out = ""
    HEX = "0123456789ABCDEF"
    for i in range(0, len(b), 4):
        nib = (b[i]<<3) | (b[i+1]<<2) | (b[i+2]<<1) | b[i+3]
        out += HEX[nib]
    return "0x" + out

def alu_add(a, b, width=WIDTH):
    a = leftpad(a, width)
    b = leftpad(b, width)
    res, c = addripple(a, b, cin=0, width=width)
    n = res[0]
    z = 1 if all(bit == 0 for bit in res) else 0
    s1, s2, sres = a[0], b[0], res[0]
    v = 1 if (s1 == s2 and sres != s1) else 0
    return res, (n, z, c, v)

def alu_sub(a, b, width=WIDTH):
    a = leftpad(a, width)
    b = leftpad(b, width)
    bneg = twonegation(b)
    res, c = addripple(a, bneg, cin=0, width=width)
    n = res[0]
    z = 1 if all(bit == 0 for bit in res) else 0
    s1, s2, sres = a[0], b[0], res[0]
    v = 1 if (s1 != s2 and sres != s1) else 0
    return res, (n, z, c, v)

def alu_and(a, b, width=WIDTH):
    a = leftpad(a, width)
    b = leftpad(b, width)
    res = [(x & y) for x, y in zip(a, b)]
    n = res[0]
    z = 1 if all(bit == 0 for bit in res) else 0
    return res, (n, z, 0, 0)

def alu_or(a, b, width=WIDTH):
    a = leftpad(a, width)
    b = leftpad(b, width)
    res = [(x | y) for x, y in zip(a, b)]
    n = res[0]
    z = 1 if all(bit == 0 for bit in res) else 0
    return res, (n, z, 0, 0)

def alu_xor(a, b, width=WIDTH):
    a = leftpad(a, width)
    b = leftpad(b, width)
    res = [(x ^ y) for x, y in zip(a, b)]
    n = res[0]
    z = 1 if all(bit == 0 for bit in res) else 0
    return res, (n, z, 0, 0)

def alu_sll(a, shamt_bits, width=WIDTH):
    shamt = bits_to_uint(leftpad(shamt_bits, width)[-5:])
    res = shiftleftl(leftpad(a, width), shamt)
    n = res[0]
    z = 1 if all(bit == 0 for bit in res) else 0
    return res, (n, z, 0, 0)

def alu_srl(a, shamt_bits, width=WIDTH):
    shamt = bits_to_uint(leftpad(shamt_bits, width)[-5:])
    res = shiftrightl(leftpad(a, width), shamt)
    n = res[0]
    z = 1 if all(bit == 0 for bit in res) else 0
    return res, (n, z, 0, 0)

def alu_sra(a, shamt_bits, width=WIDTH):
    shamt = bits_to_uint(leftpad(shamt_bits, width)[-5:])
    res = shiftrighta(leftpad(a, width), shamt)
    n = res[0]
    z = 1 if all(bit == 0 for bit in res) else 0
    return res, (n, z, 0, 0)

def alu_slt(a, b, width=WIDTH):
    res, (n, z, c, v) = alu_sub(a, b, width)
    lt = 1 if (n ^ v) else 0
    out = [0]*(width-1) + [lt]
    return out, (out[0], 1 if lt == 0 else 0, 0, 0)

def alu_sltu(a, b, width=WIDTH):
    a = leftpad(a, width)
    b = leftpad(b, width)
    _, c = addripple(a, twonegation(b), cin=0, width=width)
    lt = 1 if c == 0 else 0
    out = [0]*(width-1) + [lt]
    return out, (out[0], 1 if lt == 0 else 0, 0, 0)

def alu(op, rs1, rs2, width=WIDTH):
    op = op.upper()
    if op == "ADD": res, f = alu_add(rs1, rs2, width)
    elif op == "SUB": res, f = alu_sub(rs1, rs2, width)
    elif op == "AND": res, f = alu_and(rs1, rs2, width)
    elif op == "OR": res, f = alu_or(rs1, rs2, width)
    elif op == "XOR": res, f = alu_xor(rs1, rs2, width)
    elif op == "SLL": res, f = alu_sll(rs1, rs2, width)
    elif op == "SRL": res, f = alu_srl(rs1, rs2, width)
    elif op == "SRA": res, f = alu_sra(rs1, rs2, width)
    elif op == "SLT": res, f = alu_slt(rs1, rs2, width)
    elif op == "SLTU": res, f = alu_sltu(rs1, rs2, width)
    else: raise ValueError(f"Bad ALU op: {op}")
    n, z, c, v = f
    return {"bits": res, "hex": bits_to_hex(res), "flags": {"N": n, "Z": z, "C": c, "V": v}}
