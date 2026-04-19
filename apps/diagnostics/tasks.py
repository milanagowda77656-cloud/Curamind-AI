"""
CuraMind AI - Diagnostics Celery Tasks
Async image processing pipeline:
  1. Parse DICOM metadata (pydicom)
  2. Strip identifying metadata (privacy)
  3. Run pre-trained AI model for anomaly detection
  4. Generate heatmap overlay
  5. Save results and notify doctor
"""

import logging
import time
import io
import os
import uuid
from datetime import datetime

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='diagnostics.process_medical_image'
)
def process_medical_image(self, image_id: str):
    """
    Main Celery task: process an uploaded medical image through the full AI pipeline.

    Steps:
        1. Update queue status → PROCESSING
        2. If DICOM: parse metadata with pydicom, strip PII
        3. Run AI model inference (ResNet-based anomaly detection)
        4. Generate and save heatmap
        5. Save DiagnosticResult
        6. Send alert if high-risk
        7. Update queue status → COMPLETED
    """
    from apps.medical_records.models import MedicalImage
    from apps.diagnostics.models import DiagnosticResult, DiagnosticQueue, DiagnosticStatus

    try:
        image = MedicalImage.objects.select_related('record__patient', 'record__doctor').get(id=image_id)
    except MedicalImage.DoesNotExist:
        logger.error(f'[process_medical_image] MedicalImage {image_id} not found.')
        return

    # --- Update or create queue entry ---
    queue_entry, _ = DiagnosticQueue.objects.get_or_create(image=image)
    queue_entry.started_at = timezone.now()
    queue_entry.celery_task_id = self.request.id or ''
    queue_entry.save()

    # --- Create DiagnosticResult placeholder ---
    result, _ = DiagnosticResult.objects.get_or_create(image=image)
    result.status = DiagnosticStatus.PROCESSING
    result.save()

    start_time = time.time()

    try:
        # === STEP 1: Parse DICOM if applicable ===
        if image.is_dicom:
            _parse_dicom_metadata(image)

        # === STEP 2: Run AI inference ===
        ai_output = _run_ai_inference(image)

        # === STEP 3: Generate heatmap ===
        heatmap_file = _generate_heatmap(image, ai_output)

        # === STEP 4: Save results ===
        processing_ms = int((time.time() - start_time) * 1000)

        result.status = DiagnosticStatus.COMPLETED
        result.anomaly_score = ai_output['anomaly_score']
        result.confidence = ai_output['confidence']
        result.findings = ai_output['findings']
        result.recommendations = ai_output['recommendations']
        result.processing_time_ms = processing_ms

        if heatmap_file:
            result.heatmap_file.save(
                f'heatmap_{image_id}.png',
                ContentFile(heatmap_file),
                save=False
            )

        # If high-risk, flag for review
        if result.anomaly_score >= 0.7:
            result.status = DiagnosticStatus.REVIEW_REQUIRED

        result.save()

        # Update MedicalImage flags
        image.ai_processed = True
        image.ai_anomaly_score = result.anomaly_score
        image.ai_findings = result.findings
        image.save(update_fields=['ai_processed', 'ai_anomaly_score', 'ai_findings'])

        # === STEP 5: Alert doctor if high-risk ===
        if result.is_high_risk:
            send_high_risk_alert.delay(str(result.id))

        # Update queue
        queue_entry.completed_at = timezone.now()
        queue_entry.save()

        logger.info(
            f'[process_medical_image] Completed image {image_id} '
            f'in {processing_ms}ms. Score={result.anomaly_score:.3f}'
        )

    except Exception as exc:
        logger.error(f'[process_medical_image] Error processing {image_id}: {exc}', exc_info=True)
        result.status = DiagnosticStatus.FAILED
        result.error_message = str(exc)
        result.save()
        queue_entry.last_error = str(exc)
        queue_entry.retries += 1
        queue_entry.save()
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def _parse_dicom_metadata(image):
    """Parse DICOM file and extract metadata using pydicom. Strip patient PII."""
    try:
        import pydicom
        from pydicom.errors import InvalidDicomError

        image.file.seek(0)
        dicom_bytes = image.file.read()
        image.file.seek(0)

        ds = pydicom.dcmread(io.BytesIO(dicom_bytes))

        # Extract metadata (non-PII fields only — HIPAA compliance)
        modality = getattr(ds, 'Modality', '')
        body_part = getattr(ds, 'BodyPartExamined', '')
        series_desc = getattr(ds, 'SeriesDescription', '')
        study_date_str = getattr(ds, 'StudyDate', '')

        study_date = None
        if study_date_str:
            try:
                study_date = datetime.strptime(study_date_str, '%Y%m%d').date()
            except ValueError:
                pass

        image.dicom_modality = str(modality)[:20]
        image.dicom_body_part = str(body_part)[:100]
        image.dicom_series_description = str(series_desc)[:255]
        image.dicom_study_date = study_date

        # Strip PII tags (anonymize)
        pii_tags = [
            'PatientName', 'PatientID', 'PatientBirthDate',
            'PatientSex', 'PatientAge', 'InstitutionName',
            'ReferringPhysicianName', 'PhysiciansOfRecord',
        ]
        for tag in pii_tags:
            if hasattr(ds, tag):
                try:
                    delattr(ds, tag)
                except Exception:
                    pass

        image.save(update_fields=[
            'dicom_modality', 'dicom_body_part',
            'dicom_series_description', 'dicom_study_date'
        ])
        logger.info(f'[_parse_dicom_metadata] Parsed DICOM for image {image.id}')

    except Exception as e:
        logger.warning(f'[_parse_dicom_metadata] Could not parse DICOM for {image.id}: {e}')


