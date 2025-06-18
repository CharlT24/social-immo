import React, { useState, useEffect, useRef } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { MessageCircle, Send, User, Clock, CheckCircle, Circle, Search, Users, ArrowLeft } from 'lucide-react';

interface Message {
  id: number;
  conversation_id: number;
  expediteur_id: string;
  contenu: string;
  lu: boolean;
  created_at: string;
}

interface Conversation {
  id: number;
  participant1_id: string;
  participant2_id: string;
  created_at: string;
  updated_at: string;
  // Données enrichies
  other_user?: {
    id: string;
    nom: string;
    prenom: string;
    role: string;
    statut_externe: string;
  };
  last_message?: Message;
  unread_count?: number;
}

interface ChatComponentProps {
  className?: string;
  initialContactId?: string; // Pour ouvrir directement une conversation
}

export const ChatComponent: React.FC<ChatComponentProps> = ({ 
  className = "",
  initialContactId 
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [friends, setFriends] = useState<any[]>([]);
  const [showCreateChat, setShowCreateChat] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    initializeChat();
    
    // Auto-refresh des conversations toutes les 10 secondes
    const interval = setInterval(() => {
      if (currentUserId) {
        fetchConversations(true);
        if (selectedConversation) {
          fetchMessages(selectedConversation, true);
        }
      }
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (initialContactId && currentUserId && friends.length > 0) {
      handleStartConversationWithContact(initialContactId);
    }
  }, [initialContactId, currentUserId, friends]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const initializeChat = async () => {
    try {
      setError(null);
      
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.user) {
        setError('Vous devez être connecté pour accéder aux messages');
        return;
      }

      setCurrentUserId(session.user.id);
      
      await Promise.all([
        fetchFriends(),
        fetchConversations()
      ]);
    } catch (error: any) {
      console.error('Erreur initialisation chat:', error);
      setError(`Erreur lors du chargement: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchFriends = async () => {
    if (!currentUserId) return;

    try {
      // Récupérer les amis depuis relations_amis
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
        .select('id, nom, prenom, role, statut_externe')
        .in('id', friendIds)
        .eq('actif', true);

      if (!friendsError) {
        setFriends(friendsData || []);
      }
    } catch (error) {
      console.error('Erreur chargement amis:', error);
    }
  };

  const fetchConversations = async (silent = false) => {
    if (!currentUserId) return;

    try {
      // Récupérer les conversations où l'utilisateur participe
      const { data: convs, error } = await supabase
        .from('conversations')
        .select('*')
        .or(`participant1_id.eq.${currentUserId},participant2_id.eq.${currentUserId}`)
        .order('updated_at', { ascending: false });

      if (error) {
        if (!silent) {
          console.warn('Table conversations non disponible:', error);
          setError('Les conversations ne sont pas encore disponibles. Exécutez le script SQL.');
        }
        return;
      }

      // Enrichir avec les données des autres participants
      const enrichedConvs = await Promise.all(
        (convs || []).map(async (conv) => {
          const otherUserId = conv.participant1_id === currentUserId ? conv.participant2_id : conv.participant1_id;
          
          // Récupérer les données de l'autre utilisateur
          const { data: userData } = await supabase
            .from('utilisateurs')
            .select('id, nom, prenom, role, statut_externe')
            .eq('id', otherUserId)
            .single();

          // Récupérer le dernier message
          const { data: lastMessage } = await supabase
            .from('messages_prives')
            .select('*')
            .eq('conversation_id', conv.id)
            .order('created_at', { ascending: false })
            .limit(1)
            .single();

          // Compter les messages non lus
          const { count: unreadCount } = await supabase
            .from('messages_prives')
            .select('*', { count: 'exact', head: true })
            .eq('conversation_id', conv.id)
            .eq('lu', false)
            .neq('expediteur_id', currentUserId);

          return {
            ...conv,
            other_user: userData,
            last_message: lastMessage,
            unread_count: unreadCount || 0
          };
        })
      );

      setConversations(enrichedConvs);
    } catch (error: any) {
      if (!silent) {
        console.error('Erreur chargement conversations:', error);
        setError(`Erreur chargement conversations: ${error.message}`);
      }
    }
  };

  const fetchMessages = async (conversationId: number, silent = false) => {
    if (!silent) setLoadingMessages(true);

    try {
      const { data, error } = await supabase
        .from('messages_prives')
        .select('*')
        .eq('conversation_id', conversationId)
        .order('created_at', { ascending: true });

      if (error) throw error;

      setMessages(data || []);

      // Marquer les messages comme lus
      await supabase
        .from('messages_prives')
        .update({ lu: true })
        .eq('conversation_id', conversationId)
        .neq('expediteur_id', currentUserId);

    } catch (error: any) {
      console.error('Erreur chargement messages:', error);
      if (!silent) {
        setError(`Erreur chargement messages: ${error.message}`);
      }
    } finally {
      if (!silent) setLoadingMessages(false);
    }
  };

  const handleStartConversationWithContact = async (contactId: string) => {
    if (!currentUserId) return;

    try {
      // Vérifier si une conversation existe déjà
      const existingConv = conversations.find(conv => 
        conv.other_user?.id === contactId
      );

      if (existingConv) {
        setSelectedConversation(existingConv.id);
        await fetchMessages(existingConv.id);
        return;
      }

      // Créer une nouvelle conversation
      const { data: newConv, error } = await supabase
        .rpc('get_ou_creer_conversation', {
          user1: currentUserId,
          user2: contactId
        });

      if (error) {
        // Fallback manuel si la fonction n'existe pas
        const user1 = currentUserId < contactId ? currentUserId : contactId;
        const user2 = currentUserId < contactId ? contactId : currentUserId;
        
        const { data: convData, error: createError } = await supabase
          .from('conversations')
          .insert([{ participant1_id: user1, participant2_id: user2 }])
          .select()
          .single();

        if (createError) throw createError;
        
        setSelectedConversation(convData.id);
        await fetchConversations();
        await fetchMessages(convData.id);
      } else {
        setSelectedConversation(newConv);
        await fetchConversations();
        await fetchMessages(newConv);
      }

      setShowCreateChat(false);
    } catch (error: any) {
      console.error('Erreur création conversation:', error);
      alert(`Erreur lors de la création de la conversation: ${error.message}`);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation || !currentUserId || sending) return;

    setSending(true);

    try {
      const { data, error } = await supabase
        .from('messages_prives')
        .insert([{
          conversation_id: selectedConversation,
          expediteur_id: currentUserId,
          contenu: newMessage.trim(),
          lu: false
        }])
        .select()
        .single();

      if (error) throw error;

      // Ajouter le message localement
      setMessages(prev => [...prev, data]);
      
      // Mettre à jour la conversation
      await supabase
        .from('conversations')
        .update({ updated_at: new Date().toISOString() })
        .eq('id', selectedConversation);

      setNewMessage('');
      messageInputRef.current?.focus();
      
      // Actualiser la liste des conversations
      await fetchConversations(true);

    } catch (error: any) {
      console.error('Erreur envoi message:', error);
      alert(`Erreur lors de l'envoi: ${error.message}`);
    } finally {
      setSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'À l\'instant';
    if (diffMins < 60) return `${diffMins}min`;
    if (diffHours < 24) return `${diffHours}h`;
    if (diffDays < 7) return `${diffDays}j`;
    
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short'
    });
  };

  const getContactTypeInfo = (contact: any) => {
    if (contact.role === 'admin') return { label: 'Admin', color: 'bg-purple-100 text-purple-800' };
    if (contact.role === 'agent') return { label: 'Agent', color: 'bg-green-100 text-green-800' };
    
    switch (contact.statut_externe) {
      case 'agent_immobilier': return { label: 'Pro Immo', color: 'bg-green-100 text-green-800' };
      case 'proprietaire': return { label: 'Propriétaire', color: 'bg-blue-100 text-blue-800' };
      case 'acheteur': return { label: 'Acheteur', color: 'bg-orange-100 text-orange-800' };
      case 'locataire': return { label: 'Locataire', color: 'bg-yellow-100 text-yellow-800' };
      case 'investisseur': return { label: 'Investisseur', color: 'bg-indigo-100 text-indigo-800' };
      default: return { label: 'Particulier', color: 'bg-gray-100 text-gray-800' };
    }
  };

  const filteredConversations = conversations.filter(conv => {
    if (!searchTerm) return true;
    const otherUser = conv.other_user;
    if (!otherUser) return false;
    
    return (
      otherUser.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
      otherUser.prenom.toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

  const filteredFriends = friends.filter(friend => {
    if (!searchTerm) return true;
    return (
      friend.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
      friend.prenom.toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

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

  if (error) {
    return (
      <div className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
        <div className="text-center">
          <MessageCircle className="w-16 h-16 mx-auto mb-4 text-red-400" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Erreur de chargement
          </h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => {
              setError(null);
              initializeChat();
            }}
            className="bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700"
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Messages privés
          </h2>
          <button
            onClick={() => setShowCreateChat(!showCreateChat)}
            className="bg-orange-600 text-white px-3 py-2 rounded-lg hover:bg-orange-700 text-sm"
          >
            + Nouveau chat
          </button>
        </div>
        
        {/* Recherche */}
        <div className="mt-3 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder="Rechercher une conversation..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm"
          />
        </div>
      </div>

      <div className="flex h-96">
        {/* Liste des conversations */}
        <div className="w-1/3 border-r border-gray-100 flex flex-col">
          {/* Nouveau chat */}
          {showCreateChat && (
            <div className="p-4 bg-blue-50 border-b border-blue-200">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-900">Nouveau chat</h4>
                <button
                  onClick={() => setShowCreateChat(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </div>
              
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {filteredFriends.length === 0 ? (
                  <p className="text-sm text-gray-500">Aucun ami trouvé</p>
                ) : (
                  filteredFriends.map((friend) => {
                    const typeInfo = getContactTypeInfo(friend);
                    return (
                      <div
                        key={friend.id}
                        onClick={() => handleStartConversationWithContact(friend.id)}
                        className="flex items-center space-x-2 p-2 hover:bg-white rounded-lg cursor-pointer"
                      >
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                          <span className="text-blue-600 font-medium text-xs">
                            {friend.prenom[0]}{friend.nom[0]}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {friend.prenom} {friend.nom}
                          </p>
                          <span className={`inline-block px-2 py-0.5 rounded-full text-xs ${typeInfo.color}`}>
                            {typeInfo.label}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* Liste conversations */}
          <div className="flex-1 overflow-y-auto">
            {filteredConversations.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                <MessageCircle className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p className="text-sm">
                  {searchTerm ? 'Aucune conversation trouvée' : 'Aucune conversation'}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Commencez par envoyer une demande d'ami
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {filteredConversations.map((conv) => {
                  const otherUser = conv.other_user;
                  if (!otherUser) return null;

                  const isSelected = selectedConversation === conv.id;
                  const typeInfo = getContactTypeInfo(otherUser);

                  return (
                    <div
                      key={conv.id}
                      onClick={() => {
                        setSelectedConversation(conv.id);
                        fetchMessages(conv.id);
                      }}
                      className={`p-3 cursor-pointer transition-colors ${
                        isSelected ? 'bg-orange-50 border-r-2 border-orange-500' : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <div className="relative">
                          <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                            <span className="text-orange-600 font-medium text-sm">
                              {otherUser.prenom[0]}{otherUser.nom[0]}
                            </span>
                          </div>
                          {conv.unread_count && conv.unread_count > 0 && (
                            <div className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                              {conv.unread_count}
                            </div>
                          )}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <p className="font-medium text-sm text-gray-900 truncate">
                              {otherUser.prenom} {otherUser.nom}
                            </p>
                            <span className={`px-2 py-0.5 rounded-full text-xs ${typeInfo.color}`}>
                              {typeInfo.label}
                            </span>
                          </div>
                          
                          {conv.last_message && (
                            <p className="text-xs text-gray-500 truncate mt-1">
                              {conv.last_message.expediteur_id === currentUserId ? 'Vous: ' : ''}
                              {conv.last_message.contenu}
                            </p>
                          )}
                          
                          <p className="text-xs text-gray-400 mt-1">
                            {formatDate(conv.updated_at)}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Zone de chat */}
        <div className="flex-1 flex flex-col">
          {selectedConversation ? (
            <>
              {/* Header conversation */}
              <div className="p-4 border-b border-gray-100 bg-gray-50">
                {(() => {
                  const conv = conversations.find(c => c.id === selectedConversation);
                  const otherUser = conv?.other_user;
                  if (!otherUser) return null;

                  const typeInfo = getContactTypeInfo(otherUser);

                  return (
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                        <span className="text-orange-600 font-medium text-sm">
                          {otherUser.prenom[0]}{otherUser.nom[0]}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">
                          {otherUser.prenom} {otherUser.nom}
                        </p>
                        <span className={`px-2 py-1 rounded-full text-xs ${typeInfo.color}`}>
                          {typeInfo.label}
                        </span>
                      </div>
                    </div>
                  );
                })()}
              </div>

              {/* Messages */}
              <div className="flex-1 p-4 overflow-y-auto space-y-4">
                {loadingMessages ? (
                  <div className="text-center text-gray-500">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600 mx-auto"></div>
                    <p className="mt-2 text-sm">Chargement des messages...</p>
                  </div>
                ) : messages.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    <MessageCircle className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                    <p className="text-sm">Aucun message dans cette conversation</p>
                    <p className="text-xs text-gray-400 mt-1">Envoyez le premier message !</p>
                  </div>
                ) : (
                  messages.map((message) => {
                    const isOwn = message.expediteur_id === currentUserId;
                    
                    return (
                      <div key={message.id} className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                          isOwn 
                            ? 'bg-orange-600 text-white' 
                            : 'bg-gray-100 text-gray-900'
                        }`}>
                          <p className="text-sm">{message.contenu}</p>
                          <div className={`flex items-center space-x-1 mt-1 ${
                            isOwn ? 'justify-end' : 'justify-start'
                          }`}>
                            <span className={`text-xs ${
                              isOwn ? 'text-orange-100' : 'text-gray-500'
                            }`}>
                              {formatDate(message.created_at)}
                            </span>
                            {isOwn && (
                              <span className="text-orange-100">
                                {message.lu ? <CheckCircle className="w-3 h-3" /> : <Circle className="w-3 h-3" />}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Zone de saisie */}
              <div className="p-4 border-t border-gray-100">
                <div className="flex space-x-2">
                  <input
                    ref={messageInputRef}
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Tapez votre message..."
                    className="flex-1 p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    disabled={sending}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!newMessage.trim() || sending}
                    className="px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {sending ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <MessageCircle className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-lg mb-2">Sélectionnez une conversation</p>
                <p className="text-sm">pour commencer à discuter</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};