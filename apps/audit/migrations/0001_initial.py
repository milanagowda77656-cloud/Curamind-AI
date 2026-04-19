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
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(choices=[('LOGIN', 'Login'), ('LOGOUT', 'Logout'), ('REGISTER', 'Register'), ('VIEW_RECORD', 'View Medical Record'), ('CREATE_RECORD', 'Create Medical Record'), ('UPDATE_RECORD', 'Update Medical Record'), ('DELETE_RECORD', 'Delete Medical Record'), ('UPLOAD_IMAGE', 'Upload Medical Image'), ('REVIEW_DIAGNOSTIC', 'Review Diagnostic Result'), ('RETRIGGER_ANALYSIS', 'Retrigger AI Analysis'), ('CREATE_APPOINTMENT', 'Create Appointment'), ('UPDATE_APPOINTMENT', 'Update Appointment'), ('UPDATE_PROFILE', 'Update Profile'), ('CHANGE_PASSWORD', 'Change Password'), ('PASSWORD_RESET', 'Password Reset'), ('PERMISSION_DENIED', 'Permission Denied'), ('SUSPICIOUS_ACTIVITY', 'Suspicious Activity')], max_length=50)),
                ('resource_type', models.CharField(max_length=100)),
                ('resource_id', models.CharField(blank=True, max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('extra_data', models.JSONField(blank=True, default=dict)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='accounts.user')),
            ],
            options={
                'verbose_name': 'Audit Log Entry',
                'verbose_name_plural': 'Audit Log Entries',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user', 'timestamp'], name='audit_user_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', 'timestamp'], name='audit_action_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['resource_type', 'resource_id'], name='audit_resource_idx'),
        ),
    ]
