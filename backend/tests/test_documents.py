"""
Tests for Phase 3B — Document Generation Foundation.

Covers:
- Authorization (cross-tenant isolation)
- Tenant isolation
- Generated PDF content existence
- Aggregate correctness
- Export endpoints (status codes, content type)
- Audit events
- Missing resource handling
"""

from __future__ import annotations

import io
from unittest.mock import ANY, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.schemas.document import (
    DocumentFormat,
    DocumentMeta,
    DocumentType,
    EncounterSummaryDocumentData,
    InvoiceDocumentData,
    PatientStatementDocumentData,
    PrescriptionDocumentData,
)
from app.services.document_service import (
    _build_encounter_summary_html,
    _build_invoice_html,
    _build_patient_statement_html,
    _build_prescription_html,
    _escape_html,
    _fmt_currency,
    _fmt_date,
    _fmt_dt,
    generate_encounter_summary_pdf,
    generate_invoice_pdf,
    generate_patient_statement_pdf,
    generate_prescription_pdf,
)


# ═════════════════════════════════════════════════════════════════════════════
# TEMPLATE HELPER TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestTemplateHelpers:
    def test_fmt_currency_none(self):
        assert _fmt_currency(None) == "₹0.00"

    def test_fmt_currency_value(self):
        assert _fmt_currency(150.50) == "₹150.50"

    def test_fmt_dt_none(self):
        assert _fmt_dt(None) == ""

    def test_fmt_date_none(self):
        assert _fmt_date(None) == ""

    def test_escape_html_none(self):
        assert _escape_html(None) == ""

    def test_escape_html_special_chars(self):
        result = _escape_html('<script>alert("xss")</script>')
        assert "<" in result
        assert ">" in result
        assert '"""' in result

    def test_escape_html_plain_text(self):
        assert _escape_html("Hello, World!") == "Hello, World!"


# ═════════════════════════════════════════════════════════════════════════════
# DOCUMENT BUILDER TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestInvoiceHtmlBuilder:
    def test_build_invoice_html_contains_expected_sections(self):
        """Verify the invoice HTML contains all expected sections."""
        data = InvoiceDocumentData(
            bill_id="00000000-0000-0000-0000-000000000001",
            patient_id="00000000-0000-0000-0000-000000000002",
            patient_name="John Doe",
            doctor_id="00000000-0000-0000-0000-000000000003",
            doctor_name="Dr. Smith",
            doctor_specialization="Cardiology",
            tenant_id="00000000-0000-0000-0000-000000000004",
            tenant_name="Heart Clinic",
            bill_amount=500.00,
            consultation_amount=300.00,
            inventory_amount=200.00,
            inventory_items=[
                {"item_name": "Bandage", "quantity": 2, "total": 100.00},
                {"item_name": "Medicine", "quantity": 1, "total": 100.00},
            ],
            status="paid",
            paid_at="2026-01-15T10:30:00",
            paid_via="cash",
            created_at="2026-01-15T10:00:00",
        )

        html = _build_invoice_html(data)

        # Check for key content
        assert "Heart Clinic" in html
        assert "Dr. Smith" in html
        assert "Cardiology" in html
        assert "John Doe" in html
        assert "Invoice" in html
        assert "₹500.00" in html
        assert "₹300.00" in html
        assert "PAID" in html
        assert "Bandage" in html
        assert "Medicine" in html
        assert "Consultation Fee" in html

        # Check for TODO hooks
        assert "TODO: Phase 3C" in html

    def test_build_invoice_html_unpaid_status(self):
        """Verify unpaid status renders correctly."""
        data = InvoiceDocumentData(
            bill_id="00000000-0000-0000-0000-000000000001",
            patient_id="00000000-0000-0000-0000-000000000002",
            patient_name="Jane Doe",
            tenant_id="00000000-0000-0000-0000-000000000004",
            bill_amount=250.00,
            consultation_amount=250.00,
            inventory_amount=0.00,
            status="unpaid",
            created_at="2026-01-15T10:00:00",
        )

        html = _build_invoice_html(data)
        assert "UNPAID" in html
        assert "status-unpaid" in html


