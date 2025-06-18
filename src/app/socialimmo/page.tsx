'use client'

import React, { useState } from 'react';
import WallComponent from '../../components/socialimmo/WallComponent';
import ChatComponent from '../../components/socialimmo/ChatComponent';
import FriendsComponent from '../../components/socialimmo/FriendsComponent';
import { Home, MessageCircle, Users, Search, Bell, User } from 'lucide-react';

export default function SocialImmoPage() {
  const [activeTab, setActiveTab] = useState<'wall' | 'chat' | 'friends'>('wall');

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-8">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <Home className="h-5 w-5 text-white" />
                </div>
                <h1 className="text-xl font-bold text-gray-900">Social Immo</h1>
              </div>
              
              <nav className="hidden md:flex space-x-8">
                <button
                  onClick={() => setActiveTab('wall')}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium ${
                    activeTab === 'wall'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Home className="h-4 w-4" />
                  <span>Accueil</span>
                </button>
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium ${
                    activeTab === 'chat'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <MessageCircle className="h-4 w-4" />
                  <span>Messages</span>
                </button>
                <button
                  onClick={() => setActiveTab('friends')}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium ${
                    activeTab === 'friends'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Users className="h-4 w-4" />
                  <span>Réseau</span>
                </button>
              </nav>
            </div>

            <div className="flex items-center space-x-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <input
                  type="text"
                  placeholder="Rechercher..."
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent w-64"
                />
              </div>
              
              <button className="relative p-2 text-gray-600 hover:text-gray-900">
                <Bell className="h-5 w-5" />
                <span className="absolute top-0 right-0 h-2 w-2 bg-red-500 rounded-full"></span>
              </button>
              
              <button className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                <User className="h-4 w-4 text-gray-600" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation mobile */}
      <div className="md:hidden bg-white border-t">
        <div className="flex justify-around py-2">
          <button
            onClick={() => setActiveTab('wall')}
            className={`flex flex-col items-center py-2 px-3 ${
              activeTab === 'wall' ? 'text-blue-600' : 'text-gray-500'
            }`}
          >
            <Home className="h-5 w-5" />
            <span className="text-xs mt-1">Accueil</span>
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex flex-col items-center py-2 px-3 ${
              activeTab === 'chat' ? 'text-blue-600' : 'text-gray-500'
            }`}
          >
            <MessageCircle className="h-5 w-5" />
            <span className="text-xs mt-1">Messages</span>
          </button>
          <button
            onClick={() => setActiveTab('friends')}
            className={`flex flex-col items-center py-2 px-3 ${
              activeTab === 'friends' ? 'text-blue-600' : 'text-gray-500'
            }`}
          >
            <Users className="h-5 w-5" />
            <span className="text-xs mt-1">Réseau</span>
          </button>
        </div>
      </div>

      {/* Contenu principal */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'wall' && <WallComponent />}
        {activeTab === 'chat' && <ChatComponent />}
        {activeTab === 'friends' && <FriendsComponent />}
      </main>
    </div>
  );
}
