'use client'

import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { MessageCircle, Send, Search, Users, Phone, Video } from 'lucide-react';

interface Message {
  id: string;
  content: string;
  user_id: string;
  chat_id: string;
  created_at: string;
}

interface Chat {
  id: string;
  name: string;
  last_message?: string;
  last_message_time?: string;
  unread_count: number;
}

const ChatComponent: React.FC = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [selectedChat, setSelectedChat] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadChats();
  }, []);

  useEffect(() => {
    if (selectedChat) {
      loadMessages(selectedChat);
    }
  }, [selectedChat]);

  const loadChats = async () => {
    // Demo data for chats
    const demoChats: Chat[] = [
      {
        id: 'chat-1',
        name: 'Agents Immobiliers Paris',
        last_message: 'Nouveau bien disponible !',
        last_message_time: new Date().toISOString(),
        unread_count: 3
      },
      {
        id: 'chat-2',
        name: 'Investisseurs Lyon',
        last_message: 'Rendement intéressant sur ce secteur',
        last_message_time: new Date(Date.now() - 3600000).toISOString(),
        unread_count: 0
      },
      {
        id: 'chat-3',
        name: 'Notaires Marseille',
        last_message: 'Documents prêts pour signature',
        last_message_time: new Date(Date.now() - 7200000).toISOString(),
        unread_count: 1
      }
    ];
    setChats(demoChats);
    setLoading(false);
  };

  const loadMessages = async (chatId: string) => {
    try {
      const { data, error } = await supabase
        .from('messages')
        .select('*')
        .eq('chat_id', chatId)
        .order('created_at', { ascending: true });

      if (error) throw error;
      setMessages(data || []);
    } catch (error) {
      console.error('Erreur lors du chargement des messages:', error);
      // Demo messages if DB query fails
      setMessages([
        {
          id: '1',
          content: 'Bonjour ! Comment ça va ?',
          user_id: 'other-user',
          chat_id: chatId,
          created_at: new Date(Date.now() - 3600000).toISOString()
        },
        {
          id: '2',
          content: 'Salut ! Ça va bien merci, et toi ?',
          user_id: 'current-user',
          chat_id: chatId,
          created_at: new Date(Date.now() - 3000000).toISOString()
        }
      ]);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedChat) return;

    const message: Message = {
      id: Date.now().toString(),
      content: newMessage,
      user_id: 'current-user',
      chat_id: selectedChat,
      created_at: new Date().toISOString()
    };

    try {
      const { error } = await supabase
        .from('messages')
        .insert([message]);

      if (error) throw error;
      
      setMessages([...messages, message]);
      setNewMessage('');
    } catch (error) {
      console.error('Erreur lors de l\'envoi:', error);
      // Fallback: add message locally
      setMessages([...messages, message]);
      setNewMessage('');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="flex h-96 bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Liste des chats */}
      <div className="w-1/3 border-r border-gray-200">
        <div className="p-4 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <input
              type="text"
              placeholder="Rechercher une conversation..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
        
        <div className="overflow-y-auto h-full">
          {chats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => setSelectedChat(chat.id)}
              className={`p-4 cursor-pointer hover:bg-gray-50 border-b border-gray-100 ${
                selectedChat === chat.id ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''
              }`}
            >
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-green-600 rounded-full flex items-center justify-center text-white font-semibold">
                  <Users className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-gray-900 truncate">
                      {chat.name}
                    </h4>
                    {chat.unread_count > 0 && (
                      <span className="bg-blue-600 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                        {chat.unread_count}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 truncate">
                    {chat.last_message}
                  </p>
                  <p className="text-xs text-gray-400">
                    {chat.last_message_time && new Date(chat.last_message_time).toLocaleTimeString('fr-FR', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Zone de chat */}
      <div className="flex-1 flex flex-col">
        {selectedChat ? (
          <>
            {/* En-tête du chat */}
            <div className="p-4 border-b border-gray-200 bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center text-white">
                    <Users className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      {chats.find(c => c.id === selectedChat)?.name}
                    </h3>
                    <p className="text-sm text-green-600">En ligne</p>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                    <Phone className="h-5 w-5" />
                  </button>
                  <button className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                    <Video className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${
                    message.user_id === 'current-user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-xs px-4 py-2 rounded-lg ${
                      message.user_id === 'current-user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-900'
                    }`}
                  >
                    <p className="text-sm">{message.content}</p>
                    <p className={`text-xs mt-1 ${
                      message.user_id === 'current-user' ? 'text-blue-200' : 'text-gray-500'
                    }`}>
                      {new Date(message.created_at).toLocaleTimeString('fr-FR', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Zone de saisie */}
            <div className="p-4 border-t border-gray-200">
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  placeholder="Tapez votre message..."
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button
                  onClick={sendMessage}
                  disabled={!newMessage.trim()}
                  className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="h-5 w-5" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <MessageCircle className="mx-auto h-12 w-12 mb-4 text-gray-300" />
              <p>Sélectionnez une conversation pour commencer</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatComponent;