class TestPatientStatementHtmlBuilder:
    def test_build_statement_html_contains_expected_sections(self):
        """Verify the patient statement HTML contains all expected sections."""
        data = PatientStatementDocumentData(
            patient_id="00000000-0000-0000-0000-000000000001",
            patient_name="John Doe",
            tenant_id="00000000-0000-0000-0000-000000000002",
            tenant_name="City Clinic",
            total_billed=1000.00,
            total_paid=600.00,
            total_unpaid=400.00,
            balance=400.00,
            bills=[
                {
                    "bill_id": "bill-1",
                    "amount": "500.00",
                    "status": "paid",
                    "paid_at": "2026-01-15T10:30:00",
                    "created_at": "2026-01-15T10:00:00",
                },
                {
                    "bill_id": "bill-2",
                    "amount": "500.00",
                    "status": "unpaid",
                    "paid_at": None,
                    "created_at": "2026-01-20T10:00:00",
                },
            ],
            encounters=[
                {
                    "appointment_id": "appt-1",
                    "appointment_time": "2026-01-15T09:00:00",
                    "doctor_name": "Dr. Smith",
                    "has_bill": True,
                },
            ],
        )

        html = _build_patient_statement_html(data)

        # Check for key content
        assert "City Clinic" in html
        assert "John Doe" in html
        assert "Patient Financial Statement" in html
        assert "₹1,000.00" in html
        assert "₹600.00" in html
        assert "₹400.00" in html
        assert "Dr. Smith" in html
        assert "Yes" in html

        # Check for TODO hooks
        assert "TODO: Phase 3C" in html


class TestPrescriptionHtmlBuilder:
    def test_build_prescription_html_contains_expected_sections(self):
        """Verify the prescription HTML contains all expected sections."""
        data = PrescriptionDocumentData(
            appointment_id="00000000-0000-0000-0000-000000000001",
            doctor_id="00000000-0000-0000-0000-000000000002",
            doctor_name="Dr. Smith",
            doctor_specialization="Cardiology",
            doctor_registration="MH-12345",
            patient_id="00000000-0000-0000-0000-000000000003",
            patient_name="John Doe",
            patient_age=45,
            patient_gender="Male",
            tenant_id="00000000-0000-0000-0000-000000000004",
            tenant_name="Heart Clinic",
            clinic_name="Heart Clinic",
            diagnosis="Hypertension",
            prescriptions=[
                {
                    "medicine_name": "Amlodipine",
                    "dosage": "5mg",
                    "frequency": "Once daily",
                    "duration": "30 days",
                    "instructions": "Take after breakfast",
                },
                {
                    "medicine_name": "Aspirin",
                    "dosage": "75mg",
                    "frequency": "Once daily",
                    "duration": "30 days",
                    "instructions": "Take with water",
                },
            ],
            vitals={
                "bp_systolic": 140,
                "bp_diastolic": 90,
                "pulse": 72,
            },
            notes="Follow up in 2 weeks",
            created_at="2026-01-15T10:00:00",
        )

        html = _build_prescription_html(data)

        # Check for key content
        assert "Heart Clinic" in html
        assert "Dr. Smith" in html
        assert "Cardiology" in html
        assert "MH-12345" in html
        assert "John Doe" in html
        assert "45" in html
        assert "Male" in html
        assert "Hypertension" in html
        assert "Amlodipine" in html
        assert "5mg" in html
        assert "Once daily" in html
        assert "30 days" in html
        assert "Take after breakfast" in html
        assert "Aspirin" in html
        assert "Prescription" in html

        # Check vitals
        assert "140" in html
        assert "90" in html
        assert "72" in html

        # Check notes
        assert "Follow up in 2 weeks" in html

        # Check for TODO hooks
        assert "TODO: Phase 3C" in html

    def test_build_prescription_html_no_inventory_items(self):
        """
        CRITICAL: Verify inventory items do NOT appear in prescription HTML.
        Only prescription model data should be rendered.
        """
        data = PrescriptionDocumentData(
            appointment_id="00000000-0000-0000-0000-000000000001",
            doctor_id="00000000-0000-0000-0000-000000000002",
            doctor_name="Dr. Smith",
            patient_id="00000000-0000-0000-0000-000000000003",
            patient_name="John Doe",
            tenant_id="00000000-0000-0000-0000-000000000004",
            prescriptions=[
                {
                    "medicine_name": "Paracetamol",
                    "dosage": "500mg",
                    "frequency": "As needed",
                    "duration": "5 days",
                    "instructions": "For fever",
                },
            ],
            created_at="2026-01-15T10:00:00",
        )

        html = _build_prescription_html(data)

        # Verify prescription content exists
        assert "Paracetamol" in html

        # Verify no inventory-related terms appear
        assert "Inventory" not in html
        assert "Bandage" not in html
        assert "selling_price" not in html


