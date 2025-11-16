from coreapi import core_alu, core_mdu, core_fpu

def main():
    print("Mini RISC-V Numeric Operations Simulator Tool")
    print("Type EXIT at any time to quit.")

    while True:
        op = input("Operation (ADD, SUB, MUL, DIV, AND, OR, XOR, SLL, SRL, SRA, SLT, SLTU, DIVU, REM, REMU, FADD, FSUB, FMUL, FDIV): ").strip()
        if op.upper() == "EXIT":
            break

        x = input("rs1 (hex like 0x1234ABCD): ").strip()
        if x.upper() == "EXIT":
            break
        y = input("rs2 (hex): ").strip()
        if y.upper() == "EXIT":
            break

        opu = op.upper()

        try:
            if opu in ["ADD","SUB","AND","OR","XOR","SLL","SRL","SRA","SLT","SLTU"]:
                out = core_alu(opu, x, y)
            elif opu in ["MUL","DIV","DIVU","REM","REMU"]:
                out = core_mdu(opu, x, y)
            elif opu in ["FADD","FSUB","FMUL","FDIV"]:
                # Map to core_fpu without the leading 'F'
                out = core_fpu(opu[1:], x, y)
            else:
                print("Invalid op")
                continue

            print("\nResult:")
            print("  Hex:   ", out.get("hex"))
            print("  Flags: ", out.get("flags"))
            print()
        except Exception as e:
            print(f"Error: {e}\n")
            continue

if __name__ == "__main__":
    main()