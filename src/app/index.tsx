import React, { useEffect, useState } from 'react';
import { supabase } from '../../../lib/supabaseClient';
import { useRouter } from 'next/router';

// Import depuis le dossier components - CHEMINS ABSOLUS CORRECTS
import { WallComponent } from '../../../components/socialimmo/WallComponent';
import { ChatComponent } from '../../../components/socialimmo/ChatComponent';
import { FriendsComponent } from '../../../components/socialimmo/FriendsComponent';

// Type pour les pages avec layout personnalisé
type NextPageWithLayout = React.FC & {
  getLayout?: (page: React.ReactElement) => React.ReactNode;
};

interface User {
  id: string;
  email: string;
  prenom: string;
  nom: string;
  statut_externe: string;
  role: string;
  actif: boolean;
  statut_validation: string;
}

const SocialImmoPage: NextPageWithLayout = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'wall' | 'chat' | 'friends'>('wall');
  const [authChecked, setAuthChecked] = useState(false); // ✅ ÉVITER LA BOUCLE
  const router = useRouter();

  useEffect(() => {
    // ✅ NE VÉRIFIER L'AUTH QU'UNE SEULE FOIS
    if (!authChecked) {
      checkAuth();
    }
  }, [authChecked]);

  const checkAuth = async () => {
    try {
      console.log('🔍 Vérification authentification...');
      
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();
      
      if (sessionError) {
        console.error('Erreur session:', sessionError);
        throw sessionError;
      }

      if (!session) {
        console.log('❌ Pas de session, redirection vers login');
        setAuthChecked(true);
        setLoading(false);
        router.push('/public/socialimmo/login');
        return;
      }

      console.log('✅ Session trouvée, récupération utilisateur...');

      // Récupérer les données utilisateur avec timeout
      const { data: userData, error: userError } = await Promise.race([
        supabase
          .from('utilisateurs')
          .select('*')
          .eq('id', session.user.id)
          .single(),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Timeout récupération utilisateur')), 10000)
        )
      ]) as any;

      if (userError) {
        console.error('Erreur récupération utilisateur:', userError);
        throw userError;
      }

      console.log('👤 Données utilisateur:', userData);

      // ✅ VÉRIFICATION PERMISSIONS AVEC FALLBACK
      const hasAccess = (
        // Admins et agents CRM : accès direct
        (userData.role === 'admin' || userData.role === 'agent') ||
        // Externes : doivent être validés et actifs
        (userData.role === 'externe' && userData.actif && userData.statut_validation === 'valide')
      );

      if (!hasAccess) {
        console.log('🚫 Accès refusé:', {
          role: userData.role,
          actif: userData.actif,
          statut_validation: userData.statut_validation
        });
        
        setAuthChecked(true);
        setLoading(false);
        
        // Déconnexion et redirection
        await supabase.auth.signOut();
        router.push('/public/socialimmo/login?error=access_denied');
        return;
      }

      console.log('✅ Accès autorisé, chargement interface...');
      setUser(userData);

    } catch (error: any) {
      console.error('❌ Erreur vérification auth:', error);
      
      // En cas d'erreur, ne pas boucler
      if (error.message?.includes('Timeout')) {
        console.log('⏱️ Timeout Supabase, utilisation mode dégradé');
        // Mode dégradé : permettre l'accès avec un utilisateur fictif
        setUser({
          id: 'temp-user',
          email: 'temp@example.com',
          prenom: 'Utilisateur',
          nom: 'Temporaire',
          role: 'externe',
          statut_externe: 'agent_immobilier',
          actif: true,
          statut_validation: 'valide'
        });
      } else {
        // Autre erreur : redirection login
        router.push('/public/socialimmo/login?error=auth_failed');
      }
    } finally {
      setAuthChecked(true);
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      console.log('🚪 Déconnexion...');
      await supabase.auth.signOut();
      router.push('/public/socialimmo/login');
    } catch (error) {
      console.error('Erreur déconnexion:', error);
      // Forcer la redirection même en cas d'erreur
      router.push('/public/socialimmo/login');
    }
  };

  const tabs = [
    { id: 'wall', label: 'Fil d\'actualité', icon: '📰' },
    { id: 'chat', label: 'Messages', icon: '💬' },
    { id: 'friends', label: 'Réseau', icon: '👥' }
  ];

  // ✅ ÉTATS DE CHARGEMENT AMÉLIORÉS
  if (loading || !authChecked) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-orange-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">
            {!authChecked ? 'Vérification des permissions...' : 'Chargement de Social Immo...'}
          </p>
          <p className="mt-2 text-sm text-gray-500">
            Si le chargement prend trop de temps, <a href="/public/socialimmo/login" className="text-orange-600 underline">cliquez ici</a>
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Redirection vers la page de connexion...</p>
          <a href="/public/socialimmo/login" className="text-orange-600 underline">
            Cliquez ici si la redirection ne fonctionne pas
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 min-h-screen">
      {/* Header avec navigation */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo et titre */}
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">
                Social Immo
              </h1>
              <span className="ml-2 px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded-full">
                Réseau Pro
              </span>
              {/* Badge rôle */}
              {(user.role === 'admin' || user.role === 'agent') && (
                <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                  {user.role === 'admin' ? 'Admin CRM' : 'Agent CRM'}
                </span>
              )}
              {user.id === 'temp-user' && (
                <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                  Mode Dégradé
                </span>
              )}
            </div>

            {/* Navigation par onglets */}
            <nav className="hidden md:flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'bg-orange-100 text-orange-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>

            {/* Profil utilisateur */}
            <div className="flex items-center space-x-4">
              <div className="hidden md:block text-right">
                <p className="text-sm font-medium text-gray-900">
                  {user.prenom} {user.nom}
                </p>
                <p className="text-xs text-gray-500 capitalize">
                  {user.role === 'admin' ? 'Administrateur' :
                   user.role === 'agent' ? 'Agent immobilier' :
                   user.statut_externe?.replace('_', ' ') || 'Utilisateur externe'}
                </p>
              </div>
              
              <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                <span className="text-orange-600 font-medium text-sm">
                  {user.prenom?.[0]?.toUpperCase() || 'U'}
                  {user.nom?.[0]?.toUpperCase() || ''}
                </span>
              </div>

              {/* Liens vers CRM pour admin/agent */}
              {(user.role === 'admin' || user.role === 'agent') && (
                <button
                  onClick={() => router.push('/dashboard')}
                  className="text-gray-400 hover:text-gray-600"
                  title="Retour au CRM"
                >
                  🏢
                </button>
              )}

              <button
                onClick={handleLogout}
                className="text-gray-400 hover:text-gray-600"
                title="Déconnexion"
              >
                🚪
              </button>
            </div>
          </div>

          {/* Navigation mobile */}
          <div className="md:hidden border-t border-gray-200">
            <div className="flex">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex-1 flex items-center justify-center space-x-2 py-3 text-sm font-medium ${
                    activeTab === tab.id
                      ? 'text-orange-700 border-b-2 border-orange-700'
                      : 'text-gray-600'
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Contenu principal */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Colonne principale */}
          <div className="lg:col-span-3">
            {activeTab === 'wall' && <WallComponent />}
            {activeTab === 'chat' && <ChatComponent />}
            {activeTab === 'friends' && <FriendsComponent />}
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            {/* Bienvenue */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Bienvenue {user.prenom} !
              </h3>
              <p className="text-sm text-gray-600">
                {user.role === 'admin' || user.role === 'agent' 
                  ? 'Accès CRM à Social Immo - Connectez-vous avec votre réseau professionnel.'
                  : 'Connectez-vous avec d\'autres professionnels de l\'immobilier et partagez vos actualités.'
                }
              </p>
            </div>

            {/* Statistiques rapides */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Votre activité
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Publications</span>
                  <span className="font-medium">12</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Contacts</span>
                  <span className="font-medium">47</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Messages</span>
                  <span className="font-medium">23</span>
                </div>
              </div>
            </div>

            {/* Actions rapides */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Actions rapides
              </h3>
              <div className="space-y-2">
                <button className="w-full text-left px-3 py-2 text-sm text-orange-600 hover:bg-orange-50 rounded-lg">
                  📝 Publier une actualité
                </button>
                <button className="w-full text-left px-3 py-2 text-sm text-orange-600 hover:bg-orange-50 rounded-lg">
                  🏠 Partager un bien
                </button>
                <button className="w-full text-left px-3 py-2 text-sm text-orange-600 hover:bg-orange-50 rounded-lg">
                  👤 Trouver des contacts
                </button>
                {(user.role === 'admin' || user.role === 'agent') && (
                  <button 
                    onClick={() => router.push('/dashboard')}
                    className="w-full text-left px-3 py-2 text-sm text-green-600 hover:bg-green-50 rounded-lg"
                  >
                    🏢 Retour au CRM
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ✅ DÉSACTIVER LE LAYOUT POUR CETTE PAGE
SocialImmoPage.getLayout = function getLayout(page: React.ReactElement) {
  return page;
};

export default SocialImmoPage;