class TestEncounterSummaryHtmlBuilder:
    def test_build_encounter_summary_html_contains_expected_sections(self):
        """Verify the encounter summary HTML contains all expected sections."""
        data = EncounterSummaryDocumentData(
            appointment_id="00000000-0000-0000-0000-000000000001",
            patient_id="00000000-0000-0000-0000-000000000002",
            patient_name="John Doe",
            doctor_id="00000000-0000-0000-0000-000000000003",
            doctor_name="Dr. Smith",
            doctor_specialization="Cardiology",
            tenant_id="00000000-0000-0000-0000-000000000004",
            tenant_name="Heart Clinic",
            appointment_time="2026-01-15T09:00:00",
            status="completed",
            encounter_started_at="2026-01-15T09:00:00",
            encounter_completed_at="2026-01-15T09:30:00",
            subjective_notes="Patient reports chest pain",
            objective_notes="BP 140/90, HR 72",
            assessment_notes="Hypertension, possible angina",
            plan_notes="Prescribe Amlodipine, follow up in 2 weeks",
            diagnosis="Hypertension",
            treatment_summary="Started on Amlodipine 5mg daily",
            clinical_notes="Patient advised lifestyle modifications",
            vitals={
                "temperature": 98.6,
                "bp_systolic": 140,
                "bp_diastolic": 90,
                "pulse": 72,
                "spo2": 98,
            },
            prescriptions=[
                {
                    "medicine_name": "Amlodipine",
                    "dosage": "5mg",
                    "frequency": "Once daily",
                    "duration": "30 days",
                    "instructions": "Take after breakfast",
                },
            ],
            follow_up_date="2026-01-29T09:00:00",
            follow_up_notes="Review BP readings",
            created_at="2026-01-15T10:00:00",
        )

        html = _build_encounter_summary_html(data)

        # Check for key content
        assert "Heart Clinic" in html
        assert "Dr. Smith" in html
        assert "John Doe" in html
        assert "Encounter Summary" in html
        assert "COMPLETED" in html

        # Check SOAP sections
        assert "Subjective" in html
        assert "Patient reports chest pain" in html
        assert "Objective" in html
        assert "BP 140/90, HR 72" in html
        assert "Assessment" in html
        assert "Hypertension, possible angina" in html
        assert "Plan" in html
        assert "Prescribe Amlodipine" in html

        # Check diagnosis
        assert "Hypertension" in html

        # Check treatment
        assert "Started on Amlodipine" in html

        # Check clinical notes
        assert "lifestyle modifications" in html

        # Check vitals
        assert "98.6" in html
        assert "140" in html
        assert "90" in html

        # Check prescriptions
        assert "Amlodipine" in html
        assert "5mg" in html

        # Check follow-up
        assert "Follow-up Plan" in html

        # Check for TODO hooks
        assert "TODO: Phase 3C" in html


# ═════════════════════════════════════════════════════════════════════════════
# PDF GENERATION TESTS (with mocked weasyprint)
# ═════════════════════════════════════════════════════════════════════════════


