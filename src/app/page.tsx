import Link from 'next/link';
import { Home, Users, MessageCircle, ArrowRight } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <div className="flex justify-center mb-8">
            <div className="w-20 h-20 bg-blue-600 rounded-2xl flex items-center justify-center">
              <Home className="h-10 w-10 text-white" />
            </div>
          </div>
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Social Immo
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Le premier réseau social entièrement dédié à l'immobilier français. 
            Connectez-vous avec des professionnels, partagez vos biens et développez votre réseau.
          </p>
          <Link
            href="/socialimmo"
            className="inline-flex items-center space-x-2 bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            <span>Découvrir la plateforme</span>
            <ArrowRight className="h-5 w-5" />
          </Link>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div className="bg-white p-8 rounded-xl shadow-lg">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-6">
              <Users className="h-6 w-6 text-green-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              Réseau Professionnel
            </h3>
            <p className="text-gray-600">
              Connectez-vous avec des agents, notaires, promoteurs et investisseurs. 
              Développez votre réseau immobilier.
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl shadow-lg">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-6">
              <MessageCircle className="h-6 w-6 text-blue-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              Communication
            </h3>
            <p className="text-gray-600">
              Échangez en temps réel avec vos contacts. Groupes thématiques, 
              messages privés et discussions professionnelles.
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl shadow-lg">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-6">
              <Home className="h-6 w-6 text-purple-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              Partage de Biens
            </h3>
            <p className="text-gray-600">
              Publiez et partagez vos biens immobiliers avec votre réseau. 
              Géolocalisation et visites virtuelles incluses.
            </p>
          </div>
        </div>

        <div className="text-center mt-16">
          <p className="text-gray-600">
            Version de démonstration - Données fictives pour présentation
          </p>
        </div>
      </div>
    </div>
  );
}
