"""Debug script to check doctor profile completeness - v2."""
from __future__ import annotations

import sys
sys.path.insert(0, 'backend')

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

doc_id = '2c9982da-0710-4589-9140-4d26fe221f8f'

# Find all tables with 'profile' in name
tables = db.execute(
    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%profile%'")
).fetchall()
print(f'Tables with profile: {[t[0] for t in tables]}')

# Find all tables with 'doctor' in name
tables2 = db.execute(
    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%doctor%'")
).fetchall()
print(f'Tables with doctor: {[t[0] for t in tables2]}')

# Check doctor_structured_profile (singular)
try:
    profiles = db.execute(
        text("SELECT id, doctor_id, is_profile_complete, verification_status FROM doctor_structured_profile WHERE doctor_id = :did"),
        {'did': doc_id}
    ).fetchall()
    for p in profiles:
        print(f'Profile: id={p[0]}, doctor_id={p[1]}, is_profile_complete={p[2]}, verification_status={p[3]}')
    if not profiles:
        print('No structured profile found for this doctor')
except Exception as e:
    print(f'doctor_structured_profile error: {e}')

# Check doctor_profiles
try:
    profiles2 = db.execute(
        text("SELECT * FROM doctor_profiles WHERE doctor_id = :did"),
        {'did': doc_id}
    ).fetchall()
    for p in profiles2:
        print(f'DoctorProfile: {p}')
    if not profiles2:
        print('No doctor_profiles found')
except Exception as e:
    print(f'doctor_profiles error: {e}')

# Check doctor table columns
cols = db.execute(
    text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'doctors' ORDER BY ordinal_position")
).fetchall()
print(f'\nDoctor columns:')
for c in cols:
    print(f'  {c[0]}: {c[1]}')

# Check doctor with tenant
doc = db.execute(
    text("SELECT d.id, d.user_id, d.tenant_id, t.name as tenant_name FROM doctors d LEFT JOIN tenants t ON d.tenant_id = t.id WHERE d.id = :did"),
    {'did': doc_id}
).fetchone()
if doc:
    print(f'\nDoctor with tenant: id={doc[0]}, user_id={doc[1]}, tenant_id={doc[2]}, tenant_name={doc[3]}')

db.close()
