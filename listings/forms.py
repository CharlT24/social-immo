from django import forms
from .models import Commentaire, Agence


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


INPUT_CLASS = 'w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all'
SELECT_CLASS = INPUT_CLASS


class AgenceCreateForm(forms.Form):
    """Formulaire de creation d'agence + compte utilisateur"""

    # Infos agence
    nom_agence = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ex: Immobilier Dupont'}),
        label='Nom de l\'agence'
    )
    reference_agence = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ex: OI123'}),
        label='Reference client (du CRM)',
        help_text='La reference dans le flux XML'
    )
    feed_url = forms.URLField(
        widget=forms.URLInput(attrs={'class': INPUT_CLASS, 'placeholder': 'https://logiciel-immo-clean.vercel.app/api/export/socialimmo/...'}),
        label='URL du flux XML'
    )
    feed_type = forms.ChoiceField(
        choices=Agence.FEED_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
        label='Type de flux',
        initial='url'
    )
    logo_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': INPUT_CLASS, 'placeholder': 'https://...'}),
        label='URL du logo (optionnel)'
    )

    # Contact agence
    contact_nom = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nom du contact'}),
        label='Nom du contact'
    )
    contact_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'contact@agence.fr'}),
        label='Email du contact'
    )
    contact_telephone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': '06 12 34 56 78'}),
        label='Telephone'
    )
    adresse = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 2, 'placeholder': 'Adresse de l\'agence'}),
        label='Adresse'
    )

    # Compte utilisateur
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'identifiant de connexion'}),
        label='Identifiant du responsable'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'email@agence.fr'}),
        label='Email du responsable',
        help_text='Les identifiants seront envoyes a cette adresse'
    )

    def clean_reference_agence(self):
        ref = self.cleaned_data['reference_agence']
        if Agence.objects.filter(reference=ref).exists():
            raise forms.ValidationError('Une agence avec cette reference existe deja.')
        return ref

    def clean_username(self):
        from django.contrib.auth.models import User
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Ce nom d\'utilisateur est deja pris.')
        return username

    def clean_email(self):
        from django.contrib.auth.models import User
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Un compte avec cet email existe deja.')
        return email
