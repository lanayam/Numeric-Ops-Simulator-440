from init import *
from mdu import *
from float32 import *

#this is the function for what we expect
def check(name, expected, got):
    if expected == got:
        print(f"[PASS] {name} -> {got}")
    else:
        print(f"[FAIL] {name}: expected {expected}, got {got}")

#Now we are going to check twos compliment
def test_twos_complement():
    print("\n=== Testing Two's Complement Functions ===")

    check("to_twos(5, 8)", "00000101", to_twos(5, 8))
    check("to_twos(-5, 8)", "11111011", to_twos(-5, 8))

    check("from_twos('00000101')", 5, from_twos("00000101"))
    check("from_twos('11111011')", -5, from_twos("11111011"))

    check("to_twos(-1, 4)", "1111", to_twos(-1, 4))
    check("from_twos('1111')", -1, from_twos("1111"))

def test_m_extension():
    print("\n=== Testing RISC-V M Extension ===")

    #this is mul
    check("mul(7, 3)", 21, mul(7, 3))
    check("mul(-7, 3)", -21, mul(-7, 3))

    # mulh (signed × signed high 32 bits)
    check("mulh(0x7FFFFFFF, 0x7FFFFFFF)",
          mulh(0x7FFFFFFF, 0x7FFFFFFF),
          mulh(0x7FFFFFFF, 0x7FFFFFFF))

    # mulhsu (signed × unsigned)
    check("mulhsu(-5, 10)", mulhsu(-5, 10), mulhsu(-5, 10))

    # mulhu (unsigned × unsigned)
    check("mulhu(0xFFFFFFFF, 0xFFFFFFFF)",
          mulhu(0xFFFFFFFF, 0xFFFFFFFF),
          mulhu(0xFFFFFFFF, 0xFFFFFFFF))

    #this is division
    check("div(10, 3)", 3, div(10, 3))
    check("div(-10, 3)", -3, div(-10, 3))
    check("div(7, -2)", -3, div(7, -2))

    #this should be division by zero
    check("div(5, 0)", -1, div(5, 0))
    check("divu(5, 0)", 0xFFFFFFFF, divu(5, 0))

    #this is the unsigned division
    check("divu(10, 3)", 3, divu(10, 3))

    #this will be the remainder
    check("rem(10, 3)", 1, rem(10, 3))
    check("rem(-10, 3)", -1, rem(-10, 3))
    check("remu(10, 3)", 1, remu(10, 3))


def test_float32():
    print("\n=== Testing Float32 Operations ===")

    #this should be for encoding and decoding
    check("float_to_bits(1.0)", float_to_bits(1.0), float_to_bits(1.0))
    check("bits_to_float(float_to_bits(3.5))",
          3.5,
          bits_to_float(float_to_bits(3.5)))

    #this should check for addition
    check("fadd(1.5, 2.5)", 4.0, fadd(1.5, 2.5))
    check("fadd(-2.0, 5.0)", 3.0, fadd(-2.0, 5.0))

    #this should check for subtraction
    check("fsub(5.0, 2.0)", 3.0, fsub(5.0, 2.0))
    check("fsub(2.0, 5.0)", -3.0, fsub(2.0, 5.0))

    #this should check for multiplication
    check("fmul(3.0, 2.0)", 6.0, fmul(3.0, 2.0))
    check("fmul(-1.5, 4.0)", -6.0, fmul(-1.5, 4.0))

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
