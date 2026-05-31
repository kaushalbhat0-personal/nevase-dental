"""Debug script to check doctor profile completeness - v3."""
from __future__ import annotations

import sys
sys.path.insert(0, 'backend')

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

doc_id = '2c9982da-0710-4589-9140-4d26fe221f8f'

# Check doctor_profiles columns
cols = db.execute(
    text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'doctor_profiles' ORDER BY ordinal_position")
).fetchall()
print(f'doctor_profiles columns:')
for c in cols:
    print(f'  {c[0]}: {c[1]}')

# Check doctor_profiles for this doctor
profiles = db.execute(
    text("SELECT * FROM doctor_profiles WHERE doctor_id = :did"),
    {'did': doc_id}
).fetchall()
print(f'\ndoctor_profiles for doc {doc_id}:')
for p in profiles:
    print(f'  {p}')

# Check doctor table columns
cols2 = db.execute(
    text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'doctors' ORDER BY ordinal_position")
).fetchall()
print(f'\ndoctor columns:')
for c in cols2:
    print(f'  {c[0]}: {c[1]}')

# Check doctor with tenant
doc = db.execute(
    text("SELECT d.id, d.user_id, d.tenant_id, t.name as tenant_name FROM doctors d LEFT JOIN tenants t ON d.tenant_id = t.id WHERE d.id = :did"),
    {'did': doc_id}
).fetchone()
if doc:
    print(f'\nDoctor with tenant: id={doc[0]}, user_id={doc[1]}, tenant_id={doc[2]}, tenant_name={doc[3]}')

# Check user
user_id = '163bec58-8e99-42bb-867c-80e8931b8825'
user = db.execute(
    text("SELECT id, email, role, is_owner FROM users WHERE id = :uid"),
    {'uid': user_id}
).fetchone()
if user:
    print(f'\nUser: id={user[0]}, email={user[1]}, role={user[2]}, is_owner={user[3]}')

# Check appointment
appt_id = '33c2710f-fe03-4325-9e9d-d750dd25073d'
appt = db.execute(
    text("SELECT id, doctor_id, patient_id, tenant_id, status FROM appointments WHERE id = :aid"),
    {'aid': appt_id}
).fetchone()
if appt:
    print(f'\nAppointment: id={appt[0]}, doctor_id={appt[1]}, patient_id={appt[2]}, tenant_id={appt[3]}, status={appt[4]}')

db.close()
