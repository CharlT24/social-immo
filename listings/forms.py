from django import forms
from .models import Commentaire, Agence, ProProfile, Annonce, InspirationTag, UserProfile


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
        label='Votre metier principal'
    )
    autres_metiers = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={'class': PRO_INPUT,
                                      'placeholder': 'Ex: Plomberie, Electricite, Peinture'}),
        label='Autres corps de metier (optionnel)',
        help_text="Pour les entreprises tous corps d'etat : listez vos specialites, separees par des virgules."
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
    siret = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'class': PRO_INPUT, 'placeholder': '14 chiffres — pour obtenir le badge Verifie'}),
        label='SIRET'
    )
    google_business_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': PRO_INPUT, 'placeholder': 'https://g.page/... ou lien Google Maps'}),
        label='Lien Google (fiche / avis)'
    )

    def __init__(self, *args, existing_user=None, **kwargs):
        """existing_user : si un utilisateur DEJA connecte devient pro, on
        rattache le profil a son compte (pas de nouveau compte, pas de mot de
        passe a redonner)."""
        super().__init__(*args, **kwargs)
        self.existing_user = existing_user
        if existing_user:
            for champ in ('email', 'password1', 'password2'):
                self.fields[champ].required = False
            self.fields['email'].initial = existing_user.email

    def clean_email(self):
        from django.contrib.auth.models import User
        email = self.cleaned_data.get('email', '')
        # Utilisateur deja connecte : on garde son email, aucun conflit.
        if self.existing_user:
            return email or self.existing_user.email
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Un compte avec cet email existe deja — connectez-vous, puis creez votre profil pro.')
        return email

    def clean(self):
        cleaned = super().clean()
        # Verification du mot de passe uniquement pour un NOUVEAU compte.
        if not getattr(self, 'existing_user', None):
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


# --- Espace Particulier ---

PART_INPUT = 'w-full px-4 py-3.5 bg-apple-bg border border-transparent rounded-xl text-apple-text placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent focus:bg-white transition-all'
PART_SELECT = PART_INPUT
PART_TEXTAREA = PART_INPUT + ' resize-none'

TYPE_BIEN_CHOICES = [
    ('', 'Type de bien...'),
    ('Appartement', 'Appartement'),
    ('Maison', 'Maison'),
    ('Terrain', 'Terrain'),
    ('Studio', 'Studio'),
    ('Loft', 'Loft'),
    ('Villa', 'Villa'),
    ('Duplex', 'Duplex'),
    ('Parking', 'Parking / Box'),
    ('Commerce', 'Local commercial'),
    ('Bureau', 'Bureau'),
    ('Immeuble', 'Immeuble'),
    ('Autre', 'Autre'),
]

DPE_CHOICES = [('', 'Non renseigne')] + [(l, l) for l in 'ABCDEFG']


