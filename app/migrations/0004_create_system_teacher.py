from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_system_teacher(apps, schema_editor):
    Teacher = apps.get_model("app", "Teacher")

    Teacher.objects.get_or_create(
        login_id="system@school.local",
        defaults={
            "name": "システム",
            "name_kana": "しすてむ",
            "password_hash": make_password("system_dummy_password"),
            "permission_level": "管理者",
            "gender": "その他",
            "birth_date": "2000-01-01",
            "phone": "",
            "user_type": "teacher",
        }
    )

class Migration(migrations.Migration):

    dependencies = [
        ("app", "0003_message_is_system"),
    ]

    operations = [
        migrations.RunPython(create_system_teacher),
    ]
