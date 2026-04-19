from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Appointment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('appointment_type', models.CharField(choices=[('GENERAL', 'General Consultation'), ('FOLLOWUP', 'Follow-up'), ('DIAGNOSTIC', 'Diagnostic Review'), ('IMAGING', 'Imaging Review'), ('EMERGENCY', 'Emergency')], default='GENERAL', max_length=20)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('CONFIRMED', 'Confirmed'), ('CANCELLED', 'Cancelled'), ('COMPLETED', 'Completed'), ('NO_SHOW', 'No Show')], default='PENDING', max_length=20)),
                ('scheduled_at', models.DateTimeField()),
                ('duration_minutes', models.PositiveIntegerField(default=30)),
                ('reason', models.TextField()),
                ('notes', models.TextField(blank=True)),
                ('cancellation_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doctor', models.ForeignKey(limit_choices_to={'role': 'DOCTOR'}, on_delete=django.db.models.deletion.CASCADE, related_name='doctor_appointments', to='accounts.user')),
                ('patient', models.ForeignKey(limit_choices_to={'role': 'PATIENT'}, on_delete=django.db.models.deletion.CASCADE, related_name='patient_appointments', to='accounts.user')),
            ],
            options={'ordering': ['-scheduled_at']},
        ),
        migrations.CreateModel(
            name='AppointmentSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('is_booked', models.BooleanField(default=False)),
                ('doctor', models.ForeignKey(limit_choices_to={'role': 'DOCTOR'}, on_delete=django.db.models.deletion.CASCADE, related_name='appointment_slots', to='accounts.user')),
                ('appointment', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='slot', to='appointments.appointment')),
            ],
            options={'ordering': ['date', 'start_time']},
        ),
        migrations.AddIndex(
            model_name='appointment',
            index=models.Index(fields=['patient', 'status'], name='appt_patient_status_idx'),
        ),
        migrations.AddIndex(
            model_name='appointment',
            index=models.Index(fields=['doctor', 'scheduled_at'], name='appt_doctor_scheduled_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='appointmentslot',
            unique_together={('doctor', 'date', 'start_time')},
        ),
    ]
