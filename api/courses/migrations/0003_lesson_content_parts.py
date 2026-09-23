from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='lesson',
            old_name='content_body',
            new_name='body',
        ),
        migrations.AlterField(
            model_name='lesson',
            name='body',
            field=models.TextField(blank=True, help_text='Markdown.'),
        ),
        migrations.RemoveField(
            model_name='lesson',
            name='content_type',
        ),
        migrations.RemoveField(
            model_name='lesson',
            name='content_url',
        ),
        migrations.AddField(
            model_name='lesson',
            name='video_key',
            field=models.CharField(blank=True, help_text='Private bucket key.', max_length=500),
        ),
        migrations.AddField(
            model_name='lesson',
            name='slides_key',
            field=models.CharField(blank=True, help_text='Private bucket key.', max_length=500),
        ),
    ]