class ParticulierAnnonceForm(forms.ModelForm):
    """Formulaire de depot d'annonce pour les particuliers (type LeBonCoin)"""

    libelle_type = forms.ChoiceField(
        choices=TYPE_BIEN_CHOICES,
        widget=forms.Select(attrs={'class': PART_SELECT}),
        label='Type de bien'
    )
    type_transaction = forms.ChoiceField(
        choices=[('V', 'Vente'), ('L', 'Location'), ('S', 'Location courte durée')],
        widget=forms.Select(attrs={'class': PART_SELECT, 'onchange': 'majTypeCourteDuree()'}),
        label='Type d\'annonce'
    )
    dpe_etiquette_conso = forms.ChoiceField(
        choices=DPE_CHOICES, required=False,
        widget=forms.Select(attrs={'class': PART_SELECT}),
        label='DPE Energie'
    )
    dpe_etiquette_ges = forms.ChoiceField(
        choices=DPE_CHOICES, required=False,
        widget=forms.Select(attrs={'class': PART_SELECT}),
        label='DPE GES'
    )

    class Meta:
        model = Annonce
        fields = [
            'titre', 'texte', 'libelle_type', 'type_transaction',
            'prix', 'loyer_mensuel', 'charges_locatives',
            'prix_nuit', 'nb_voyageurs', 'nuits_min', 'frais_menage', 'depot_garantie',
            'equip_wifi', 'equip_cuisine', 'equip_lave_linge', 'equip_clim',
            'equip_tv', 'equip_piscine', 'equip_animaux',
            'ville', 'code_postal',
            'nb_pieces', 'nb_chambres', 'surface', 'surface_terrain',
            'etage', 'ascenseur', 'parking', 'meuble', 'exterieur',
            'dpe_etiquette_conso', 'dpe_valeur_conso',
            'dpe_etiquette_ges', 'dpe_valeur_ges',
            'visite_virtuelle_url',
        ]
        widgets = {
            'visite_virtuelle_url': forms.URLInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Lien Matterport / visite 3D (https://my.matterport.com/show/?m=...)'
            }),
            'titre': forms.TextInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Ex: Appartement 3 pieces lumineux centre-ville'
            }),
            'texte': forms.Textarea(attrs={
                'class': PART_TEXTAREA,
                'rows': 5,
                'placeholder': 'Decrivez votre bien : etat, equipements, environnement, transports...'
            }),
            'prix': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Prix en euros'
            }),
            'loyer_mensuel': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Loyer mensuel en euros'
            }),
            'charges_locatives': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Charges mensuelles en euros'
            }),
            'prix_nuit': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Prix par nuit en euros'
            }),
            'nb_voyageurs': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Nombre de voyageurs (capacité)'
            }),
            'nuits_min': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Nombre de nuits minimum'
            }),
            'frais_menage': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Frais de ménage (optionnel)'
            }),
            'depot_garantie': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Caution (optionnel)'
            }),
            'ville': forms.TextInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Ville'
            }),
            'code_postal': forms.TextInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Code postal'
            }),
            'nb_pieces': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Nombre de pieces'
            }),
            'nb_chambres': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Nombre de chambres'
            }),
            'surface': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Surface habitable en m2'
            }),
            'surface_terrain': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Surface terrain en m2 (optionnel)'
            }),
            'dpe_valeur_conso': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Valeur kWh/m2/an'
            }),
            'dpe_valeur_ges': forms.NumberInput(attrs={
                'class': PART_INPUT,
                'placeholder': 'Valeur kgCO2/m2/an'
            }),
        }
        labels = {
            'titre': 'Titre de l\'annonce',
            'texte': 'Description',
            'prix': 'Prix (euros)',
            'loyer_mensuel': 'Loyer mensuel (euros)',
            'charges_locatives': 'Charges (euros/mois)',
            'prix_nuit': 'Prix par nuit (euros)',
            'nb_voyageurs': 'Voyageurs (capacité)',
            'nuits_min': 'Nuits minimum',
            'frais_menage': 'Frais de ménage (euros)',
            'depot_garantie': 'Caution (euros)',
            'ville': 'Ville',
            'code_postal': 'Code postal',
            'nb_pieces': 'Pieces',
            'nb_chambres': 'Chambres',
            'surface': 'Surface habitable (m2)',
            'surface_terrain': 'Surface terrain (m2)',
            'dpe_valeur_conso': 'Valeur energie (kWh/m2/an)',
            'dpe_valeur_ges': 'Valeur GES (kgCO2/m2/an)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le prix (vente) ne doit pas etre requis au niveau du champ : selon le
        # type d'annonce c'est le loyer (L) ou le prix/nuit (S) qui compte. La
        # bonne exigence est verifiee par type dans clean().
        self.fields['prix'].required = False

    def clean(self):
        cleaned = super().clean()
        transaction = cleaned.get('type_transaction')
        if transaction == 'V' and not cleaned.get('prix'):
            self.add_error('prix', 'Le prix est requis pour une vente.')
        if transaction == 'L' and not cleaned.get('loyer_mensuel'):
            self.add_error('loyer_mensuel', 'Le loyer est requis pour une location.')
        if transaction == 'S' and not cleaned.get('prix_nuit'):
            self.add_error('prix_nuit', 'Le prix par nuit est requis pour une location courte durée.')
        return cleaned


class UserProfileForm(forms.Form):
    """Formulaire de profil utilisateur particulier"""

    first_name = forms.CharField(
        max_length=30, required=False,
        widget=forms.TextInput(attrs={'class': PART_INPUT, 'placeholder': 'Prenom'}),
        label='Prenom'
    )
    last_name = forms.CharField(
        max_length=30, required=False,
        widget=forms.TextInput(attrs={'class': PART_INPUT, 'placeholder': 'Nom'}),
        label='Nom'
    )
    telephone = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'class': PART_INPUT, 'placeholder': '06 12 34 56 78'}),
        label='Telephone'
    )
    ville = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': PART_INPUT, 'placeholder': 'Votre ville'}),
        label='Ville'
    )
    code_postal = forms.CharField(
        max_length=10, required=False,
        widget=forms.TextInput(attrs={'class': PART_INPUT, 'placeholder': 'Code postal'}),
        label='Code postal'
    )
