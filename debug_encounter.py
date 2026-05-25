#!/usr/bin/env python3
"""
Debug script to trace what happens during encounter completion.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set up environment
os.environ['DATABASE_URL'] = "postgresql://postgres.cweypvkblipnrtpcogmm:49y2KDIe6MrrthrM@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

from app.core.database import SessionLocal
from app.models.appointment import Appointment, Prescription
from app.models.patient_medication_schedule import PatientMedicationSchedule
from app.services import appointment_service
import logging

# Set up logging to see our debug messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_encounter_completion_debug():
    """Test encounter completion with debug output."""
    db = SessionLocal()
    
    try:
        # Find a completed appointment to examine
        appointment = db.query(Appointment).filter(
            Appointment.encounter_completed_at.isnot(None)
        ).order_by(Appointment.encounter_completed_at.desc()).first()
        
        if not appointment:
            print("No completed appointments found!")
            return False
            
        print(f"Found appointment: {appointment.id}")
        print(f"Status: {appointment.status}")
        print(f"Encounter completed at: {appointment.encounter_completed_at}")
        
        # Count prescriptions and schedules before
        rx_before = db.query(Prescription).filter(
            Prescription.appointment_id == appointment.id
        ).count()
        
        sched_before = db.query(PatientMedicationSchedule).join(Prescription).filter(
            Prescription.appointment_id == appointment.id
        ).count()
        
        print(f"BEFORE - Prescriptions: {rx_before}, Schedules: {sched_before}")
        
        # Now let's manually test the derivation function to see if it works
        prescriptions = db.query(Prescription).filter(
            Prescription.appointment_id == appointment.id
        ).all()
        
        print(f"Found {len(prescriptions)} prescriptions")
        
        for i, rx in enumerate(prescriptions):
            print(f"  Prescription {i+1}: {rx.id}")
            print(f"    Notes: {rx.notes}")
            print(f"    Items: {len(rx.items)}")
            
            # Check if schedules already exist for this prescription
            existing_schedules = db.query(PatientMedicationSchedule).filter(
                PatientMedicationSchedule.prescription_id == rx.id
            ).count()
            print(f"    Existing schedules: {existing_schedules}")
            
            if existing_schedules == 0 and len(rx.items) > 0:
                print(f"    Attempting to derive schedules...")
                try:
                    # This should create schedules
                    appointment_service._derive_medication_schedules_from_prescription(
                        db, rx, appointment
                    )
                    db.commit()
                    print(f"    Derivation completed")
                    
                    # Check again
                    new_schedules = db.query(PatientMedicationSchedule).filter(
                        PatientMedicationSchedule.prescription_id == rx.id
                    ).count()
                    print(f"    Schedules after derivation: {new_schedules}")
                except Exception as e:
                    print(f"    Error during derivation: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Final count
        rx_after = db.query(Prescription).filter(
            Prescription.appointment_id == appointment.id
        ).count()
        
        sched_after = db.query(PatientMedicationSchedule).join(Prescription).filter(
            Prescription.appointment_id == appointment.id
        ).count()
        
        print(f"AFTER - Prescriptions: {rx_after}, Schedules: {sched_after}")
        
        if rx_after > 0 and sched_after == 0:
            print("ISSUE: Prescriptions exist but no medication schedules!")
            return False
        elif rx_after > 0 and sched_after > 0:
            print("OK: Prescriptions have medication schedules")
            return True
        else:
            print("No prescriptions found")
            return False
            
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_encounter_completion_debug()
    sys.exit(0 if success else 1)