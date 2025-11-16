import ieee754
from bitsfunc import leftpad
from alu import alu
from mdu import mdu
from fpu import FPU

# coreapi.py
# thin API for ALU/MDU/FPU

WIDTH = 32

def hex_to_bits(h, width=WIDTH):
    h = h.strip().lower()
    if h.startswith("0x"): h = h[2:]
    n = int(h or "0", 16)
    return [(n >> i) & 1 for i in range(width - 1, -1, -1)]

def bits_to_hex(b):
    b = leftpad(b, ((len(b)+3)//4)*4)
    out = ""
    HEX = "0123456789ABCDEF"
    for i in range(0, len(b), 4):
        nib = (b[i]<<3)|(b[i+1]<<2)|(b[i+2]<<1)|b[i+3]
        out += HEX[nib]
    return "0x" + out

def core_alu(op, x_hex, y_hex, width=WIDTH):
    x = hex_to_bits(x_hex, width)
    y = hex_to_bits(y_hex, width)
    r = alu(op, x, y, width)
    return {"hex": bits_to_hex(r["bits"]), "flags": r["flags"]}

def core_mdu(op, x_hex, y_hex, width=WIDTH):
    x = hex_to_bits(x_hex, width)
    y = hex_to_bits(y_hex, width)
    r = mdu(op, x, y, width)
    return {"hex": bits_to_hex(r["bits"]), "flags": r["flags"]}

def core_fpu(op, ax_hex, bx_hex):
    f = FPU()
    a = hex_to_bits(ax_hex, 32)
    b = hex_to_bits(bx_hex, 32)
    opu = op.upper()
    if   opu == "ADD": out, flags = f.f32_add(a, b)
    elif opu == "SUB": out, flags = f.f32_sub(a, b)
    elif opu == "MUL": out, flags = f.f32_mul(a, b)
    elif opu == "DIV": out, flags = f.f32_div(a, b)
    else: raise ValueError("FPU op: ADD|SUB|MUL|DIV")
    return {"hex": bits_to_hex(out), "flags": flags}
