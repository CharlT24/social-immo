from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('listings', '0009_photo_inspiration'),
    ]

    operations = [
        migrations.CreateModel(
            name='PhotoCommentaire',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texte', models.TextField(max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('auteur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photo_commentaires', to=settings.AUTH_USER_MODEL)),
                ('photo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='commentaires', to='listings.photo')),
                ('photo_pro', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='commentaires', to='listings.prorealisationphoto')),
            ],
            options={
                'verbose_name': 'Commentaire Photo',
                'verbose_name_plural': 'Commentaires Photos',
                'ordering': ['-created_at'],
            },
        ),
    ]
