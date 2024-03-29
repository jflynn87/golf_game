# Generated by Django 2.0.4 on 2019-04-01 14:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('golf_app', '0011_auto_20190313_1820'),
    ]

    operations = [
        migrations.CreateModel(
            name='mpScores',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bracket', models.CharField(max_length=5)),
                ('round', models.FloatField()),
                ('match_num', models.CharField(max_length=5)),
                ('result', models.CharField(max_length=10)),
                ('score', models.CharField(max_length=10)),
            ],
        ),
        migrations.AddField(
            model_name='field',
            name='withdrawn',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='scoredetails',
            name='toPar',
            field=models.CharField(max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='mpscores',
            name='player',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='player', to='golf_app.Field'),
        ),
        migrations.AlterUniqueTogether(
            name='mpscores',
            unique_together={('player', 'round')},
        ),
    ]
