import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { Search, UserPlus, MessageCircle, Users, Building2, Home, TrendingUp, UserCheck, Clock, Check, X, Bell } from 'lucide-react';

interface Contact {
  id: string;
  nom: string;
  prenom: string;
  email: string;
  statut_externe: string;
  role: string;
  actif: boolean;
}

interface ContactRequest {
  id: string;
  expediteur_id: string;
  destinataire_id: string;
  expediteur_nom?: string;
  expediteur_prenom?: string;
  destinataire_nom?: string;
  destinataire_prenom?: string;
  statut: 'en_attente' | 'accepte' | 'refuse';
  message?: string;
  created_at: string;
}

interface FriendsComponentProps {
  className?: string;
  onStartConversation?: (contact: Contact) => void;
}

export const FriendsComponent: React.FC<FriendsComponentProps> = ({ 
  className = "",
  onStartConversation
}) => {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [friends, setFriends] = useState<Contact[]>([]);
  const [contactRequests, setContactRequests] = useState<ContactRequest[]>([]);
  const [sentRequests, setSentRequests] = useState<ContactRequest[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'friends' | 'requests' | 'discover'>('friends');
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [sendingRequest, setSendingRequest] = useState<string | null>(null);
  const [processingRequest, setProcessingRequest] = useState<string | null>(null);

  useEffect(() => {
    initializeContacts();
    
    // Auto-refresh toutes les 30 secondes pour les demandes
    const interval = setInterval(() => {
      if (currentUserId) {
        fetchContactRequests();
        fetchFriends();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const initializeContacts = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.user) return;

      setCurrentUserId(session.user.id);
      await Promise.all([
        fetchContacts(),
        fetchContactRequests(),
        fetchFriends()
      ]);
    } catch (error) {
      console.error('Erreur initialisation contacts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchContacts = async () => {
    try {
      const { data, error } = await supabase
        .from('utilisateurs')
        .select('id, nom, prenom, email, statut_externe, role, actif')
        .eq('actif', true)
        .order('nom', { ascending: true });

      if (error) throw error;

      const filteredContacts = (data || []).filter(contact => {
        if (contact.id === currentUserId) return false;
        return contact.role === 'agent' || contact.role === 'admin' || 
               (contact.role === 'externe' && contact.actif);
      });

      setContacts(filteredContacts);
    } catch (error) {
      console.error('Erreur chargement contacts:', error);
    }
  };

  const fetchContactRequests = async () => {
    if (!currentUserId) return;

    try {
      // Demandes reçues
      const { data: receivedRequests, error: receivedError } = await supabase
        .from('demandes_contact')
        .select(`
          id, expediteur_id, destinataire_id, statut, message, created_at,
          expediteur_nom, expediteur_prenom
        `)
        .eq('destinataire_id', currentUserId)
        .eq('statut', 'en_attente')
        .order('created_at', { ascending: false });

      if (receivedError) {
        console.warn('Table demandes_contact non disponible, simulation...');
        setContactRequests([]);
      } else {
        setContactRequests(receivedRequests || []);
      }

      // Demandes envoyées
      const { data: sentRequestsData, error: sentError } = await supabase
        .from('demandes_contact')
        .select(`
          id, expediteur_id, destinataire_id, statut, message, created_at,
          destinataire_nom, destinataire_prenom
        `)
        .eq('expediteur_id', currentUserId)
        .order('created_at', { ascending: false });

      if (!sentError) {
        setSentRequests(sentRequestsData || []);
      }

    } catch (error) {
      console.error('Erreur chargement demandes:', error);
    }
  };

  const fetchFriends = async () => {
    if (!currentUserId) return;

    try {
      // Récupérer les relations d'amitié
      const { data: relations, error } = await supabase
        .from('relations_amis')
        .select('user1_id, user2_id')
        .or(`user1_id.eq.${currentUserId},user2_id.eq.${currentUserId}`);

      if (error) {
        console.warn('Table relations_amis non disponible');
        return;
      }

      const friendIds = relations?.map(relation => 
        relation.user1_id === currentUserId ? relation.user2_id : relation.user1_id
      ) || [];

      if (friendIds.length === 0) {
        setFriends([]);
        return;
      }

      // Récupérer les données des amis
      const { data: friendsData, error: friendsError } = await supabase
        .from('utilisateurs')
        .select('id, nom, prenom, email, statut_externe, role, actif')
        .in('id', friendIds)
        .eq('actif', true);

      if (!friendsError) {
        setFriends(friendsData || []);
      }

    } catch (error) {
      console.error('Erreur chargement amis:', error);
    }
  };

  const handleSendContactRequest = async (contact: Contact) => {
    if (!currentUserId) {
      alert('Vous devez être connecté');
      return;
    }

    setSendingRequest(contact.id);

    try {
      // Récupérer mes infos pour les noms
      const { data: userData } = await supabase
        .from('utilisateurs')
        .select('nom, prenom')
        .eq('id', currentUserId)
        .single();

      const requestData = {
        expediteur_id: currentUserId,
        destinataire_id: contact.id,
        statut: 'en_attente',
        message: `Demande de connexion sur Social Immo`,
        expediteur_nom: userData?.nom || '',
        expediteur_prenom: userData?.prenom || '',
        destinataire_nom: contact.nom,
        destinataire_prenom: contact.prenom
      };

      const { error } = await supabase
        .from('demandes_contact')
        .insert([requestData]);

      if (error) {
        if (error.code === '42P01') {
          alert(`📨 Demande envoyée à ${contact.prenom} ${contact.nom}\n\n(Mode simulation - Exécutez le script SQL pour activer)`);
          return;
        }
        throw error;
      }

      // Créer une notification pour le destinataire
      await supabase.from('notifications').insert([{
        user_id: contact.id,
        type: 'demande_ami',
        titre: 'Nouvelle demande de connexion',
        contenu: `${userData?.prenom} ${userData?.nom} souhaite se connecter avec vous`,
        related_id: null
      }]);

      alert(`✅ Demande de connexion envoyée à ${contact.prenom} ${contact.nom}`);
      await fetchContactRequests();

    } catch (error: any) {
      console.error('Erreur envoi demande:', error);
      alert(`❌ Erreur : ${error.message}`);
    } finally {
      setSendingRequest(null);
    }
  };

  const handleAcceptRequest = async (request: ContactRequest) => {
    setProcessingRequest(request.id);

    try {
      // Mettre à jour le statut de la demande
      const { error: updateError } = await supabase
        .from('demandes_contact')
        .update({ statut: 'accepte' })
        .eq('id', request.id);

      if (updateError) throw updateError;

      // Créer la relation d'amitié
      const { error: relationError } = await supabase
        .rpc('creer_relation_amitie', {
          user1: request.expediteur_id,
          user2: currentUserId
        });

      if (relationError) {
        console.warn('Fonction creer_relation_amitie non trouvée, insertion manuelle...');
        
        const user1 = request.expediteur_id < currentUserId! ? request.expediteur_id : currentUserId!;
        const user2 = request.expediteur_id < currentUserId! ? currentUserId! : request.expediteur_id;
        
        await supabase
          .from('relations_amis')
          .insert([{ user1_id: user1, user2_id: user2 }]);
      }

      // Notification pour l'expéditeur
      await supabase.from('notifications').insert([{
        user_id: request.expediteur_id,
        type: 'ami_accepte',
        titre: 'Demande acceptée',
        contenu: `${request.destinataire_prenom} ${request.destinataire_nom} a accepté votre demande de connexion`,
        related_id: parseInt(request.id)
      }]);

      alert(`✅ Vous êtes maintenant connecté avec ${request.expediteur_prenom} ${request.expediteur_nom}`);
      
      await Promise.all([
        fetchContactRequests(),
        fetchFriends()
      ]);

    } catch (error: any) {
      console.error('Erreur acceptation demande:', error);
      alert(`❌ Erreur : ${error.message}`);
    } finally {
      setProcessingRequest(null);
    }
  };

  const handleRejectRequest = async (request: ContactRequest) => {
    setProcessingRequest(request.id);

    try {
      const { error } = await supabase
        .from('demandes_contact')
        .update({ statut: 'refuse' })
        .eq('id', request.id);

      if (error) throw error;

      alert(`❌ Demande de ${request.expediteur_prenom} ${request.expediteur_nom} refusée`);
      await fetchContactRequests();

    } catch (error: any) {
      console.error('Erreur refus demande:', error);
      alert(`❌ Erreur : ${error.message}`);
    } finally {
      setProcessingRequest(null);
    }
  };

  const handleStartConversation = (contact: Contact) => {
    if (onStartConversation) {
      onStartConversation(contact);
    } else {
      console.log('Démarrer conversation avec:', contact);
      alert(`💬 Conversation avec ${contact.prenom} ${contact.nom} - Fonctionnalité en développement`);
    }
  };

  // Filtrer selon l'onglet actif
  const getFilteredData = () => {
    const search = searchTerm.toLowerCase();
    
    switch (activeTab) {
      case 'friends':
        return friends.filter(friend => 
          friend.nom.toLowerCase().includes(search) ||
          friend.prenom.toLowerCase().includes(search)
        );
      case 'requests':
        return contactRequests; // Pas de filtre recherche sur les demandes
      case 'discover':
        return contacts.filter(contact => {
          const matchesSearch = 
            contact.nom.toLowerCase().includes(search) ||
            contact.prenom.toLowerCase().includes(search);
          
          if (!matchesSearch) return false;
          
          // Exclure ceux qui sont déjà amis
          const isAlreadyFriend = friends.some(friend => friend.id === contact.id);
          if (isAlreadyFriend) return false;
          
          // Exclure ceux à qui on a déjà envoyé une demande en attente
          const hasPendingRequest = sentRequests.some(req => 
            req.destinataire_id === contact.id && req.statut === 'en_attente'
          );
          if (hasPendingRequest) return false;
          
          return true;
        });
      default:
        return [];
    }
  };

  const getContactTypeInfo = (contact: Contact) => {
    if (contact.role === 'admin') {
      return { 
        label: 'Admin', 
        color: 'bg-purple-100 text-purple-800 border-purple-200',
        icon: <Building2 className="w-4 h-4" />
      };
    }
    if (contact.role === 'agent') {
      return { 
        label: 'Agent', 
        color: 'bg-green-100 text-green-800 border-green-200',
        icon: <Building2 className="w-4 h-4" />
      };
    }
    
    switch (contact.statut_externe) {
      case 'agent_immobilier':
        return { 
          label: 'Pro Immo', 
          color: 'bg-green-100 text-green-800 border-green-200',
          icon: <Building2 className="w-4 h-4" />
        };
      case 'proprietaire':
        return { 
          label: 'Propriétaire', 
          color: 'bg-blue-100 text-blue-800 border-blue-200',
          icon: <Home className="w-4 h-4" />
        };
      case 'acheteur':
        return { 
          label: 'Acheteur', 
          color: 'bg-orange-100 text-orange-800 border-orange-200',
          icon: <Home className="w-4 h-4" />
        };
      case 'locataire':
        return { 
          label: 'Locataire', 
          color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
          icon: <Home className="w-4 h-4" />
        };
      case 'investisseur':
        return { 
          label: 'Investisseur', 
          color: 'bg-indigo-100 text-indigo-800 border-indigo-200',
          icon: <TrendingUp className="w-4 h-4" />
        };
      default:
        return { 
          label: 'Particulier', 
          color: 'bg-gray-100 text-gray-800 border-gray-200',
          icon: <Users className="w-4 h-4" />
        };
    }
  };

  if (loading) {
    return (
      <div className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    );
  }

  const filteredData = getFilteredData();

  return (
    <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="p-6 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Réseau professionnel
        </h2>

        {/* Onglets */}
        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg mb-4">
          <button
            onClick={() => setActiveTab('friends')}
            className={`flex-1 flex items-center justify-center space-x-2 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'friends'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Amis ({friends.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('requests')}
            className={`flex-1 flex items-center justify-center space-x-2 py-2 px-3 rounded-md text-sm font-medium transition-colors relative ${
              activeTab === 'requests'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Bell className="w-4 h-4" />
            <span>Demandes</span>
            {contactRequests.length > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {contactRequests.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('discover')}
            className={`flex-1 flex items-center justify-center space-x-2 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'discover'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Search className="w-4 h-4" />
            <span>Découvrir</span>
          </button>
        </div>

        {/* Recherche (sauf pour les demandes) */}
        {activeTab !== 'requests' && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Rechercher par nom..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            />
          </div>
        )}
      </div>

      {/* Contenu selon l'onglet */}
      <div className="max-h-96 overflow-y-auto">
        {/* Onglet Amis */}
        {activeTab === 'friends' && (
          <div>
            {filteredData.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Users className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-lg mb-2">
                  {searchTerm ? 'Aucun ami trouvé' : 'Aucun ami connecté'}
                </p>
                <p className="text-sm text-gray-400">
                  Explorez l'onglet "Découvrir" pour trouver des contacts
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {filteredData.map((friend) => {
                  const typeInfo = getContactTypeInfo(friend);
                  return (
                    <div key={friend.id} className="p-4 hover:bg-gray-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center shadow-sm">
                            <span className="text-white font-semibold text-sm">
                              {(friend.prenom?.[0] || 'U').toUpperCase()}
                              {(friend.nom?.[0] || '').toUpperCase()}
                            </span>
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center space-x-3">
                              <h3 className="font-semibold text-gray-900">
                                {friend.prenom} {friend.nom}
                              </h3>
                              <div className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium border ${typeInfo.color}`}>
                                {typeInfo.icon}
                                <span>{typeInfo.label}</span>
                              </div>
                            </div>
                            <p className="text-sm text-gray-500 mt-1">
                              Connecté • Social Immo
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleStartConversation(friend)}
                            className="inline-flex items-center space-x-1 px-3 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                            title="Envoyer un message"
                          >
                            <MessageCircle className="w-4 h-4" />
                            <span>Message</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Onglet Demandes */}
        {activeTab === 'requests' && (
          <div>
            {contactRequests.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Bell className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-lg mb-2">Aucune demande en attente</p>
                <p className="text-sm text-gray-400">
                  Les nouvelles demandes de connexion apparaîtront ici
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {contactRequests.map((request) => {
                  const isProcessing = processingRequest === request.id;
                  
                  return (
                    <div key={request.id} className="p-4 bg-blue-50 border-l-4 border-blue-400">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center shadow-sm">
                            <span className="text-white font-semibold text-sm">
                              {(request.expediteur_prenom?.[0] || 'U').toUpperCase()}
                              {(request.expediteur_nom?.[0] || '').toUpperCase()}
                            </span>
                          </div>
                          <div className="flex-1">
                            <h3 className="font-semibold text-gray-900">
                              {request.expediteur_prenom} {request.expediteur_nom}
                            </h3>
                            <p className="text-sm text-gray-600 mt-1">
                              Souhaite se connecter avec vous
                            </p>
                            {request.message && (
                              <p className="text-sm text-gray-500 mt-1 italic">
                                "{request.message}"
                              </p>
                            )}
                            <p className="text-xs text-gray-400 mt-2">
                              {new Date(request.created_at).toLocaleDateString('fr-FR', {
                                day: 'numeric',
                                month: 'long',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleAcceptRequest(request)}
                            disabled={isProcessing}
                            className="inline-flex items-center space-x-1 px-3 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                          >
                            {isProcessing ? (
                              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            ) : (
                              <Check className="w-4 h-4" />
                            )}
                            <span>Accepter</span>
                          </button>
                          
                          <button
                            onClick={() => handleRejectRequest(request)}
                            disabled={isProcessing}
                            className="inline-flex items-center space-x-1 px-3 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                          >
                            <X className="w-4 h-4" />
                            <span>Refuser</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            
            {/* Demandes envoyées */}
            {sentRequests.length > 0 && (
              <div className="border-t border-gray-200 p-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Demandes envoyées</h4>
                <div className="space-y-2">
                  {sentRequests.filter(req => req.statut === 'en_attente').map((request) => (
                    <div key={request.id} className="flex items-center justify-between p-2 bg-yellow-50 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <Clock className="w-4 h-4 text-yellow-600" />
                        <span className="text-sm text-gray-700">
                          {request.destinataire_prenom} {request.destinataire_nom}
                        </span>
                      </div>
                      <span className="text-xs text-yellow-600 font-medium">En attente</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Onglet Découvrir */}
        {activeTab === 'discover' && (
          <div>
            {filteredData.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Search className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-lg mb-2">
                  {searchTerm 
                    ? 'Aucun contact trouvé'
                    : 'Aucun nouveau contact'
                  }
                </p>
                <p className="text-sm text-gray-400">
                  {searchTerm 
                    ? 'Essayez une autre recherche'
                    : 'Vous êtes connecté avec tous les membres disponibles'
                  }
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {filteredData.map((contact) => {
                  const typeInfo = getContactTypeInfo(contact);
                  const isRequesting = sendingRequest === contact.id;
                  
                  return (
                    <div key={contact.id} className="p-4 hover:bg-gray-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-orange-400 to-orange-600 rounded-full flex items-center justify-center shadow-sm">
                            <span className="text-white font-semibold text-sm">
                              {(contact.prenom?.[0] || 'U').toUpperCase()}
                              {(contact.nom?.[0] || '').toUpperCase()}
                            </span>
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center space-x-3">
                              <h3 className="font-semibold text-gray-900">
                                {contact.prenom} {contact.nom}
                              </h3>
                              <div className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium border ${typeInfo.color}`}>
                                {typeInfo.icon}
                                <span>{typeInfo.label}</span>
                              </div>
                            </div>
                            <p className="text-sm text-gray-500 mt-1">
                              Membre Social Immo
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleSendContactRequest(contact)}
                            disabled={isRequesting}
                            className="inline-flex items-center space-x-1 px-3 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            title="Envoyer une demande de connexion"
                          >
                            {isRequesting ? (
                              <>
                                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                <span>Envoi...</span>
                              </>
                            ) : (
                              <>
                                <UserPlus className="w-4 h-4" />
                                <span>Connecter</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer avec stats */}
      <div className="p-4 border-t border-gray-100 bg-gray-50">
        <div className="flex justify-between items-center text-sm text-gray-600">
          <div className="flex items-center space-x-4">
            <span className="flex items-center space-x-1">
              <Users className="w-3 h-3" />
              <span>{friends.length} amis</span>
            </span>
            {contactRequests.length > 0 && (
              <span className="flex items-center space-x-1">
                <Bell className="w-3 h-3" />
                <span>{contactRequests.length} demande{contactRequests.length > 1 ? 's' : ''}</span>
              </span>
            )}
          </div>
          <span>
            {filteredData.length} affiché{filteredData.length > 1 ? 's' : ''}
          </span>
        </div>
      </div>
    </div>
  );
};