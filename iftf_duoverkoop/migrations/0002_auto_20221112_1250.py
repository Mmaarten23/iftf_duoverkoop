# Generated by Django 3.2.8 on 2022-11-12 11:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('iftf_duoverkoop', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='association',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='iftf_duoverkoop/media/associations'),
        ),
        migrations.AddField(
            model_name='performance',
            name='association',
            field=models.ForeignKey(default='NONE', editable=False, on_delete=django.db.models.deletion.CASCADE, to='iftf_duoverkoop.association'),
        ),
        migrations.AddField(
            model_name='purchase',
            name='ticket1',
            field=models.ForeignKey(default='NONE', editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='ticket1', to='iftf_duoverkoop.performance'),
        ),
        migrations.AddField(
            model_name='purchase',
            name='ticket2',
            field=models.ForeignKey(default='NONE', editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='ticket2', to='iftf_duoverkoop.performance'),
        ),
    ]
