"""Derived organization labels (not stored; based on active doctor count per tenant)."""


def organization_label_from_active_doctor_count(active_doctor_count: int) -> str:
    """
    >1 active doctors: multi-organization. Exactly one: solo practice.
    Complements raw ``tenants.type`` (``individual`` vs ``organization``).
    """
    if active_doctor_count > 1:
        return "Clinic/Hospital"
    return "Individual Doctor"
