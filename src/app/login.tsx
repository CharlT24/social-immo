import React, { useState, useEffect } from 'react';
import { supabase } from '../../../lib/supabaseClient';
import { useRouter } from 'next/router';
import Link from 'next/link';

// Type pour les pages avec layout personnalisé
type NextPageWithLayout = React.FC & {
  getLayout?: (page: React.ReactElement) => React.ReactNode;
};

interface LoginForm {
  email: string;
  password: string;
}

const SocialImmoLoginPage: NextPageWithLayout = () => {
  const [formData, setFormData] = useState<LoginForm>({
    email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [currentSession, setCurrentSession] = useState<any>(null);
  const router = useRouter();

  // Récupérer les paramètres d'erreur de l'URL
  useEffect(() => {
    const urlError = router.query.error as string;
    if (urlError === 'access_denied') {
      setError('Votre compte n\'a pas les permissions pour accéder à Social Immo');
    } else if (urlError === 'auth_failed') {
      setError('Erreur d\'authentification. Veuillez vous reconnecter.');
    }
  }, [router.query]);

  // Vérifier si déjà connecté - SANS REDIRECTION AUTO
  useEffect(() => {
    if (!sessionChecked) {
      checkExistingSession();
    }
  }, [sessionChecked]);

  const checkExistingSession = async () => {
    try {
      console.log('🔍 Vérification session existante...');
      
      const { data: { session }, error } = await Promise.race([
        supabase.auth.getSession(),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Timeout session check')), 5000)
        )
      ]) as any;

      if (error) {
        console.log('⚠️ Erreur session check:', error);
        setSessionChecked(true);
        return;
      }

      // ✅ STOCKER LA SESSION au lieu de rediriger
      setCurrentSession(session);
      console.log(session ? '✅ Session existante trouvée' : '❌ Aucune session');
    } catch (error: any) {
      console.log('⚠️ Erreur lors de la vérification de session:', error);
    } finally {
      setSessionChecked(true);
    }
  };

  // ✅ FONCTION DE DÉCONNEXION
  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      setCurrentSession(null);
      setError(null);
      console.log('✅ Déconnexion réussie');
    } catch (error) {
      console.error('❌ Erreur déconnexion:', error);
      setError('Erreur lors de la déconnexion');
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      console.log('🔐 Tentative de connexion...');

      // Connexion Supabase Auth avec timeout
      const { data: authData, error: authError } = await Promise.race([
        supabase.auth.signInWithPassword({
          email: formData.email.trim(),
          password: formData.password
        }),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Timeout connexion')), 10000)
        )
      ]) as any;

      if (authError) {
        throw authError;
      }

      if (!authData.user) {
        throw new Error('Échec de la connexion');
      }

      console.log('✅ Connexion réussie, vérification utilisateur...');

      // Vérifier si l'utilisateur existe dans la table utilisateurs
      const { data: userData, error: userError } = await supabase
        .from('utilisateurs')
        .select('id, role, actif, statut_validation, prenom, nom, email')
        .eq('id', authData.user.id)
        .single();

      if (userError) {
        // 🆕 CRÉATION AUTOMATIQUE si utilisateur n'existe pas
        console.log('👤 Utilisateur non trouvé, création automatique...');
        
        const newUserData = {
          id: authData.user.id,
          email: authData.user.email,
          prenom: authData.user.user_metadata?.prenom || 'Utilisateur',
          nom: authData.user.user_metadata?.nom || 'Social Immo',
          telephone: authData.user.user_metadata?.telephone || '',
          role: 'externe',
          statut_externe: 'acheteur', // Par défaut
          statut_validation: 'valide', // ✅ VALIDATION AUTOMATIQUE
          actif: true,
          created_at: new Date().toISOString()
        };

        const { error: insertError } = await supabase
          .from('utilisateurs')
          .insert([newUserData]);

        if (insertError) {
          console.error('❌ Erreur création utilisateur:', insertError);
          throw new Error('Erreur lors de la création de votre profil');
        }

        console.log('✅ Utilisateur créé automatiquement');
      } else {
        console.log('✅ Utilisateur existant trouvé:', userData);
        
        // Vérifier que l'utilisateur est actif (pas de restriction stricte)
        if (!userData.actif) {
          throw new Error('Votre compte a été désactivé. Contactez le support.');
        }
      }

      console.log('✅ Accès autorisé, redirection vers Social Immo...');
      
      // ✅ REDIRECTION VERS SOCIAL IMMO
      setTimeout(() => {
        router.push('/public/socialimmo');
      }, 500);

    } catch (error: any) {
      console.error('❌ Erreur connexion:', error);
      
      if (error.message === 'Invalid login credentials') {
        setError('Email ou mot de passe incorrect');
      } else if (error.message?.includes('Timeout')) {
        setError('La connexion prend trop de temps. Vérifiez votre connexion internet.');
      } else {
        setError(error.message || 'Erreur lors de la connexion');
      }
    } finally {
      setLoading(false);
    }
  };

  // Affichage pendant la vérification de session
  if (!sessionChecked) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-orange-100 flex items-center justify-center p-4">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-orange-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Vérification de votre session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-orange-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-600 rounded-full mb-4">
            <span className="text-white text-2xl font-bold">SI</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Social Immo
          </h1>
          <p className="text-gray-600">
            Le réseau social de l'immobilier
          </p>
        </div>

        {/* Formulaire de connexion */}
        <div className="bg-white rounded-lg shadow-md p-6">
          {/* ✅ MESSAGE SI DÉJÀ CONNECTÉ */}
          {currentSession && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-green-800 font-semibold">Déjà connecté !</h3>
                  <p className="text-green-700 text-sm">Vous êtes connecté en tant que : {currentSession.user.email}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="text-red-600 hover:text-red-700 text-sm font-medium"
                >
                  Se déconnecter
                </button>
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => router.push('/public/socialimmo')}
                  className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700"
                >
                  Aller à Social Immo →
                </button>
                <button
                  onClick={handleLogout}
                  className="bg-gray-500 text-white px-4 py-2 rounded text-sm hover:bg-gray-600"
                >
                  Changer de compte
                </button>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
                disabled={loading}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent disabled:opacity-50"
                placeholder="votre.email@exemple.com"
              />
            </div>

            {/* Mot de passe */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Mot de passe
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                required
                disabled={loading}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent disabled:opacity-50"
                placeholder="••••••••"
              />
            </div>

            {/* Erreur */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            {/* Info création automatique */}
            <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
              <p className="text-orange-700 text-sm">
                ✨ <strong>Accès simplifié :</strong> Connectez-vous avec vos identifiants. 
                Si c'est votre première connexion, votre profil sera créé automatiquement !
              </p>
            </div>

            {/* Bouton de connexion */}
            <button
              type="submit"
              disabled={loading || !formData.email || !formData.password}
              className="w-full bg-orange-600 text-white py-3 px-4 rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Connexion...
                </span>
              ) : (
                'Se connecter à Social Immo'
              )}
            </button>
          </form>

          {/* Liens */}
          <div className="mt-6 text-center space-y-3">
            <p className="text-sm text-gray-600">
              Pas encore de compte ?{' '}
              <Link href="/public/register" className="text-orange-600 hover:text-orange-700 font-medium">
                Créer un compte
              </Link>
            </p>
            
            <div className="flex items-center">
              <div className="flex-1 border-t border-gray-300"></div>
              <span className="px-3 text-sm text-gray-500">ou</span>
              <div className="flex-1 border-t border-gray-300"></div>
            </div>

            <p className="text-sm text-gray-600">
              Accès professionnel CRM ?{' '}
              <Link href="/login" className="text-green-600 hover:text-green-700 font-medium">
                Connexion CRM
              </Link>
            </p>
          </div>
        </div>

        {/* Info utilisateurs */}
        <div className="mt-6 bg-white rounded-lg shadow-sm p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-2">🏠 Qui peut accéder ?</h3>
          <div className="space-y-1 text-xs text-gray-600">
            <div className="flex items-center">
              <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
              <span>Tous les utilisateurs inscrits</span>
            </div>
            <div className="flex items-center">
              <span className="w-2 h-2 bg-orange-400 rounded-full mr-2"></span>
              <span>Création automatique de profil</span>
            </div>
            <div className="flex items-center">
              <span className="w-2 h-2 bg-blue-400 rounded-full mr-2"></span>
              <span>Agents, propriétaires, acheteurs, locataires</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-4 text-center">
          <p className="text-xs text-gray-500">
            Social Immo v2.0 - Le réseau de l'immobilier connecté
          </p>
        </div>
      </div>
    </div>
  );
};

// ✅ DÉSACTIVER LE LAYOUT POUR CETTE PAGE
SocialImmoLoginPage.getLayout = function getLayout(page: React.ReactElement) {
  return page;
};

export default SocialImmoLoginPage;