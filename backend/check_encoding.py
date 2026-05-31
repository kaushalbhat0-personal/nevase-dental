"""Check UTF-8 encoding of document_service.py."""
with open(
    "D:/Kaushal/Python/Python Projects/medical_webapp/backend/app/services/document_service.py",
    "rb",
) as f:
    data = f.read()

# Proper UTF-8 validation
i = 0
while i < len(data):
    b = data[i]
    if b < 0x80:
        i += 1
    elif 0xC2 <= b <= 0xDF:
        if i + 1 >= len(data) or not (0x80 <= data[i + 1] <= 0xBF):
            print(f"Invalid 2-byte sequence at {i}: {hex(b)}")
            print(f"  Context: {data[max(0,i-5):i+10]}")
            break
        i += 2
    elif 0xE0 <= b <= 0xEF:
        if (
            i + 2 >= len(data)
            or not (0x80 <= data[i + 1] <= 0xBF)
            or not (0x80 <= data[i + 2] <= 0xBF)
        ):
            print(f"Invalid 3-byte sequence at {i}: {hex(b)}")
            print(f"  Context: {data[max(0,i-5):i+10]}")
            break
        i += 3
    elif 0xF0 <= b <= 0xF4:
        if i + 3 >= len(data) or not all(0x80 <= data[i + j] <= 0xBF for j in range(1, 4)):
            print(f"Invalid 4-byte sequence at {i}")
            break
        i += 4
    else:
        print(f"Invalid byte at {i}: {hex(b)}")
        print(f"  Context: {data[max(0,i-10):i+20]}")
        break
else:
    print("All bytes are valid UTF-8")
    print(f"Total size: {len(data)} bytes")

# Now try to compile
text = data.decode("utf-8")
try:
    compile(text, "document_service.py", "exec")
    print("Compilation OK")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    lines = text.split("\n")
    print(f"Line {e.lineno}: {repr(lines[e.lineno-1])}")
    print(f"Line {e.lineno-1}: {repr(lines[e.lineno-2])}")
    print(f"Line {e.lineno+1}: {repr(lines[e.lineno])}")
