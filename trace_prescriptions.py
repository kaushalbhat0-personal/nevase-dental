#!/usr/bin/env python3
"""
Script to trace prescription flow and verify database state after encounter completion.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base
from app.models.appointment import Appointment, Prescription, PrescriptionItem
from app.models.patient_medication_schedule import PatientMedicationSchedule
from app.models.user import User
from app.models.patient import Patient
from app.models.tenant import Tenant
from app.models.doctor import Doctor
import uuid
from datetime import datetime, timezone

def get_db_session():
    """Create a database session."""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def trace_prescription_flow():
    """Trace the prescription flow and verify database state."""
    db = get_db_session()
    
    try:
        print("=== TRACING PRESCRIPTION FLOW ===")
        
        # Find the most recent completed appointment
        recent_appointment = db.query(Appointment).filter(
            Appointment.status == "completed"
        ).order_by(Appointment.encounter_completed_at.desc()).first()
        
        if not recent_appointment:
            print("No completed appointments found!")
            return
            
        print(f"Found completed appointment: {recent_appointment.id}")
        print(f"Patient ID: {recent_appointment.patient_id}")
        print(f"Doctor ID: {recent_appointment.doctor_id}")
        print(f"Tenant ID: {recent_appointment.tenant_id}")
        print(f"Encounter completed at: {recent_appointment.encounter_completed_at}")
        
        # Get prescriptions for this appointment
        prescriptions = db.query(Prescription).filter(
            Prescription.appointment_id == recent_appointment.id
        ).all()
        
        print(f"\nFound {len(prescriptions)} prescription(s):")
        
        total_schedules = 0
        for i, prescription in enumerate(prescriptions):
            print(f"\n  Prescription {i+1}:")
            print(f"    ID: {prescription.id}")
            print(f"    Notes: {prescription.notes}")
            print(f"    Created at: {prescription.created_at}")
            
            # Get prescription items
            items = db.query(PrescriptionItem).filter(
                PrescriptionItem.prescription_id == prescription.id
            ).all()
            
            print(f"    Items: {len(items)}")
            
            for j, item in enumerate(items):
                print(f"      Item {j+1}:")
                print(f"        ID: {item.id}")
                print(f"        Medicine: {item.medicine_name}")
                print(f"        Dosage: {item.dosage}")
                print(f"        Frequency: {item.frequency}")
                print(f"        Duration: {item.duration}")
                print(f"        Instructions: {item.instructions}")
            
            # Get medication schedules for this prescription
            schedules = db.query(PatientMedicationSchedule).filter(
                PatientMedicationSchedule.prescription_id == prescription.id
            ).all()
            
            print(f"    Medication Schedules: {len(schedules)}")
            total_schedules += len(schedules)
            
            for k, schedule in enumerate(schedules):
                print(f"      Schedule {k+1}:")
                print(f"        ID: {schedule.id}")
                print(f"        Patient ID: {schedule.patient_id}")
                print(f"        Medicine Name: {schedule.medicine_name}")
                print(f"        Dosage: {schedule.dosage}")
                print(f"        Frequency: {schedule.frequency}")
                print(f"        Start Date: {schedule.start_date}")
                print(f"        End Date: {schedule.end_date}")
                print(f"        Is Active: {schedule.is_active}")
                print(f"        Status: {schedule.status}")
                print(f"        Taken Count: {schedule.taken_count}")
                print(f"        Skipped Count: {schedule.skipped_count}")
                print(f"        Total Doses: {schedule.total_doses}")
        
        print(f"\n=== SUMMARY ===")
        print(f"Appointment ID: {recent_appointment.id}")
        print(f"Prescription Count: {len(prescriptions)}")
        print(f"Medication Schedule Count: {total_schedules}")
        
        # Check if schedules were created
        if len(prescriptions) > 0 and total_schedules == 0:
            print("ISSUE FOUND: Prescriptions exist but no medication schedules were created!")
            return False
        elif len(prescriptions) > 0 and total_schedules > 0:
            print("OK: Prescriptions have corresponding medication schedules")
            return True
        else:
            print("No prescriptions found for this appointment")
            return False
            
    except Exception as e:
        print(f"Error during tracing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = trace_prescription_flow()
    sys.exit(0 if success else 1)