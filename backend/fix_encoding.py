"""Fix UTF-8 encoding issues in document_service.py."""
with open(
    "D:/Kaushal/Python/Python Projects/medical_webapp/backend/app/services/document_service.py",
    "rb",
) as f:
    data = f.read()

# Decode with utf-8, replacing errors
text = data.decode("utf-8", errors="replace")

# Write back as proper UTF-8
with open(
    "D:/Kaushal/Python/Python Projects/medical_webapp/backend/app/services/document_service.py",
    "w",
    encoding="utf-8",
) as f:
    f.write(text)

print("File re-encoded successfully")
print(f"Original size: {len(data)} bytes")
print(f"New size: {len(text.encode('utf-8'))} bytes")
