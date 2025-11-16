import ieee754  # prefer ieee754 pack/unpack
from bitsfunc import leftpad
from adderfunc import addripple
from shifter_func import shiftleftl, shiftrightl

# fpu.py
# float32: add/sub/mul via bit steps (RNE). returns (bits, flags, trace)

BIAS = 127

class Class:
    NAN="NaN"; INF="Inf"; ZERO="Zero"; SUB="Subnormal"; NORM="Normal"

# helpers
def _bits_to_uint(b):
    v=0
    for x in b: v=(v<<1)|x
    return v

def _uint_to_bits(u, w):
    return [(u>>i)&1 for i in range(w-1,-1,-1)]

def _add1(bits):
    out=bits[:]; c=1
    for i in range(len(out)-1,-1,-1):
        t=out[i]+c
        out[i]=t&1; c=1 if t>1 else 0
        if c==0: break
    return out,c

def _classify(x):
    s,e,f = x[0], x[1:9], x[9:]
    eo = all(b==0 for b in e); e1 = all(b==1 for b in e)
    if e1 and any(f): return (Class.NAN,s,None,[1]+[0]*23)
    if e1:           return (Class.INF,s,None,[1]+[0]*23)
    if eo and any(f):return (Class.SUB,s,-126,[0]+f)
    if eo:           return (Class.ZERO,s,-126,[0]+[0]*23)
    ev=_bits_to_uint(e)-BIAS
    return (Class.NORM,s,ev,[1]+f)

def _int_to_exp(w):
    w = 0 if w<0 else (255 if w>255 else w)
    return _uint_to_bits(w,8)

def _pack(sign, e_unb, sig_bits, flags):
    # sig_bits: 24 kept + tail (optional)
    sig = sig_bits[:]
    if len(sig)<24: sig += [0]*(24-len(sig))
    kept = sig[:24]
    rest = sig[24:]

    g = rest[0] if len(rest)>=1 else 0
    r = rest[1] if len(rest)>=2 else 0
    s = 1 if any(rest[2:]) else 0
    if any(rest): flags["inexact"]=True

    inc = 1 if (g==1 and (r==1 or s==1 or kept[-1]==1)) else 0
    if inc:
        kept, c = _add1(kept)
        if c:
            kept = [1]+kept[:-1]
            e_unb += 1
        flags["inexact"]=True

    eb = e_unb + BIAS

    if eb >= 255:
        flags["overflow"]=True; flags["inexact"]=True
        return [sign]+[1]*8 + [0]*23

    if eb <= 0:
        # subnormal/zero path
        shift = 1 - eb
        ext = kept + rest
        if shift >= len(ext):
            shifted=[0]*len(ext); sticky = 1 if any(ext) else 0
        else:
            shifted = ext[:len(ext)-shift]
            dropped = ext[len(ext)-shift:]
            sticky = 1 if any(dropped) else 0

        top24 = shifted[:24] if len(shifted)>=24 else ([0]*(24-len(shifted))+shifted)
        tail  = shifted[24:] if len(shifted)>24 else []
        g2 = tail[0] if len(tail)>=1 else 0
        r2 = tail[1] if len(tail)>=2 else 0
        s2 = 1 if sticky or any(tail[2:]) else 0

        inc2 = 1 if (g2==1 and (r2==1 or s2==1 or top24[-1]==1)) else 0
        if inc2:
            top24, c2 = _add1(top24)
            if c2:
                eb = 1
                frac = top24[1:24]
                flags["inexact"]=True
                return [sign]+_int_to_exp(eb)+frac
            flags["inexact"]=True

        flags["underflow"]=True
        frac = top24[1:24]
        return [sign]+[0]*8 + frac

    exp_bits = _int_to_exp(eb)
    frac = kept[1:24]
    return [sign]+exp_bits+frac