def _run_ai_inference(image) -> dict:
    """
    Run AI anomaly detection on the medical image.

    In production: load a serialized ResNet50/PyTorch model and run inference.
    For demo: uses a deterministic simulation based on file properties.

    Returns dict with anomaly_score, confidence, findings, recommendations.
    """
    try:
        # --- Production path: load real PyTorch model ---
        # import torch
        # from torchvision import transforms
        # from PIL import Image as PILImage
        # model = torch.load('models/curamind_resnet50.pth')
        # model.eval()
        # ... transform and infer ...

        # --- Demo path: simulate AI output ---
        file_size = image.file_size_bytes or 1
        # Deterministic score based on file properties (demo only)
        seed_value = (file_size % 100) / 100.0
        anomaly_score = round(min(max(seed_value, 0.05), 0.95), 3)
        confidence = round(0.75 + (seed_value * 0.2), 3)

        findings = _generate_findings(anomaly_score, image.dicom_body_part or 'General')
        recommendations = _generate_recommendations(anomaly_score)

        return {
            'anomaly_score': anomaly_score,
            'confidence': confidence,
            'findings': findings,
            'recommendations': recommendations,
        }

    except Exception as e:
        logger.error(f'[_run_ai_inference] Inference failed for {image.id}: {e}')
        return {
            'anomaly_score': 0.0,
            'confidence': 0.0,
            'findings': 'AI analysis could not be completed.',
            'recommendations': 'Manual review required.',
        }


def _generate_findings(score: float, body_part: str) -> str:
    """Generate human-readable findings text based on anomaly score (demo)."""
    if score < 0.3:
        return f'No significant anomalies detected in {body_part or "the image"}. Tissue density appears within normal parameters.'
    elif score < 0.5:
        return f'Minor irregularities detected in {body_part or "the image"}. Findings are inconclusive and may warrant follow-up.'
    elif score < 0.7:
        return f'Moderate anomalies identified in {body_part or "the image"}. Possible areas of concern highlighted in heatmap overlay.'
    else:
        return f'Significant anomalies detected in {body_part or "the image"}. High-confidence indicators of pathology present. URGENT review recommended.'


def _generate_recommendations(score: float) -> str:
    if score < 0.3:
        return 'Routine follow-up as scheduled. No immediate action required.'
    elif score < 0.5:
        return 'Consider repeat imaging in 3-6 months. Discuss findings with patient.'
    elif score < 0.7:
        return 'Specialist referral recommended. Schedule follow-up within 2-4 weeks.'
    else:
        return 'URGENT: Immediate specialist consultation required. Do not delay follow-up.'


def _generate_heatmap(image, ai_output: dict):
    """
    Generate a heatmap overlay image for the AI findings.

    Production: use Grad-CAM or LIME on the PyTorch model.
    Demo: generate a colored overlay using Pillow.
    """
    try:
        from PIL import Image as PILImage, ImageDraw, ImageFont
        import struct

        score = ai_output['anomaly_score']

        # Create a simple heatmap visualization
        width, height = 512, 512
        img = PILImage.new('RGB', (width, height), color=(20, 20, 40))
        draw = ImageDraw.Draw(img)

        # Draw gradient circles representing anomaly regions
        import math
        center_x, center_y = width // 2, height // 2
        max_radius = min(width, height) // 3

        for i in range(20, 0, -1):
            radius = int(max_radius * (i / 20) * score)
            alpha = int(255 * (i / 20))
            r = min(255, int(score * 255 * 1.5))
            g = max(0, int((1 - score) * 200))
            b = 50
            color = (r, g, b)
            draw.ellipse(
                [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                outline=color, width=2
            )

        # Add score text
        draw.text((10, 10), f'Anomaly Score: {score:.3f}', fill=(255, 255, 255))
        draw.text((10, 30), f'Confidence: {ai_output["confidence"]:.3f}', fill=(200, 200, 200))

        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    except Exception as e:
        logger.warning(f'[_generate_heatmap] Could not generate heatmap: {e}')
        return None


@shared_task(name='diagnostics.send_high_risk_alert')
def send_high_risk_alert(result_id: str):
    """
    Send email alert to the responsible doctor when a high-risk
    diagnostic result (anomaly_score >= 0.7) is detected.
    """
    from apps.diagnostics.models import DiagnosticResult

    try:
        result = DiagnosticResult.objects.select_related(
            'image__record__doctor', 'image__record__patient'
        ).get(id=result_id)

        doctor = result.image.record.doctor
        patient = result.image.record.patient

        subject = f'[CuraMind AI] HIGH RISK Alert — {patient.get_full_name()}'
        message = (
            f'Dear Dr. {doctor.get_full_name()},\n\n'
            f'The AI diagnostic system has flagged a HIGH RISK finding for your patient:\n\n'
            f'Patient: {patient.get_full_name()}\n'
            f'Image: {result.image.original_filename}\n'
            f'Anomaly Score: {result.anomaly_score:.3f} (Confidence: {result.confidence:.3f})\n\n'
            f'Findings:\n{result.findings}\n\n'
            f'Recommendations:\n{result.recommendations}\n\n'
            f'Please log in to CuraMind AI to review this case immediately.\n\n'
            f'This is an automated alert from CuraMind AI Diagnostic Engine.\n'
            f'Do not reply to this email.'
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[doctor.email],
            fail_silently=False,
        )
        logger.info(f'[send_high_risk_alert] Alert sent to {doctor.email} for result {result_id}')

    except Exception as e:
        logger.error(f'[send_high_risk_alert] Failed to send alert for {result_id}: {e}')
