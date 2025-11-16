from bitsfunc import leftpad
 
def adder_full (a, b, Cin):
    s = (a ^ b) ^ Cin
    Cout = (a & b) | (Cin & (a ^ b))
    return (s, Cout)

def addripple(a_bits , b_bits, cin = 0, width = None):
    a = a_bits[:] 
    b = b_bits[:]
    if width is None:
        width = max(len(a), len(b))
        
    a = leftpad(a, width) 
    b = leftpad(b, width)
    
    aL = a[::-1]
    bL = b[::-1]
    outL = []
    c = cin
    for ai, bi in zip(aL, bL):
        si, c = adder_full(ai, bi, c)
        outL.append(si)
        

    return outL[::-1] , c

def twonegation(b):
    inv = [1 - x for x in b]
    s, c = addripple(inv, [0] * len(b), cin=1)
    return s

def flagadder(rs1, rs2, res, out):
    n = res[0]
    z = 1
    for x in res:
        if x == 1: 
            z = 0
            break
            
    c = out
    s1 = rs1[0]
    s2 = rs2[0]
    sres = res[0]
    v = 1 if (s1 == s2 and sres != s1) else 0
    
    return (n, z, c, v)
