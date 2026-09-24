from django.db import migrations, models


def clear_thumbnails(apps, schema_editor):
    # Every existing value is a pasted URL, not a key in the thumbnail bucket.
    apps.get_model("courses", "Course").objects.exclude(thumbnail_key="").update(thumbnail_key="")


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0003_lesson_content_parts'),
    ]

    operations = [
        migrations.RenameField(
            model_name='course',
            old_name='thumbnail_url',
            new_name='thumbnail_key',
        ),
        migrations.AlterField(
            model_name='course',
            name='thumbnail_key',
            field=models.CharField(blank=True, help_text='Thumbnail bucket key.', max_length=500),
        ),
        migrations.RunPython(clear_thumbnails, migrations.RunPython.noop),
    ]
