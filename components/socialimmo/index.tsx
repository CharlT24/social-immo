import React, { useState } from 'react';

// Import des composants modulaires
import { WallComponent } from './WallComponent';
import { ChatComponent } from './ChatComponent';
import { FriendsComponent } from './FriendsComponent';

interface SocialImmoProps {
  className?: string;
}

const SocialImmo: React.FC<SocialImmoProps> = ({ className = "" }) => {
  const [activeTab, setActiveTab] = useState<'wall' | 'chat' | 'friends'>('wall');

  const tabs = [
    { id: 'wall', label: 'Fil d\'actualité', icon: '📰' },
    { id: 'chat', label: 'Messages', icon: '💬' },
    { id: 'friends', label: 'Réseau', icon: '👥' }
  ];

  return (
    <div className={`bg-gray-50 min-h-screen ${className}`}>
      {/* Header avec navigation */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">
                Social Immo
              </h1>
              <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                Réseau Pro
              </span>
            </div>

            {/* Navigation par onglets */}
            <nav className="flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>
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
                <button className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg">
                  📝 Publier une actualité
                </button>
                <button className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg">
                  🏠 Partager un bien
                </button>
                <button className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg">
                  👤 Trouver des contacts
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SocialImmo;
