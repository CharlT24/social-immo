import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { MessageCircle, Send, Search, Users } from 'lucide-react';

interface Message {
  id: number;
  contenu: string;
  expediteur_id: string;
  created_at: string;
}

interface ChatComponentProps {
  className?: string;
}

export const ChatComponent: React.FC<ChatComponentProps> = ({ 
  className = ""
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  useEffect(() => {
    initializeChat();
  }, []);

  const initializeChat = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        setCurrentUserId(session.user.id);
        await fetchMessages();
      }
    } catch (error) {
      console.error('Erreur initialisation chat:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async () => {
    try {
      const { data, error } = await supabase
        .from('messages_prives')
        .select('*')
        .order('created_at', { ascending: true })
        .limit(50);

      if (!error) {
        setMessages(data || []);
      }
    } catch (error) {
      console.error('Erreur chargement messages:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !currentUserId) return;

    try {
      const { data, error } = await supabase
        .from('messages_prives')
        .insert([{
          contenu: newMessage.trim(),
          expediteur_id: currentUserId,
          conversation_id: 1 // Conversation générale pour le demo
        }])
        .select()
        .single();

      if (!error) {
        setMessages(prev => [...prev, data]);
        setNewMessage('');
      }
    } catch (error) {
      console.error('Erreur envoi message:', error);
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

  return (
    <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Messages privés
          </h2>
          <button className="bg-orange-600 text-white px-3 py-2 rounded-lg hover:bg-orange-700 text-sm">
            + Nouveau chat
          </button>
        </div>
      </div>

      <div className="flex h-96">
        {/* Liste des conversations */}
        <div className="w-1/3 border-r border-gray-100 p-4">
          <div className="text-center text-gray-500 py-8">
            <MessageCircle className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-sm">Aucune conversation</p>
            <p className="text-xs text-gray-400 mt-1">
              Commencez par ajouter des amis
            </p>
          </div>
        </div>

        {/* Zone de chat */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <MessageCircle className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p className="text-lg mb-2">Sélectionnez une conversation</p>
              <p className="text-sm">pour commencer à discuter</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
