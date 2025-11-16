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

