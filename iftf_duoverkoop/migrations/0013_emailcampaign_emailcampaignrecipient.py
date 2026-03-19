from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('iftf_duoverkoop', '0012_emailtemplatesettings'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('audience_type', models.CharField(choices=[('ALL', 'All customers'), ('ASSOCIATIONS', 'Specific associations'), ('PERFORMANCE', 'Specific performance')], max_length=20)),
                ('subject_template', models.TextField()),
                ('text_template', models.TextField(blank=True, default='')),
                ('html_template', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('QUEUED', 'Queued'), ('RUNNING', 'Running'), ('SUCCEEDED', 'Succeeded'), ('PARTIAL_FAILED', 'Partially failed'), ('FAILED', 'Failed')], db_index=True, default='QUEUED', max_length=20)),
                ('total_recipients', models.PositiveIntegerField(default=0)),
                ('sent_count', models.PositiveIntegerField(default=0)),
                ('failed_count', models.PositiveIntegerField(default=0)),
                ('error_message', models.TextField(blank=True, default='')),
                ('audience_associations', models.ManyToManyField(blank=True, to='iftf_duoverkoop.association')),
                ('audience_performance', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='iftf_duoverkoop.performance')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='email_campaigns_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'permissions': [('manage_email_campaigns', 'Can create and send email campaigns'), ('view_email_campaign_reports', 'Can view email campaign reports')],
            },
        ),
        migrations.CreateModel(
            name='EmailCampaignRecipient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('customer_name', models.CharField(blank=True, default='', max_length=128)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('SENT', 'Sent'), ('FAILED', 'Failed')], db_index=True, default='PENDING', max_length=10)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, default='')),
                ('audience_context', models.TextField(blank=True, default='')),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipients', to='iftf_duoverkoop.emailcampaign')),
                ('purchase', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='iftf_duoverkoop.purchase')),
            ],
            options={
                'ordering': ['email'],
                'unique_together': {('campaign', 'email')},
            },
        ),
    ]