class FPU:
    def __init__(self):
        self.flags = {"inexact":False,"overflow":False,"underflow":False,"invalid":False}

    # unpack using ieee754 helpers if present
    def _unpack(self, x):
        try:
            return ieee754.f32_unpack(x)
        except Exception:
            return _classify(x)

    def _reset(self):
        self.flags = {"inexact":False,"overflow":False,"underflow":False,"invalid":False}

    # add/sub (op = +1 for add, -1 for sub)
    def _addsub(self, a, b, sub=False):
        tr=[]
        ca, sa, ea, ma = self._unpack(a)
        cb, sb, eb, mb = self._unpack(b)
        tr.append({"state":"CLASS", "ca":ca, "cb":cb})

        # NaNs
        if ca==Class.NAN or cb==Class.NAN:
            self.flags["invalid"]=True
            return ([0,1,1,1,1,1,1,1,1]+[1]+[0]*22, self.flags, tr)

        # inf cases
        if ca==Class.INF and cb==Class.INF and (sa != (sb^sub)):
            self.flags["invalid"]=True
            return ([0,1,1,1,1,1,1,1,1]+[1]+[0]*22, self.flags, tr)
        if ca==Class.INF: return ([sa]+[1]*8+[0]*23, self.flags, tr)
        if cb==Class.INF: return ([(sb^sub)]+[1]*8+[0]*23, self.flags, tr)

        # zeros/subnormals handled by align below; build aligned mantissas
        # extend mantissas with 2-bit tail for guard/round
        ia = _bits_to_uint(ma)
        ib = _bits_to_uint(mb)

        # align exponents (right shift smaller mantissa)
        if ea > eb:
            d = ea - eb
            tr.append({"state":"ALIGN","shift_b":d})
            # shift b by d with sticky
            b_ext = mb[:] + [0,0]
            sticky = 0
            for _ in range(d):
                sticky |= b_ext[-1]
                b_ext = [0]+b_ext[:-1]
            b_ext[-1] |= sticky
            mb_al = b_ext
            ma_al = ma[:] + [0,0]
            E = ea
        elif eb > ea:
            d = eb - ea
            tr.append({"state":"ALIGN","shift_a":d})
            a_ext = ma[:] + [0,0]
            sticky = 0
            for _ in range(d):
                sticky |= a_ext[-1]
                a_ext = [0]+a_ext[:-1]
            a_ext[-1] |= sticky
            ma_al = a_ext
            mb_al = mb[:] + [0,0]
            E = eb
        else:
            ma_al = ma[:] + [0,0]
            mb_al = mb[:] + [0,0]
            E = ea

        # add or subtract mantissas
        sb_eff = sb ^ (1 if sub else 0)
        tr.append({"state":"OP", "sa":sa, "sb":sb_eff})
        ia = _bits_to_uint(ma_al); ib = _bits_to_uint(mb_al)
        if sa == sb_eff:
            # same sign -> add
            sum_bits = _uint_to_bits(ia+ib, len(ma_al)+1)  # one extra headroom
            sgn = sa
        else:
            # different sign -> subtract larger - smaller
            if ia >= ib:
                diff = ia - ib
                sgn = sa
            else:
                diff = ib - ia
                sgn = sb_eff
            sum_bits = _uint_to_bits(diff, len(ma_al)+1)

        tr.append({"state":"SUM", "sig":sum_bits[:28]})

        # normalize
        # case: carry at top
        if sum_bits[0]==1:
            # shift right 1, exponent++
            gr = sum_bits[-2:]
            kept24 = sum_bits[:-1]
            E += 1
            sig_for_pack = kept24 + gr
        else:
            # shift left until leading 1 at index 0 (or zero)
            k = 0
            while k < len(sum_bits) and sum_bits[k]==0:
                k += 1
            if k == len(sum_bits):
                # zero
                return ([sgn]+[0]*8+[0]*23, self.flags, tr)
            # left shift by k
            shifted = sum_bits[k:] + [0]*k
            E -= k
            gr = [0,0]
            kept24 = shifted[:24]
            tail = shifted[24:26]
            if len(tail)>=2: gr = tail[:2]
            elif len(tail)==1: gr=[tail[0],0]
            sig_for_pack = kept24 + gr

        tr.append({"state":"NORM", "E":E, "kept":sig_for_pack[:24], "gr":sig_for_pack[24:]})
        out = _pack(sgn, E, sig_for_pack, self.flags)
        tr.append({"state":"PACK"})
        return (out, self.flags, tr)

    def f32_add(self, a_bits, b_bits):
        self._reset()
        return self._addsub(leftpad(a_bits,32), leftpad(b_bits,32), sub=False)

    def f32_sub(self, a_bits, b_bits):
        self._reset()
        return self._addsub(leftpad(a_bits,32), leftpad(b_bits,32), sub=True)

    def f32_mul(self, a_bits, b_bits):
        self._reset()
        tr=[]
        ca, sa, ea, ma = self._unpack(leftpad(a_bits,32))
        cb, sb, eb, mb = self._unpack(leftpad(b_bits,32))
        tr.append({"state":"CLASS","ca":ca,"cb":cb})

        # NaNs
        if ca==Class.NAN or cb==Class.NAN:
            self.flags["invalid"]=True
            return ([0,1,1,1,1,1,1,1,1]+[1]+[0]*22, self.flags, tr)
        # 0 * inf
        if (ca in (Class.ZERO,Class.SUB) and cb==Class.INF) or (cb in (Class.ZERO,Class.SUB) and ca==Class.INF):
            self.flags["invalid"]=True
            return ([0,1,1,1,1,1,1,1,1]+[1]+[0]*22, self.flags, tr)
        # propagate inf
        if ca==Class.INF or cb==Class.INF:
            s = sa ^ sb
            return ([s]+[1]*8+[0]*23, self.flags, tr)
        # zero shortcut
        if ca in (Class.ZERO,Class.SUB) or cb in (Class.ZERO,Class.SUB):
            s = sa ^ sb
            return ([s]+[0]*8+[0]*23, self.flags, tr)

        s = sa ^ sb
        E = ea + eb
        # 24x24 -> 48 via shift-add on bits (simple loop)
        a24 = ma[:]   # [1] + frac
        b24 = mb[:]
        prod = [0]*48

        # shift-add: for i from LSB of b24, add (a24 << (47-(i_pos)))
        # we implement via integer-ish accumulation on bit arrays using addripple
        for i in range(23,-1,-1):
            if b24[i]==1:
                # align a24 into 48
                shift = 23 - i
                left = a24 + [0]*shift
                left = ([0]*(48-len(left))) + left
                # add into prod
                res, _ = addripple(prod, left, cin=0, width=48)
                prod = res

        tr.append({"state":"MUL48","sig48":prod[:28]})
        # normalize: product in [1,4)
        if prod[0]==1:
            # >=2 -> shift right 1
            gr = prod[-2:]
            kept24 = prod[:24]
            E += 1
            sig_for_pack = kept24 + gr
        else:
            # already ~1.x
            kept24 = prod[1:25]
            gr = prod[25:27]
            sig_for_pack = kept24 + (gr if len(gr)==2 else [0,0])

        tr.append({"state":"NORM","E":E,"kept":sig_for_pack[:24],"gr":sig_for_pack[24:]})
        out = _pack(s, E, sig_for_pack, self.flags)
        tr.append({"state":"PACK"})
        return (out, self.flags, tr)
