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

        if opcode == OPC_JAL and rd == 0 and get_J_imm(instr) == 0:
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
            a = r[rs1]; imm = get_I_imm(instr)
            if   funct3 == 0b000: y = (a + imm) & 0xFFFFFFFF                   # addi
            elif funct3 == 0b111: y = a & imm                                   # andi
            elif funct3 == 0b110: y = a | imm                                   # ori
            elif funct3 == 0b100: y = a ^ imm                                   # xori
            elif funct3 == 0b001: y = (a << (imm & 0x1F)) & 0xFFFFFFFF          # slli
            elif funct3 == 0b101:
# =====================================================================
# TODO GUIDE (next ~125 lines as comments) — partner checklist
# Work is complete up through:  `elif funct3 == 0b101:` (OPIMM SRLI/SRAI case).
# The notes below tell you EXACTLY what to ADD / MODIFY / REMOVE next.
# Copy this whole block right after your current code location.
# =====================================================================

# --- A) COMPLETE STORE VARIANTS (SB/SH) ---------------------------------------
# ADD: In the OPC_STORE handler, add support for SB (funct3=000) and SH (funct3=001)
#      using *byte-addressable* memory semantics. Keep SW (010) as you already have.
#
# 1) If you still use a "word-only" dict DMEM, switch to a byte-addressable class
#    (see Section C below) before adding SB/SH, otherwise partial stores won't behave.
#
# 2) Pseudocode inside OPC_STORE:
#    - imm  = get_S_imm(instr)
#    - addr = (reg[rs1] + imm) & 0xFFFFFFFF
#    - if funct3 == 0b000:   # SB
#         dmem.store8(addr, reg[rs2] & 0xFF)
#      elif funct3 == 0b001: # SH
#         require 2-byte alignment (raise on misalign)
#         dmem.store16(addr, reg[rs2] & 0xFFFF)
#      elif funct3 == 0b010: # SW (already done)
#         require 4-byte alignment
#         dmem.store32(addr, reg[rs2] & 0xFFFFFFFF)
#    - advance PC by 4; enforce x0=0
#
# 3) TEST quickly:
#    - create a tiny hex that does LUI a base (0x00020000), SB a byte 'A',
#      LB it back, check correct sign-extension.

# --- B) COMPLETE LOAD VARIANTS (LB/LH/LBU/LHU) -------------------------------
# ADD: In OPC_LOAD handler, support:
#   LB  (funct3=000)  → sign-extend 8-bit
#   LH  (funct3=001)  → sign-extend 16-bit (require halfword alignment)
#   LBU (funct3=100)  → zero-extend 8-bit
#   LHU (funct3=101)  → zero-extend 16-bit (require halfword alignment)
#
# Pseudocode inside OPC_LOAD:
#   imm  = get_I_imm(instr)
#   addr = (reg[rs1] + imm) & 0xFFFFFFFF
#   if funct3 == 0b000: val = sext(dmem.load8(addr), 8)
#   elif funct3 == 0b001: require align2; val = sext(dmem.load16(addr), 16)
#   elif funct3 == 0b010: (LW you already did) require align4; val = dmem.load32(addr)
#   elif funct3 == 0b100: val = zext(dmem.load8(addr), 8)
#   elif funct3 == 0b101: require align2; val = zext(dmem.load16(addr), 16)
#   write-back to rd if rd != 0; advance PC by 4; enforce x0=0
#
# NOTE: Keep unaligned detection consistent with your store rules.

# --- C) SWITCH DMEM TO BYTE-ADDRESSABLE BACKING ------------------------------
# ADD: A small class that stores bytes (addr→byte), little-endian assembly for 16/32-bit.
#
# class ByteAddressableDMem:
#   - __init__(base=0x00010000): self.base, self._b=dict()
#   - helper _in_range(addr): return addr >= base  (addresses below base are unmapped)
#   - load8(addr):   return 0 if <base else dict.get(addr, 0)
#   - load16(addr):  read two bytes (b0, b1) little-endian (addr, addr+1)
#   - load32(addr):  read four bytes (b0..b3) little-endian
#   - store8(addr,v): if <base: ignore; else set dict[addr]=v&0xFF
#   - store16(addr,v): write two bytes
#   - store32(addr,v): write four bytes
#
# MODIFY: In RV32ISim.__init__, replace "self.dmem = {}" with:
#         self.dmem = ByteAddressableDMem()
#
# REMOVE: Any old word-only dmem helpers (load_word_dmem/store_word_dmem) once new class is in.
#         Update all load/store call sites to use load8/16/32 or store8/16/32 accordingly.
#
# OPTIONAL (nice EC): Add an MMIO console at 0x00020000: when store8 hits that address,
#                     print(chr(value&0xFF), end="", flush=True) to simulate UART TX.