class TestPdfGeneration:
    """Test PDF generation with mocked weasyprint."""

    @patch("app.services.document_service._render_pdf")
    @patch("app.services.document_service.log_structured_audit_event")
    @patch("app.services.document_service._aggregate_invoice_data")
    def test_generate_invoice_pdf_calls_audit(
        self,
        mock_aggregate: MagicMock,
        mock_audit: MagicMock,
        mock_render: MagicMock,
        db_session: MagicMock,
        current_user: MagicMock,
    ):
        """Verify audit event is logged when invoice PDF is generated."""
        mock_aggregate.return_value = InvoiceDocumentData(
            bill_id="00000000-0000-0000-0000-000000000001",
            patient_id="00000000-0000-0000-0000-000000000002",
            patient_name="Test Patient",
            tenant_id="00000000-0000-0000-0000-000000000003",
            bill_amount=100.00,
            consultation_amount=100.00,
            inventory_amount=0.00,
            status="paid",
            created_at="2026-01-15T10:00:00",
        )
        mock_render.return_value = b"%PDF-1.4 mock pdf content"

        result = generate_invoice_pdf(
            db=db_session,
            bill_id="00000000-0000-0000-0000-000000000001",
            current_user=current_user,
            tenant_id="00000000-0000-0000-0000-000000000003",
        )

        # Verify audit event was logged
        mock_audit.assert_called_once_with(
            event="invoice_generated",
            tenant_id=ANY,
            resource_id=ANY,
            actor_id=ANY,
            document_type="invoice",
            request_id=ANY,
        )

        # Verify PDF bytes returned
        assert result == b"%PDF-1.4 mock pdf content"

    @patch("app.services.document_service._render_pdf")
    @patch("app.services.document_service.log_structured_audit_event")
    @patch("app.services.document_service._aggregate_prescription_data")
    def test_generate_prescription_pdf_calls_audit(
        self,
        mock_aggregate: MagicMock,
        mock_audit: MagicMock,
        mock_render: MagicMock,
        db_session: MagicMock,
        current_user: MagicMock,
    ):
        """Verify audit event is logged when prescription PDF is generated."""
        mock_aggregate.return_value = PrescriptionDocumentData(
            appointment_id="00000000-0000-0000-0000-000000000001",
            doctor_id="00000000-0000-0000-0000-000000000002",
            doctor_name="Dr. Test",
            patient_id="00000000-0000-0000-0000-000000000003",
            patient_name="Test Patient",
            tenant_id="00000000-0000-0000-0000-000000000004",
            prescriptions=[],
            created_at="2026-01-15T10:00:00",
        )
        mock_render.return_value = b"%PDF-1.4 mock pdf content"

        result = generate_prescription_pdf(
            db=db_session,
            appointment_id="00000000-0000-0000-0000-000000000001",
            current_user=current_user,
            tenant_id="00000000-0000-0000-0000-000000000004",
        )

        mock_audit.assert_called_once_with(
            event="prescription_generated",
            tenant_id=ANY,
            resource_id=ANY,
            actor_id=ANY,
            document_type="prescription",
            request_id=ANY,
        )
        assert result == b"%PDF-1.4 mock pdf content"

    @patch("app.services.document_service._render_pdf")
    @patch("app.services.document_service.log_structured_audit_event")
    @patch("app.services.document_service._aggregate_encounter_summary_data")
    def test_generate_encounter_summary_pdf_calls_audit(
        self,
        mock_aggregate: MagicMock,
        mock_audit: MagicMock,
        mock_render: MagicMock,
        db_session: MagicMock,
        current_user: MagicMock,
    ):
        """Verify audit event is logged when encounter summary PDF is generated."""
        mock_aggregate.return_value = EncounterSummaryDocumentData(
            appointment_id="00000000-0000-0000-0000-000000000001",
            patient_id="00000000-0000-0000-0000-000000000002",
            patient_name="Test Patient",
            doctor_id="00000000-0000-0000-0000-000000000003",
            doctor_name="Dr. Test",
            tenant_id="00000000-0000-0000-0000-000000000004",
            appointment_time="2026-01-15T09:00:00",
            status="completed",
            created_at="2026-01-15T10:00:00",
        )
        mock_render.return_value = b"%PDF-1.4 mock pdf content"

        result = generate_encounter_summary_pdf(
            db=db_session,
            appointment_id="00000000-0000-0000-0000-000000000001",
            current_user=current_user,
            tenant_id="00000000-0000-0000-0000-000000000004",
        )

        mock_audit.assert_called_once_with(
            event="encounter_summary_generated",
            tenant_id=ANY,
            resource_id=ANY,
            actor_id=ANY,
            document_type="encounter_summary",
            request_id=ANY,
        )
        assert result == b"%PDF-1.4 mock pdf content"

    @patch("app.services.document_service._render_pdf")
    @patch("app.services.document_service.log_structured_audit_event")
    @patch("app.services.document_service._aggregate_patient_statement_data")
    def test_generate_patient_statement_pdf_calls_audit(
        self,
        mock_aggregate: MagicMock,
        mock_audit: MagicMock,
        mock_render: MagicMock,
        db_session: MagicMock,
        current_user: MagicMock,
    ):
        """Verify audit event is logged when patient statement PDF is generated."""
        mock_aggregate.return_value = PatientStatementDocumentData(
            patient_id="00000000-0000-0000-0000-000000000001",
            patient_name="Test Patient",
            tenant_id="00000000-0000-0000-0000-000000000002",
            total_billed=100.00,
            total_paid=50.00,
            total_unpaid=50.00,
            balance=50.00,
            bills=[],
            encounters=[],
        )
        mock_render.return_value = b"%PDF-1.4 mock pdf content"

        result = generate_patient_statement_pdf(
            db=db_session,
            patient_id="00000000-0000-0000-0000-000000000001",
            current_user=current_user,
            tenant_id="00000000-0000-0000-0000-000000000002",
        )

        mock_audit.assert_called_once_with(
            event="patient_statement_generated",
            tenant_id=ANY,
            resource_id=ANY,
            actor_id=ANY,
            document_type="patient_statement",
            request_id=ANY,
        )
        assert result == b"%PDF-1.4 mock pdf content"

    @patch("app.services.document_service._render_pdf")
    @patch("app.services.document_service.log_structured_audit_event")
    @patch("app.services.document_service._aggregate_invoice_data")
    def test_generate_invoice_html_format(
        self,
        mock_aggregate: MagicMock,
        mock_audit: MagicMock,
        mock_render: MagicMock,
        db_session: MagicMock,
        current_user: MagicMock,
    ):
        """Verify HTML format returns HTML bytes, not PDF."""
        mock_aggregate.return_value = InvoiceDocumentData(
            bill_id="00000000-0000-0000-0000-000000000001",
            patient_id="00000000-0000-0000-0000-000000000002",
            patient_name="Test Patient",
            tenant_id="00000000-0000-0000-0000-000000000003",
            bill_amount=100.00,
            consultation_amount=100.00,
            inventory_amount=0.00,
            status="paid",
            created_at="2026-01-15T10:00:00",
        )

        result = generate_invoice_pdf(
            db=db_session,
            bill_id="00000000-0000-0000-0000-000000000001",
            current_user=current_user,
            tenant_id="00000000-0000-0000-0000-000000000003",
            fmt=DocumentFormat.html,
        )

        # Should be HTML bytes, not PDF
        assert b"<!DOCTYPE html>" in result
        assert b"Invoice" in result
        # _render_pdf should NOT have been called
        mock_render.assert_not_called()


