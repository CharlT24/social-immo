'use client'

import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { UserPlus, Users, Search, Check, X, MessageCircle } from 'lucide-react';

interface Friend {
  id: string;
  user_id: string;
  friend_id: string;
  status: 'pending' | 'accepted' | 'blocked';
  created_at: string;
  friend_name?: string;
  friend_profession?: string;
}

const FriendsComponent: React.FC = () => {
  const [friends, setFriends] = useState<Friend[]>([]);
  const [pendingRequests, setPendingRequests] = useState<Friend[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<'friends' | 'requests' | 'search'>('friends');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFriendsData();
  }, []);

  const loadFriendsData = async () => {
    // Demo data
    const demoFriends: Friend[] = [
      {
        id: '1',
        user_id: 'current-user',
        friend_id: 'friend-1',
        status: 'accepted',
        created_at: new Date().toISOString(),
        friend_name: 'Marie Dubois',
        friend_profession: 'Agent Immobilier'
      },
      {
        id: '2',
        user_id: 'current-user',
        friend_id: 'friend-2',
        status: 'accepted',
        created_at: new Date().toISOString(),
        friend_name: 'Pierre Martin',
        friend_profession: 'Notaire'
      }
    ];

    const demoPending: Friend[] = [
      {
        id: '3',
        user_id: 'friend-3',
        friend_id: 'current-user',
        status: 'pending',
        created_at: new Date().toISOString(),
        friend_name: 'Sophie Laurent',
        friend_profession: 'Promoteur Immobilier'
      }
    ];

    setFriends(demoFriends);
    setPendingRequests(demoPending);
    setLoading(false);
  };

  const acceptFriendRequest = async (requestId: string) => {
    try {
      const { error } = await supabase
        .from('friends')
        .update({ status: 'accepted' })
        .eq('id', requestId);

      if (error) throw error;

      // Move from pending to friends
      const request = pendingRequests.find(r => r.id === requestId);
      if (request) {
        setPendingRequests(pendingRequests.filter(r => r.id !== requestId));
        setFriends([...friends, { ...request, status: 'accepted' }]);
      }
    } catch (error) {
      console.error('Erreur lors de l\'acceptation:', error);
    }
  };

  const rejectFriendRequest = async (requestId: string) => {
    try {
      const { error } = await supabase
        .from('friends')
        .delete()
        .eq('id', requestId);

      if (error) throw error;

      setPendingRequests(pendingRequests.filter(r => r.id !== requestId));
    } catch (error) {
      console.error('Erreur lors du rejet:', error);
    }
  };

  const sendFriendRequest = async (friendId: string) => {
    try {
      const { error } = await supabase
        .from('friends')
        .insert([
          {
            user_id: 'current-user',
            friend_id: friendId,
            status: 'pending'
          }
        ]);

      if (error) throw error;
      
      alert('Demande d\'ami envoyée !');
    } catch (error) {
      console.error('Erreur lors de l\'envoi:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Onglets */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            <button
              onClick={() => setActiveTab('friends')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'friends'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Users className="h-4 w-4" />
                <span>Mes contacts ({friends.length})</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('requests')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'requests'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <div className="flex items-center space-x-2">
                <UserPlus className="h-4 w-4" />
                <span>Demandes ({pendingRequests.length})</span>
                {pendingRequests.length > 0 && (
                  <span className="bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                    {pendingRequests.length}
                  </span>
                )}
              </div>
            </button>
            <button
              onClick={() => setActiveTab('search')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'search'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Search className="h-4 w-4" />
                <span>Rechercher</span>
              </div>
            </button>
          </nav>
        </div>

        <div className="p-6">
          {/* Onglet Mes contacts */}
          {activeTab === 'friends' && (
            <div className="space-y-4">
              {friends.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Users className="mx-auto h-12 w-12 mb-4 text-gray-300" />
                  <p>Aucun contact pour le moment.</p>
                  <p className="text-sm">Commencez par rechercher des professionnels !</p>
                </div>
              ) : (
                friends.map((friend) => (
                  <div key={friend.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
                        {friend.friend_name?.charAt(0) || 'U'}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">{friend.friend_name}</h3>
                        <p className="text-sm text-gray-600">{friend.friend_profession}</p>
                        <p className="text-xs text-gray-400">
                          Contact depuis {new Date(friend.created_at).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <button className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 transition-colors">
                        <MessageCircle className="h-4 w-4" />
                      </button>
                      <button className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors">
                        Profil
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Onglet Demandes */}
          {activeTab === 'requests' && (
            <div className="space-y-4">
              {pendingRequests.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <UserPlus className="mx-auto h-12 w-12 mb-4 text-gray-300" />
                  <p>Aucune demande en attente.</p>
                </div>
              ) : (
                pendingRequests.map((request) => (
                  <div key={request.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-green-600 rounded-full flex items-center justify-center text-white font-semibold">
                        {request.friend_name?.charAt(0) || 'U'}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">{request.friend_name}</h3>
                        <p className="text-sm text-gray-600">{request.friend_profession}</p>
                        <p className="text-xs text-gray-400">
                          Demande envoyée le {new Date(request.created_at).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => acceptFriendRequest(request.id)}
                        className="bg-green-600 text-white p-2 rounded-lg hover:bg-green-700 transition-colors"
                      >
                        <Check className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => rejectFriendRequest(request.id)}
                        className="bg-red-600 text-white p-2 rounded-lg hover:bg-red-700 transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Onglet Recherche */}
          {activeTab === 'search' && (
            <div className="space-y-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Rechercher par nom, ville, spécialité..."
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Filtres */}
              <div className="flex flex-wrap gap-2">
                <button className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm">
                  Agents Immobiliers
                </button>
                <button className="bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm">
                  Notaires
                </button>
                <button className="bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm">
                  Promoteurs
                </button>
                <button className="bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm">
                  Investisseurs
                </button>
              </div>

              {/* Résultats de recherche */}
              <div className="space-y-4">
                {[
                  { id: 'search-1', name: 'Jean Dupont', profession: 'Agent Immobilier à Paris', mutual: 3 },
                  { id: 'search-2', name: 'Anne Moreau', profession: 'Notaire à Lyon', mutual: 1 },
                  { id: 'search-3', name: 'Paul Leroy', profession: 'Promoteur à Marseille', mutual: 0 }
                ].map((person) => (
                  <div key={person.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                        {person.name.charAt(0)}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">{person.name}</h3>
                        <p className="text-sm text-gray-600">{person.profession}</p>
                        {person.mutual > 0 && (
                          <p className="text-xs text-blue-600">
                            {person.mutual} contact{person.mutual > 1 ? 's' : ''} en commun
                          </p>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => sendFriendRequest(person.id)}
                      className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
                    >
                      <UserPlus className="h-4 w-4" />
                      <span>Ajouter</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FriendsComponent;
