import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { Search, UserPlus, MessageCircle, Users } from 'lucide-react';

interface Contact {
  id: string;
  nom: string;
  prenom: string;
  email: string;
  statut_externe: string;
  role: string;
}

interface FriendsComponentProps {
  className?: string;
}

export const FriendsComponent: React.FC<FriendsComponentProps> = ({ 
  className = ""
}) => {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'friends' | 'discover'>('friends');

  useEffect(() => {
    fetchContacts();
  }, []);

  const fetchContacts = async () => {
    try {
      const { data, error } = await supabase
        .from('utilisateurs')
        .select('id, nom, prenom, email, statut_externe, role')
        .eq('actif', true)
        .order('nom', { ascending: true });

      if (!error) {
        setContacts(data || []);
      }
    } catch (error) {
      console.error('Erreur chargement contacts:', error);
    } finally {
      setLoading(false);
    }
  };

  const getContactTypeInfo = (contact: Contact) => {
    if (contact.role === 'admin') {
      return { 
        label: 'Admin', 
        color: 'bg-purple-100 text-purple-800 border-purple-200'
      };
    }
    if (contact.role === 'agent') {
      return { 
        label: 'Agent', 
        color: 'bg-green-100 text-green-800 border-green-200'
      };
    }
    
    switch (contact.statut_externe) {
      case 'agent_immobilier':
        return { 
          label: 'Pro Immo', 
          color: 'bg-green-100 text-green-800 border-green-200'
        };
      case 'proprietaire':
        return { 
          label: 'Propriétaire', 
          color: 'bg-blue-100 text-blue-800 border-blue-200'
        };
      case 'acheteur':
        return { 
          label: 'Acheteur', 
          color: 'bg-orange-100 text-orange-800 border-orange-200'
        };
      default:
        return { 
          label: 'Particulier', 
          color: 'bg-gray-100 text-gray-800 border-gray-200'
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

  const filteredContacts = contacts.filter(contact => 
    contact.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
    contact.prenom.toLowerCase().includes(searchTerm.toLowerCase())
  );

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
            <span>Amis (0)</span>
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

        {/* Recherche */}
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
      </div>

      {/* Contenu */}
      <div className="max-h-96 overflow-y-auto">
        {activeTab === 'friends' ? (
          <div className="p-8 text-center text-gray-500">
            <Users className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p className="text-lg mb-2">Aucun ami connecté</p>
            <p className="text-sm text-gray-400">
              Explorez l'onglet "Découvrir" pour trouver des contacts
            </p>
          </div>
        ) : (
          <div>
            {filteredContacts.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Search className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-lg mb-2">Aucun contact trouvé</p>
                <p className="text-sm text-gray-400">
                  Essayez une autre recherche
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {filteredContacts.map((contact) => {
                  const typeInfo = getContactTypeInfo(contact);
                  
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
                              <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${typeInfo.color}`}>
                                <span>{typeInfo.label}</span>
                              </div>
                            </div>
                            <p className="text-sm text-gray-500 mt-1">
                              Membre Social Immo
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2">
                          <button className="inline-flex items-center space-x-1 px-3 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors">
                            <UserPlus className="w-4 h-4" />
                            <span>Connecter</span>
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
    </div>
  );
};
