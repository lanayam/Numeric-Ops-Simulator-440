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
def sext (value, bits):
    sign = 1 << (bits - 1)
    return (value & (sign -1)) - (value & sign)
def I_imm (instr):
    return sext((instr >> 20) & 0xFFF, 12)
def S_imm(instr):
    imm = ((instr >> 25) & 0x7F) << 5 | ((instr >> 7) & 0x1F)
    return sext(imm, 12)

def B_imm(instr):
    # imm[12|10:5|4:1|11|0] packed as B-type; LSB is zero after forming
    imm12   = (instr >> 31) & 0x1
    imm11   = (instr >> 7)  & 0x1
    imm10_5 = (instr >> 25) & 0x3F
    imm4_1  = (instr >> 8)  & 0xF
    imm = (imm12 << 12) | (imm11 << 11) | (imm10_5 << 5) | (imm4_1 << 1)
    return sext(imm, 13)

def U_imm(instr):
    return (instr & 0xFFFFF000)  # upper 20 bits, already aligned

def J_imm(instr):
    # J-type: [20|10:1|11|19:12], LSB is zero after forming
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
        self.imem = imem_words[:]  # list of 32-bit words
        self.dmem = {}             # simple dict for word-addressed DMEM (aligned)
        self.max_steps = max_steps
        self.trace = trace
        self.halted = False

    def load_dmem(self, addr):
        if addr % 4 != 0:
            raise RuntimeError(f"Unaligned LW at 0x{addr:08X}")
        if addr < DMEM_BASE:
            # unmapped returns 0 per our simple model
            return 0
        return self.dmem.get(addr, 0)

    def store_dmem(self, addr, data):
        if addr % 4 != 0:
            raise RuntimeError(f"Unaligned SW at 0x{addr:08X}")
        if addr < DMEM_BASE:
            # ignore unmapped stores
            return
        self.dmem[addr] = data & 0xFFFFFFFF

    def step(self):
        if self.pc % 4 != 0:
            raise RuntimeError(f"PC not aligned: 0x{self.pc:08X}")

        index = self.pc // 4
        if index < 0 or index >= len(self.imem):
            # PC fell off program; halt
            self.halted = True
            return

        instr = self.imem[index] & 0xFFFFFFFF
        opcode = instr & 0x7F
        rd  = (instr >> 7)  & 0x1F
        funct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F
        funct7b5 = (instr >> 30) & 0x1

        r = self.reg  # alias
        pc_next = self.pc + 4  # default

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
            if   (funct3, funct7b5) == (0b000, 0): y = (a + b) & 0xFFFFFFFF         # add
            elif (funct3, funct7b5) == (0b000, 1): y = (a - b) & 0xFFFFFFFF         # sub
            elif (funct3, funct7b5) == (0b111, 0): y = a & b                         # and
            elif (funct3, funct7b5) == (0b110, 0): y = a | b                         # or
            elif (funct3, funct7b5) == (0b100, 0): y = a ^ b                         # xor
            elif (funct3, funct7b5) == (0b001, 0): y = (a << (b & 0x1F)) & 0xFFFFFFFF# sll
            elif (funct3, funct7b5) == (0b101, 0): y = (a >> (b & 0x1F))             # srl
            elif (funct3, funct7b5) == (0b101, 1):
                sh = (b & 0x1F)
                y = ((a & 0xFFFFFFFF) >> sh) if (a & 0x80000000)==0 else ((0xFFFFFFFF << (32-sh)) | ((a & 0xFFFFFFFF) >> sh))  # sra
            else: y = 0
            wreg(rd, y)

        elif opcode == OPC_OPIMM:  # I-type ALU
            a = r[rs1]; imm = I_imm(instr)
            if   funct3 == 0b000: y = (a + imm) & 0xFFFFFFFF                   # addi
            elif funct3 == 0b111: y = a & imm                                   # andi
            elif funct3 == 0b110: y = a | imm                                   # ori
            elif funct3 == 0b100: y = a ^ imm                                   # xori
            elif funct3 == 0b001: y = (a << (imm & 0x1F)) & 0xFFFFFFFF          # slli
            elif funct3 == 0b101:
                shamt = imm & 0x1F
                if funct7b5 == 0:
                    # srli
                    y = (a & 0xFFFFFFFF) >> shamt
                else:
                    # srai (arithmetic, preserve sign)
                    if a & 0x80000000:
                        y = ((a & 0xFFFFFFFF) >> shamt) | (0xFFFFFFFF << (32 - shamt))
                    else:
                        y = (a & 0xFFFFFFFF) >> shamt
            else: y = 0
            wreg(rd, y)

        # Loads and Stores
        elif opcode == OPC_LOAD:
            imm  = I_imm(instr)
            addr = (r[rs1] + imm) & 0xFFFFFFFF

            if funct3 == 0b010:  # LW
                val = self.load_dmem(addr)  # will check alignment + base
                wreg(rd, val)
            else:
                # unsupported load type in this minimal subset
                pass


        elif opcode == OPC_STORE:
            imm  = S_imm(instr)
            addr = (r[rs1] + imm) & 0xFFFFFFFF

            if funct3 == 0b010:  # SW
                self.store_dmem(addr, r[rs2])
            else:
                # unsupported store type in this minimal subset
                pass

        # BRANCH: beq, bne
        elif opcode == OPC_BRANCH:
            offset = B_imm(instr)
            take = False

            if funct3 == 0b000:       # BEQ
                take = (r[rs1] == r[rs2])
            elif funct3 == 0b001:     # BNE
                take = (r[rs1] != r[rs2])
            else:
                take = False

            if take:
                pc_next = (self.pc + offset) & 0xFFFFFFFF

        # JAL
        elif opcode == OPC_JAL:
            offset = J_imm(instr)
            # link
            wreg(rd, self.pc + 4)
            # jump target
            pc_next = (self.pc + offset) & 0xFFFFFFFF

        # JALR
        elif opcode == OPC_JALR:
            imm  = I_imm(instr)
            t    = (r[rs1] + imm) & 0xFFFFFFFF
            wreg(rd, self.pc + 4)
            pc_next = t & ~1  # clear bit 0 per RISC-V spec

        # LUI
        elif opcode == OPC_LUI:
            imm = U_imm(instr)
            wreg(rd, imm)

        # AUIPC
        elif opcode == OPC_AUIPC:
            imm = U_imm(instr)
            val = (self.pc + imm) & 0xFFFFFFFF
            wreg(rd, val)

        # else: unknown opcode so treat as NOP (pc just moves on)

        # commit PC and enforce x0 = 0
        self.pc = pc_next & 0xFFFFFFFF
        self.reg[0] = 0

        if self.trace:
            print(f"[0x{self.pc:08X}] instr=0x{instr:08X}")
