"""Debug script to check doctor profile completeness."""
from __future__ import annotations

import sys
sys.path.insert(0, 'backend')

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

user_id = '163bec58-8e99-42bb-867c-80e8931b8825'
doc_id = '2c9982da-0710-4589-9140-4d26fe221f8f'

# Check doctor_structured_profiles table
try:
    profiles = db.execute(
        text("SELECT id, doctor_id, is_profile_complete, verification_status FROM doctor_structured_profiles WHERE doctor_id = :did"),
        {'did': doc_id}
    ).fetchall()
    for p in profiles:
        print(f'Profile: id={p[0]}, doctor_id={p[1]}, is_profile_complete={p[2]}, verification_status={p[3]}')
    if not profiles:
        print('No structured profile found for this doctor')
except Exception as e:
    print(f'doctor_structured_profiles error: {e}')

# Check doctor table columns
try:
    cols = db.execute(
        text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'doctors' ORDER BY ordinal_position")
    ).fetchall()
    print(f'\nDoctor columns:')
    for c in cols:
        print(f'  {c[0]}: {c[1]}')
except Exception as e:
    print(f'columns error: {e}')

# Check if doctor has tenant loaded
doc = db.execute(
    text("SELECT d.id, d.user_id, d.tenant_id, t.name as tenant_name FROM doctors d LEFT JOIN tenants t ON d.tenant_id = t.id WHERE d.id = :did"),
    {'did': doc_id}
).fetchone()
if doc:
    print(f'\nDoctor with tenant: id={doc[0]}, user_id={doc[1]}, tenant_id={doc[2]}, tenant_name={doc[3]}')

db.close()
