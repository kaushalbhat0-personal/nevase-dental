"""Trace prescription data flow in mark_appointment_completed"""
import re

with open('backend/app/services/appointment_service.py', 'r', encoding='utf-8') as f:
    c = f.read()

idx = c.find('def mark_appointment_completed')
rest = c[idx:]
m = re.search(r'def mark_appointment_completed.*?(?=\ndef |\Z)', rest, re.DOTALL)
if m:
    text = m.group()
    # Find the prescriptions block
    for kw in ['data.prescriptions', '_create_appointment_prescriptions', 'prescription']:
        pidx = text.find(kw)
        if pidx >= 0:
            print(f'Found "{kw}" at offset {pidx}:')
            print(text[max(0,pidx-200):pidx+500])
            print('---')
    
    # Print lines 80-200 of the function
    print('=== LINES 80-200 ===')
    lines = text.split('\n')
    for i, line in enumerate(lines[80:200]):
        print(f'{i+80}: {line}')
