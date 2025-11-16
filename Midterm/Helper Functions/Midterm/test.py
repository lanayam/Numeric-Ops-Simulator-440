from coreapi import core_alu, core_mdu, hex_to_bits, bits_to_hex
from fpu import FPU
from twos import encode_twos_complement, decode_twos_complement

# Simple check helper
def check(name, expected, got):
    if expected == got:
        print(f"[PASS] {name} -> {got}")
    else:
        print(f"[FAIL] {name}: expected {expected}, got {got}")

def test_twos_complement():
    print("\n=== Testing Two's Complement (WIDTH=32) ===")
    # encode -> hex checks (32-bit fixed width)
    check("encode_twos_complement(5).hex", "0x00000005", encode_twos_complement(5)["hex"])
    check("encode_twos_complement(-5).hex", "0xFFFFFFFB", encode_twos_complement(-5)["hex"])

    # round-trip via bits
    pos5_bits = hex_to_bits(encode_twos_complement(5)["hex"], 32)
    neg5_bits = hex_to_bits(encode_twos_complement(-5)["hex"], 32)
    check("decode_twos_complement(bits_of(+5))", 5, decode_twos_complement(pos5_bits)["value"])
    check("decode_twos_complement(bits_of(-5))", -5, decode_twos_complement(neg5_bits)["value"])

    # edge cases
    check("encode_twos_complement(-1).hex", "0xFFFFFFFF", encode_twos_complement(-1)["hex"])
    check("encode_twos_complement(0).hex", "0x00000000", encode_twos_complement(0)["hex"])

def test_m_extension():
    print("\n=== Testing RISC-V M Extension via core_mdu ===")
    # MUL
    check("MUL 3*7", "0x00000015", core_mdu("MUL", "0x00000003", "0x00000007")["hex"])
    # DIVU
    check("DIVU 15/3", "0x00000005", core_mdu("DIVU", "0x0000000F", "0x00000003")["hex"])
    # REM / REMU
    check("REM 10%3", "0x00000001", core_mdu("REM", "0x0000000A", "0x00000003")["hex"])
    check("REMU 10%3", "0x00000001", core_mdu("REMU", "0x0000000A", "0x00000003")["hex"])
    # Signed DIV negative case (implementation choice: two's-quotient in hex)
    check("DIV -10/3", "0xFFFFFFFD", core_mdu("DIV", "0xFFFFFFF6", "0x00000003")["hex"])


def test_float32():
    print("\n=== Testing Float32 via FPU (selected stable ops) ===")

    # 1.0 + 1.0 = 2.0
    bits, flags, trace = FPU().f32_add(hex_to_bits("0x3F800000", 32), hex_to_bits("0x3F800000", 32))
    check("FADD 1.0+1.0", "0x40000000", bits_to_hex(bits))

    # 3.0 * 2.0 = 6.0
    bits, flags, trace = FPU().f32_mul(hex_to_bits("0x40400000", 32), hex_to_bits("0x40000000", 32))
    check("FMUL 3.0*2.0", "0x40C00000", bits_to_hex(bits))


def main():
    print("\n==============================")
    print(" RUNNING FULL PROJECT TESTS ")
    print("==============================")
    test_twos_complement()
    test_m_extension()
    test_float32()
    print("\n=== ALL TESTS COMPLETE ===\n")

if __name__ == "__main__":
    main()
