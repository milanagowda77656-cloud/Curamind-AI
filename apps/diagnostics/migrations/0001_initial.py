from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('medical_records', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiagnosticResult',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('QUEUED', 'Queued'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed'), ('REVIEW_REQUIRED', 'Review Required')], default='QUEUED', max_length=20)),
                ('model_name', models.CharField(default='ResNet50-CuraMind-v1', max_length=100)),
                ('model_version', models.CharField(default='1.0.0', max_length=20)),
                ('anomaly_score', models.FloatField(blank=True, null=True)),
                ('confidence', models.FloatField(blank=True, null=True)),
                ('findings', models.TextField(blank=True)),
                ('recommendations', models.TextField(blank=True)),
                ('heatmap_file', models.FileField(blank=True, null=True, upload_to='heatmaps/')),
                ('processing_time_ms', models.PositiveIntegerField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('radiologist_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('image', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='diagnostic_result', to='medical_records.medicalimage')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_diagnostics', to='accounts.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='DiagnosticQueue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('celery_task_id', models.CharField(blank=True, max_length=255)),
                ('queued_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('retries', models.PositiveIntegerField(default=0)),
                ('last_error', models.TextField(blank=True)),
                ('image', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='queue_entry', to='medical_records.medicalimage')),
            ],
        ),
    ]
