"""Debug script to trace authorization for mark-completed."""
from __future__ import annotations

import sys
sys.path.insert(0, 'backend')

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

appt_id = '33c2710f-fe03-4325-9e9d-d750dd25073d'
doc_id = '2c9982da-0710-4589-9140-4d26fe221f8f'
user_id = '163bec58-8e99-42bb-867c-80e8931b8825'

# Appointment details
appt = db.execute(
    text('SELECT id, doctor_id, tenant_id, patient_id, status FROM appointments WHERE id = :aid'),
    {'aid': appt_id}
).fetchone()
if appt:
    print(f'Appointment: id={appt[0]}, doctor_id={appt[1]}, tenant_id={appt[2]}, patient_id={appt[3]}, status={appt[4]}')

# Doctor details
doc = db.execute(
    text('SELECT id, user_id, tenant_id FROM doctors WHERE id = :did'),
    {'did': doc_id}
).fetchone()
if doc:
    print(f'Doctor: id={doc[0]}, user_id={doc[1]}, tenant_id={doc[2]}')

# User details
user = db.execute(
    text('SELECT id, email, role, tenant_id, is_owner FROM users WHERE id = :uid'),
    {'uid': user_id}
).fetchone()
if user:
    print(f'User: id={user[0]}, email={user[1]}, role={user[2]}, tenant_id={user[3]}, is_owner={user[4]}')

# Check user_tenants table
try:
    ut_rows = db.execute(
        text("SELECT user_id, tenant_id, role FROM user_tenants WHERE user_id = :uid"),
        {'uid': user_id}
    ).fetchall()
    for ut in ut_rows:
        print(f'UserTenant: user_id={ut[0]}, tenant_id={ut[1]}, role={ut[2]}')
except Exception as e:
    print(f'user_tenants table error: {e}')

# Check if there are any other doctors linked to this user
other_doctors = db.execute(
    text("SELECT id, user_id, tenant_id FROM doctors WHERE user_id = :uid AND id != :did"),
    {'uid': user_id, 'did': doc_id}
).fetchall()
if other_doctors:
    print(f'WARNING: Multiple doctors for same user: {other_doctors}')
else:
    print('No duplicate doctors for this user')

# Check tenant IDs match
if appt and doc:
    print(f'\nTenant comparison:')
    print(f'  Appointment.tenant_id = {appt[2]}')
    print(f'  Doctor.tenant_id = {doc[2]}')
    print(f'  Match: {appt[2] == doc[2]}')

# Check doctor_id match
if appt and doc:
    print(f'\nDoctor ID comparison:')
    print(f'  Appointment.doctor_id = {appt[1]}')
    print(f'  Doctor.id = {doc[0]}')
    print(f'  Match: {appt[1] == doc[0]}')

db.close()
