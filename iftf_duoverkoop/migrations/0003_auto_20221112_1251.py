# Generated by Django 3.2.8 on 2022-11-12 11:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('iftf_duoverkoop', '0002_auto_20221112_1250'),
    ]

    operations = [
        migrations.AlterField(
            model_name='performance',
            name='association',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='iftf_duoverkoop.association'),
        ),
        migrations.AlterField(
            model_name='purchase',
            name='ticket1',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='ticket1', to='iftf_duoverkoop.performance'),
        ),
        migrations.AlterField(
            model_name='purchase',
            name='ticket2',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='ticket2', to='iftf_duoverkoop.performance'),
        ),
    ]
