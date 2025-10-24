def shiftleftl (bits, shamt):
b = bits[:]
for _ in range (shamt):
  b = b [1:] + [0]
  return b
def shiftrightl (bits, shamt):
  b = bits[:]
  for _ in range (shamt):
    b = [0] + b[:-1]
    return b
def shiftrighta (bits, shamt):
  b = bits[:]
  sign = b[0]
  for _ in range (shamt)
  b = [sign] + b[:-1]
  return b
