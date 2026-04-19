from django.db import migrations, models
import django.db.models.deletion
import apps.medical_records.models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MedicalRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('record_type', models.CharField(choices=[('CONSULTATION', 'Consultation Notes'), ('LAB_RESULT', 'Lab Result'), ('PRESCRIPTION', 'Prescription'), ('IMAGING', 'Imaging / Radiology'), ('SURGERY', 'Surgery Report'), ('ALLERGY', 'Allergy Record'), ('VACCINATION', 'Vaccination'), ('OTHER', 'Other')], max_length=20)),
                ('diagnosis', models.TextField(blank=True, db_column='diagnosis')),
                ('notes', models.TextField(blank=True, db_column='notes')),
                ('prescription', models.TextField(blank=True, db_column='prescription')),
                ('title', models.CharField(max_length=255)),
                ('is_critical', models.BooleanField(default=False)),
                ('follow_up_required', models.BooleanField(default=False)),
                ('follow_up_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doctor', models.ForeignKey(limit_choices_to={'role__in': ['DOCTOR', 'NURSE', 'RADIOLOGIST']}, on_delete=django.db.models.deletion.CASCADE, related_name='created_records', to='accounts.user')),
                ('patient', models.ForeignKey(limit_choices_to={'role': 'PATIENT'}, on_delete=django.db.models.deletion.CASCADE, related_name='medical_records', to='accounts.user')),
            ],
            options={
                'ordering': ['-created_at'],
                'permissions': [('view_own_record', 'Can view own medical record'), ('view_patient_record', 'Can view patient medical record (Doctor)')],
            },
        ),
        migrations.CreateModel(
            name='MedicalImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to=apps.medical_records.models.medical_image_upload_path, validators=[apps.medical_records.models.validate_medical_file])),
                ('original_filename', models.CharField(max_length=255)),
                ('mime_type', models.CharField(blank=True, max_length=100)),
                ('file_size_bytes', models.PositiveBigIntegerField(default=0)),
                ('is_dicom', models.BooleanField(default=False)),
                ('dicom_patient_name', models.CharField(blank=True, max_length=255)),
                ('dicom_study_date', models.DateField(blank=True, null=True)),
                ('dicom_modality', models.CharField(blank=True, max_length=20)),
                ('dicom_body_part', models.CharField(blank=True, max_length=100)),
                ('dicom_series_description', models.CharField(blank=True, max_length=255)),
                ('ai_processed', models.BooleanField(default=False)),
                ('ai_heatmap_file', models.FileField(blank=True, null=True, upload_to='heatmaps/')),
                ('ai_anomaly_score', models.FloatField(blank=True, null=True)),
                ('ai_findings', models.TextField(blank=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='medical_records.medicalrecord')),
            ],
            options={'ordering': ['-uploaded_at']},
        ),
        migrations.AddIndex(
            model_name='medicalrecord',
            index=models.Index(fields=['patient', 'record_type'], name='medrec_patient_type_idx'),
        ),
        migrations.AddIndex(
            model_name='medicalrecord',
            index=models.Index(fields=['doctor', 'created_at'], name='medrec_doctor_created_idx'),
        ),
    ]
