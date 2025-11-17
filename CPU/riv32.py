#!/usr/bin/env python3
import sys
import argparse

OPC_LOAD   = 0b0000011
OPC_STORE  = 0b0100011
OPC_OPIMM  = 0b0010011
OPC_OP     = 0b0110011
OPC_BRANCH = 0b1100011
OPC_JAL    = 0b1101111
OPC_JALR   = 0b1100111
OPC_LUI    = 0b0110111
OPC_AUIPC  = 0b0010111

DMEM_BASE  = 0x00010000
MMIO_TX    = 0x00020000

def sext(value, bits):
    sign = 1 << (bits - 1)
    return (value & (sign - 1)) - (value & sign)

def I_imm(instr):
    return sext((instr >> 20) & 0xFFF, 12)

def S_imm(instr):
    imm = ((instr >> 25) & 0x7F) << 5 | ((instr >> 7) & 0x1F)
    return sext(imm, 12)

def B_imm(instr):
    imm12   = (instr >> 31) & 0x1
    imm11   = (instr >> 7)  & 0x1
    imm10_5 = (instr >> 25) & 0x3F
    imm4_1  = (instr >> 8)  & 0xF
    imm = (imm12 << 12) | (imm11 << 11) | (imm10_5 << 5) | (imm4_1 << 1)
    return sext(imm, 13)

def U_imm(instr):
    return (instr & 0xFFFFF000)

def J_imm(instr):
    imm20   = (instr >> 31) & 0x1
    imm10_1 = (instr >> 21) & 0x3FF
    imm11   = (instr >> 20) & 0x1
    imm19_12= (instr >> 12) & 0xFF
    imm = (imm20 << 20) | (imm19_12 << 12) | (imm11 << 11) | (imm10_1 << 1)
    return sext(imm, 21)