# --- D) ADD SLT/SLTU/SLTI/SLTIU ----------------------------------------------
# ADD: In OPC_OP (R-type) and OPC_OPIMM (I-type) handlers, implement set-less-than:
#
# R-type (OPC_OP):
#   - SLT:  funct3=010, funct7=0000000 → rd = 1 if (int32(rs1) < int32(rs2)) else 0
#   - SLTU: funct3=011, funct7=0000000 → rd = 1 if (uint32(rs1) < uint32(rs2)) else 0
#
# I-type (OPC_OPIMM):
#   - SLTI:  funct3=010 → rd = 1 if (int32(rs1) < int32(imm)) else 0
#   - SLTIU: funct3=011 → rd = 1 if (uint32(rs1) < uint32(imm & 0xFFFFFFFF)) else 0
#
# IMPLEMENTATION NOTES:
#   - For signed compare, cast to Python signed 32-bit:
#       def to_s32(x): return x if x < 0x80000000 else x - 0x100000000
#   - For unsigned, compare masked 32-bit values directly.

# --- E) FACTOR OUT ALIGNMENT CHECK -------------------------------------------
# ADD: Small helper to reuse:
#   def require_aligned(addr, bytes_required):
#       if addr % bytes_required != 0:
#           raise RuntimeError(f"Unaligned access: 0x{addr:08X} (need {bytes_required}-byte alignment)")
#
# USE in LW/SW (4 bytes) and LH/SH (2 bytes). LB/SB require no alignment.

# --- F) KEEP THE HALT CONVENTION ---------------------------------------------
# VERIFY: You already detect `jal x0, 0` and stop. Leave it as-is (document in README).
# This makes grading easier and prevents infinite loops during tests.

# --- G) TEST CASES YOU SHOULD ADD (TINY .hex PROGRAMS) -----------------------
# ADD: A minimal test that exercises each new feature (commit these to the repo):
#
# 1) slt/slti/sltu/sltiu:
#    - Case signed-negative vs positive; case unsigned wraparound.
# 2) lb/lbu on 0x7F and 0x80 test values:
#    - LBU(0x80)==0x80; LB(0x80)==0xFFFFFF80 (sign extension)
# 3) lh/lhu with alignment good/bad:
#    - Valid halfword at aligned addr; attempt unaligned to confirm exception.
# 4) sb/sh:
#    - Write patterns 0xAA/0x55 and read back via lb/lh/lbu/lhu to verify endianness.
# 5) MMIO console (if added):
#    - Write 'H','i','\n' via SB to 0x00020000 and ensure it prints.
#
# For each, capture console trace + final register/memory snapshot in your README.

# --- H) README & DESIGN DOC UPDATES ------------------------------------------
# ADD (README.md):
#   - Document new instructions: SLT/SLTU/SLTI/SLTIU
#   - Document new loads/stores and alignment rules
#   - Document MMIO console address (if implemented)
#   - Explain unaligned access behavior (raises RuntimeError)
#
# ADD (docs/design.md):
#   - Update datapath notes to mention byte-addressable memory
#   - Include a small table: mnemonic → funct3/funct7 → behavior → alignment
#
# NOTE: Paste a short AI usage log (prompts + key responses) to satisfy policy.

# --- I) HOUSEKEEPING (CODE CLEANUP) ------------------------------------------
# REMOVE: Any dead code paths that still reference old dict-based word DMEM.
# REMOVE/RENAME: Functions named load_word_dmem/store_word_dmem; use load*/store* from the new class.
# MODIFY: All call sites in OPC_LOAD/OPC_STORE to use the new byte-level API.
# VERIFY: All write-backs mask to 32-bit (val & 0xFFFFFFFF); x0 stays zero every step.

# --- J) OPTIONAL SMALL EXTRAS (EASY POINTS) ----------------------------------
# (Do these only if time allows; the above is the main target.)
# - Add BNE test (already supported) plus a quick BEQ-not-taken case.
# - Add an --stop-at-pc flag to end simulation when PC hits a specific address.
# - Add a tiny disassembler in trace (decode mnemonic for readability).

# --- K) FINAL QUICK SELF-CHECK BEFORE PR -------------------------------------
# - Run sample `test_base.hex` → expect x6=2 and DMEM[0x00010000]=15.
# - Run your new tests for SLT* and byte/half loads/stores.
# - Ensure exceptions on unaligned LH/SH/LHU/SH and LW/SW.
# - Make a short screen capture or copy logs into README as "Test Output".
# - Open PR: "feature/byte-dmem + slt* + byte/half loads/stores" with notes & results.

# =====================================================================
# End of partner TODO guide
# =====================================================================
# REMOVE ENTIRE BLOCK WHEN DONE
