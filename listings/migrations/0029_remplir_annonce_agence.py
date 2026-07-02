"""Remplit Annonce.agence depuis la cle texte client_reference."""
from django.db import migrations


def remplir_fk(apps, schema_editor):
    Annonce = apps.get_model('listings', 'Annonce')
    Agence = apps.get_model('listings', 'Agence')
    agences = {a.reference: a.id for a in Agence.objects.all()}
    for annonce in Annonce.objects.exclude(client_reference=''):
        agence_id = agences.get(annonce.client_reference)
        if agence_id:
            Annonce.objects.filter(id=annonce.id).update(agence_id=agence_id)


class Migration(migrations.Migration):
    dependencies = [
        ('listings', '0028_annonce_agence'),
    ]
    operations = [
        migrations.RunPython(remplir_fk, migrations.RunPython.noop),
    ]