class RV32ISim:
    def __init__(self, imem_words, max_steps=1000, trace=False):
        self.reg = [0] * 32
        self.pc  = 0
        self.imem = imem_words[:]
        self.dmem = {}
        self.max_steps = max_steps
        self.trace = trace
        self.halted = False

    def step(self):
        if self.pc % 4 != 0:
            raise RuntimeError(f"PC not aligned: 0x{self.pc:08X}")
        index = self.pc // 4
        if index < 0 or index >= len(self.imem):
            self.halted = True
            return
        instr = self.imem[index] & 0xFFFFFFFF
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F
        funct7b5 = (instr >> 30) & 0x1
        r = self.reg
        pc_next = (self.pc + 4) & 0xFFFFFFFF

        def wreg(dest, val):
            if dest != 0:
                self.reg[dest] = val & 0xFFFFFFFF

        if opcode == OPC_JAL and rd == 0 and J_imm(instr) == 0:
            if self.trace:
                print(f"[0x{self.pc:08X}] 0000006F (JAL x0, 0) → HALT LOOP detected, stopping.")
            self.halted = True
            return

        if opcode == OPC_OP:
            a = r[rs1]; b = r[rs2]
            if (funct3, funct7b5) == (0b000, 0): y = (a + b) & 0xFFFFFFFF
            elif (funct3, funct7b5) == (0b000, 1): y = (a - b) & 0xFFFFFFFF
            elif (funct3, funct7b5) == (0b111, 0): y = a & b
            elif (funct3, funct7b5) == (0b110, 0): y = a | b
            elif (funct3, funct7b5) == (0b100, 0): y = a ^ b
            elif (funct3, funct7b5) == (0b001, 0): y = (a << (b & 0x1F)) & 0xFFFFFFFF
            elif (funct3, funct7b5) == (0b101, 0): y = (a >> (b & 0x1F))
            elif (funct3, funct7b5) == (0b101, 1):
                sh = (b & 0x1F)
                y = ((a & 0xFFFFFFFF) >> sh) if (a & 0x80000000) == 0 else ((0xFFFFFFFF << (32 - sh)) | ((a & 0xFFFFFFFF) >> sh))
            elif funct3 == 0b010:
                y = 1 if ((a ^ 0x80000000) < (b ^ 0x80000000)) else 0
            elif funct3 == 0b011:
                y = 1 if (a & 0xFFFFFFFF) < (b & 0xFFFFFFFF) else 0
            else: y = 0
            wreg(rd, y)

        elif opcode == OPC_OPIMM:
            a = r[rs1]; imm = I_imm(instr)
            if funct3 == 0b000: y = (a + imm) & 0xFFFFFFFF
            elif funct3 == 0b111: y = a & imm
            elif funct3 == 0b110: y = a | imm
            elif funct3 == 0b100: y = a ^ imm
            elif funct3 == 0b001: y = (a << (imm & 0x1F)) & 0xFFFFFFFF
            elif funct3 == 0b101:
                shamt = imm & 0x1F
                if funct7b5 == 0: y = (a & 0xFFFFFFFF) >> shamt
                else:
                    if a & 0x80000000: y = ((a & 0xFFFFFFFF) >> shamt) | (0xFFFFFFFF << (32 - shamt))
                    else: y = (a & 0xFFFFFFFF) >> shamt
            elif funct3 == 0b010:
                y = 1 if ((a ^ 0x80000000) < (imm ^ 0x80000000)) else 0
            elif funct3 == 0b011:
                y = 1 if (a & 0xFFFFFFFF) < (imm & 0xFFFFFFFF) else 0
            else: y = 0
            wreg(rd, y)

        elif opcode == OPC_LOAD:
            imm = I_imm(instr)
            addr = (r[rs1] + imm) & 0xFFFFFFFF
            if funct3 == 0b000:
                val = self.dmem.get(addr, 0) & 0xFF
                if val & 0x80: val |= 0xFFFFFF00
            elif funct3 == 0b001:
                val = ((self.dmem.get(addr, 0) & 0xFF) | ((self.dmem.get(addr + 1, 0) & 0xFF) << 8))
                if val & 0x8000: val |= 0xFFFF0000
            elif funct3 == 0b010:
                val = ((self.dmem.get(addr, 0) & 0xFF) | ((self.dmem.get(addr + 1, 0) & 0xFF) << 8) | ((self.dmem.get(addr + 2, 0) & 0xFF) << 16) | ((self.dmem.get(addr + 3, 0) & 0xFF) << 24))
            elif funct3 == 0b100:
                val = self.dmem.get(addr, 0) & 0xFF
            elif funct3 == 0b101:
                val = ((self.dmem.get(addr, 0) & 0xFF) | ((self.dmem.get(addr + 1, 0) & 0xFF) << 8))
            else:
                val = 0
            wreg(rd, val)

        elif opcode == OPC_STORE:
            imm = S_imm(instr)
            addr = (r[rs1] + imm) & 0xFFFFFFFF
            data = r[rs2]
            if addr == MMIO_TX:
                sys.stdout.write(chr(data & 0xFF))
                sys.stdout.flush()
            elif funct3 == 0b000:
                self.dmem[addr] = data & 0xFF
            elif funct3 == 0b001:
                self.dmem[addr] = data & 0xFF
                self.dmem[addr + 1] = (data >> 8) & 0xFF
            elif funct3 == 0b010:
                self.dmem[addr] = data & 0xFF
                self.dmem[addr + 1] = (data >> 8) & 0xFF
                self.dmem[addr + 2] = (data >> 16) & 0xFF
                self.dmem[addr + 3] = (data >> 24) & 0xFF

        elif opcode == OPC_BRANCH:
            offset = B_imm(instr)
            take = False
            if funct3 == 0b000: take = (r[rs1] == r[rs2])
            elif funct3 == 0b001: take = (r[rs1] != r[rs2])
            if take: pc_next = (self.pc + offset) & 0xFFFFFFFF

        elif opcode == OPC_JAL:
            offset = J_imm(instr)
            wreg(rd, self.pc + 4)
            pc_next = (self.pc + offset) & 0xFFFFFFFF

        elif opcode == OPC_JALR:
            imm = I_imm(instr)
            t = (r[rs1] + imm) & 0xFFFFFFFF
            wreg(rd, self.pc + 4)
            pc_next = t & ~1

        elif opcode == OPC_LUI:
            imm = U_imm(instr)
            wreg(rd, imm)

        elif opcode == OPC_AUIPC:
            imm = U_imm(instr)
            val = (self.pc + imm) & 0xFFFFFFFF
            wreg(rd, val)

        self.pc = pc_next & 0xFFFFFFFF
        self.reg[0] = 0
        if self.trace:
            print(f"[0x{self.pc:08X}] instr=0x{instr:08X}")

def load_hex_words(path):
    words = []
    with open(path, 'r') as f:
        for line in f:
            s = line.strip()
            if not s: continue
            w = int(s, 16) & 0xFFFFFFFF
            words.append(w)
    return words

def main():
    ap = argparse.ArgumentParser(description="RV32I Python simulator (with extras)")
    ap.add_argument("hex", help="path to prog.hex")
    ap.add_argument("--max-steps", type=int, default=1000)
    ap.add_argument("--trace", action="store_true")
    args = ap.parse_args()
    imem = load_hex_words(args.hex)
    sim = RV32ISim(imem, max_steps=args.max_steps, trace=args.trace)
    steps = 0
    while not sim.halted and steps < sim.max_steps:
        sim.step()
        steps += 1
    print(f"\nExecuted {steps} steps. Final PC=0x{sim.pc:08X}")
    print("Registers:")
    for i in range(0, 32, 8):
        print(" ".join([f"x{j:02d}=0x{sim.reg[j]:08X}" for j in range(i, i+8)]))
    base = DMEM_BASE
    print("\nDMEM snapshot (0x00010000..0x0001000F):")
    for off in range(0, 16, 4):
        addr = base + off
        val = ((sim.dmem.get(addr, 0) & 0xFF)
              | ((sim.dmem.get(addr + 1, 0) & 0xFF) << 8)
              | ((sim.dmem.get(addr + 2, 0) & 0xFF) << 16)
              | ((sim.dmem.get(addr + 3, 0) & 0xFF) << 24))
        print(f"  [0x{addr:08X}] = 0x{val:08X}")

if __name__ == "__main__":
    main()
