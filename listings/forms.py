from django import forms
from .models import Commentaire, Agence, ProProfile, Annonce, InspirationTag


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


PRO_INPUT = 'w-full px-4 py-3.5 bg-apple-bg border border-transparent rounded-xl text-apple-text placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent focus:bg-white transition-all'
PRO_SELECT = PRO_INPUT


class ProInscriptionForm(forms.Form):
    """Inscription pro : cree un compte + profil pro en une etape"""

    # Compte
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': PRO_INPUT, 'placeholder': 'votre@email.com'}),
        label='Email'
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': PRO_INPUT, 'placeholder': 'Minimum 8 caracteres'}),
        label='Mot de passe', min_length=8
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': PRO_INPUT, 'placeholder': 'Confirmez le mot de passe'}),
        label='Confirmer le mot de passe', min_length=8
    )

    # Profil pro
    nom_entreprise = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': PRO_INPUT, 'placeholder': 'Ex: Studio Deco Paris'}),
        label='Nom de votre entreprise'
    )
    metier = forms.ChoiceField(
        choices=[('', 'Choisissez votre metier...')] + list(ProProfile.METIER_CHOICES),
        widget=forms.Select(attrs={'class': PRO_SELECT}),
        label='Votre metier'
    )
    telephone = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'class': PRO_INPUT, 'placeholder': '06 12 34 56 78'}),
        label='Telephone'
    )
    ville = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': PRO_INPUT, 'placeholder': 'Votre ville'}),
        label='Ville'
    )
    code_postal = forms.CharField(
        max_length=10, required=False,
        widget=forms.TextInput(attrs={'class': PRO_INPUT, 'placeholder': 'Ex: 75001'}),
        label='Code postal'
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': PRO_INPUT, 'rows': 3, 'placeholder': 'Decrivez votre activite en quelques mots...'}),
        label='Description'
    )
    site_web = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': PRO_INPUT, 'placeholder': 'https://www.monsite.fr'}),
        label='Site web'
    )

    def clean_email(self):
        from django.contrib.auth.models import User
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Un compte avec cet email existe deja.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Les mots de passe ne correspondent pas.')
        return cleaned


class ProRealisationForm(forms.Form):
    """Formulaire d'ajout de realisation pro"""

    titre = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': PRO_INPUT, 'placeholder': 'Ex: Renovation salon contemporain'}),
        label='Titre du projet'
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': PRO_INPUT, 'rows': 3, 'placeholder': 'Decrivez ce projet...'}),
        label='Description'
    )
    categorie = forms.ChoiceField(
        choices=[('', 'Style / ambiance...')] + list(Annonce.INSPIRATION_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': PRO_SELECT}),
        label='Categorie'
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=InspirationTag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label='Tags (3 a 5 max)',
        help_text='Selectionnez les tags qui decrivent le mieux cette realisation.'
    )
    photo_urls = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': PRO_INPUT, 'rows': 4,
            'placeholder': 'Collez une URL d\'image par ligne\nhttps://exemple.com/photo1.jpg\nhttps://exemple.com/photo2.jpg'
        }),
        label='Photos (URLs)',
        help_text='Une URL par ligne. Formats acceptes : JPG, PNG, WebP.'
    )