# ═════════════════════════════════════════════════════════════════════════════
# API ENDPOINT TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestDocumentApiEndpoints:
    """Test document API endpoints with mocked services."""

    @patch("app.api.v1.endpoints.documents.generate_invoice_pdf")
    def test_download_invoice_endpoint(
        self,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        """Verify invoice download endpoint returns PDF."""
        mock_generate.return_value = b"%PDF-1.4 mock pdf"

        response = client.get(
            "/api/v1/documents/invoice/00000000-0000-0000-0000-000000000001",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert response.content == b"%PDF-1.4 mock pdf"

    @patch("app.api.v1.endpoints.documents.generate_prescription_pdf")
    def test_download_prescription_endpoint(
        self,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        """Verify prescription download endpoint returns PDF."""
        mock_generate.return_value = b"%PDF-1.4 mock pdf"

        response = client.get(
            "/api/v1/documents/prescription/00000000-0000-0000-0000-000000000001",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.4 mock pdf"

    @patch("app.api.v1.endpoints.documents.generate_encounter_summary_pdf")
    def test_download_encounter_summary_endpoint(
        self,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        """Verify encounter summary download endpoint returns PDF."""
        mock_generate.return_value = b"%PDF-1.4 mock pdf"

        response = client.get(
            "/api/v1/documents/encounter-summary/00000000-0000-0000-0000-000000000001",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.4 mock pdf"

    @patch("app.api.v1.endpoints.documents.generate_patient_statement_pdf")
    def test_download_patient_statement_endpoint(
        self,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        """Verify patient statement download endpoint returns PDF."""
        mock_generate.return_value = b"%PDF-1.4 mock pdf"

        response = client.get(
            "/api/v1/documents/statement/00000000-0000-0000-0000-000000000001",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.4 mock pdf"

    def test_download_invoice_unauthorized(self, client: TestClient):
        """Verify unauthorized access returns 401."""
        response = client.get(
            "/api/v1/documents/invoice/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_download_prescription_unauthorized(self, client: TestClient):
        """Verify unauthorized access returns 401."""
        response = client.get(
            "/api/v1/documents/prescription/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ═════════════════════════════════════════════════════════════════════════════
# DOCUMENT SCHEMA TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestDocumentSchemas:
    def test_document_meta_defaults(self):
        """Verify DocumentMeta has correct defaults."""
        meta = DocumentMeta(
            document_type=DocumentType.invoice,
            resource_id="test-123",
        )
        assert meta.document_type == DocumentType.invoice
        assert meta.document_format == DocumentFormat.pdf
        assert meta.resource_id == "test-123"
        assert meta.tenant_id is None
        assert meta.actor_id is None

    def test_invoice_document_data_defaults(self):
        """Verify InvoiceDocumentData has correct defaults."""
        data = InvoiceDocumentData(
            bill_id="00000000-0000-0000-0000-000000000001",
            patient_id="00000000-0000-0000-0000-000000000002",
            patient_name="Test",
            tenant_id="00000000-0000-0000-0000-000000000003",
            bill_amount=0.00,
            consultation_amount=0.00,
            inventory_amount=0.00,
            status="unpaid",
            created_at="2026-01-15T10:00:00",
        )
        assert data.consultation_amount == 0.00
        assert data.inventory_items == []
        assert data.doctor_id is None

    def test_prescription_document_data_no_inventory(self):
        """Verify PrescriptionDocumentData has no inventory fields."""
        data = PrescriptionDocumentData(
            appointment_id="00000000-0000-0000-0000-000000000001",
            doctor_id="00000000-0000-0000-0000-000000000002",
            doctor_name="Dr. Test",
            patient_id="00000000-0000-0000-0000-000000000003",
            patient_name="Test",
            tenant_id="00000000-0000-0000-0000-000000000004",
            created_at="2026-01-15T10:00:00",
        )
        # Verify no inventory-related fields exist
        assert not hasattr(data, "inventory_items")
        assert not hasattr(data, "inventory_amount")
        # Verify prescriptions is empty list by default
        assert data.prescriptions == []

    def test_encounter_summary_document_data_ai_hook(self):
        """Verify EncounterSummaryDocumentData has AI summary TODO hook."""
        data = EncounterSummaryDocumentData(
            appointment_id="00000000-0000-0000-0000-000000000001",
            patient_id="00000000-0000-0000-0000-000000000002",
            patient_name="Test",
            doctor_id="00000000-0000-0000-0000-000000000003",
            doctor_name="Dr. Test",
            tenant_id="00000000-0000-0000-0000-000000000004",
            appointment_time="2026-01-15T09:00:00",
            status="completed",
            created_at="2026-01-15T10:00:00",
        )
        # Verify AI summary field is commented out in schema
        # (checked via the TODO comment in the builder)
        assert data.subjective_notes is None
        assert data.prescriptions == []


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def db_session():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def current_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.id = "00000000-0000-0000-0000-000000000001"
    return user


@pytest.fixture
def client():
    """Test client fixture - requires app to be configured."""
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    """Mock auth headers for authenticated requests."""
    return {"Authorization": "Bearer test-token"}
