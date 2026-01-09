from django import forms
from .models import Commentaire


class CommentaireForm(forms.ModelForm):
    """Formulaire pour ajouter un commentaire"""

    class Meta:
        model = Commentaire
        fields = ['texte']
        widgets = {
            'texte': forms.Textarea(attrs={
                'placeholder': 'Votre question sur ce bien...',
                'rows': 3,
                'class': 'w-full p-4 bg-apple-bg border-0 rounded-xl text-apple-text placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-apple-blue focus:bg-white transition-all resize-none'
            })
        }
        labels = {
            'texte': ''
        }
