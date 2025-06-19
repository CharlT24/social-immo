'use client'

import React, { useState } from 'react';
import { Building, Home, Search, TrendingUp, ArrowRight, ArrowLeft, Check, Star } from 'lucide-react';

const SocialImmoSignup = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [userType, setUserType] = useState('');

  const userTypes = [
    {
      type: 'professional',
      title: 'Pro de l\'Immobilier',
      subtitle: 'Agent, artisan, expert...',
      icon: Building,
      color: 'from-orange-500 to-orange-600',
      borderColor: 'border-orange-200 hover:border-orange-400',
      description: 'Diffusez vos biens, développez votre réseau professionnel et trouvez de nouveaux clients',
      features: ['Diffusion de biens', 'Réseau professionnel', 'Génération de leads', 'Outils marketing']
    },
    {
      type: 'seller',
      title: 'Vendeur',
      subtitle: 'Particulier propriétaire',
      icon: Home,
      color: 'from-orange-400 to-orange-500',
      borderColor: 'border-orange-200 hover:border-orange-400',
      description: 'Vendez votre bien avec une visibilité maximale et trouvez le bon acquéreur',
      features: ['Estimation gratuite', 'Visibilité maximale', 'Contact agents', 'Conseils experts']
    },
    {
      type: 'buyer',
      title: 'Acheteur',
      subtitle: 'Recherche de bien',
      icon: Search,
      color: 'from-orange-600 to-orange-700',
      borderColor: 'border-orange-200 hover:border-orange-400',
      description: 'Trouvez le bien idéal, connectez-vous aux pros et accédez aux exclusivités',
      features: ['Alertes personnalisées', 'Biens exclusifs', 'Contact direct pros', 'Aide au financement']
    },
    {
      type: 'investor',
      title: 'Investisseur',
      subtitle: 'Opportunités d\'investissement',
      icon: TrendingUp,
      color: 'from-orange-700 to-orange-800',
      borderColor: 'border-orange-200 hover:border-orange-400',
      description: 'Découvrez les meilleures opportunités d\'investissement et maximisez votre rentabilité',
      features: ['Analyse rentabilité', 'Opportunités exclusives', 'Réseau investisseurs', 'Conseils experts']
    }
  ];

  const handleTypeSelection = (type) => {
    setUserType(type);
    setCurrentStep(2);
  };

  const nextStep = () => {
    setCurrentStep(Math.min(currentStep + 1, 4));
  };

  const prevStep = () => {
    setCurrentStep(Math.max(currentStep - 1, 1));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-orange-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-orange-500 to-orange-600 rounded-full mb-6">
            <span className="text-white text-2xl font-bold">SI</span>
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Rejoignez Social Immo
          </h1>
          <p className="text-xl text-gray-600">
            Le premier réseau social de l'immobilier français
          </p>
        </div>

        {/* Form container */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {/* Step 1: Type selection */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-4">
                  Quel est votre profil ?
                </h2>
                <p className="text-lg text-gray-600">
                  Choisissez le type de compte qui correspond le mieux à vos besoins
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                {userTypes.map((type) => {
                  const IconComponent = type.icon;
                  return (
                    <div
                      key={type.type}
                      onClick={() => handleTypeSelection(type.type)}
                      className={`relative p-6 border-2 rounded-xl cursor-pointer transition-all duration-200 hover:shadow-lg ${type.borderColor} ${
                        userType === type.type ? 'border-orange-500 shadow-lg' : ''
                      }`}
                    >
                      <div className="text-center">
                        <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br ${type.color} mb-4`}>
                          <IconComponent className="w-8 h-8 text-white" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">{type.title}</h3>
                        <p className="text-sm text-gray-600 mb-3">{type.subtitle}</p>
                        <p className="text-sm text-gray-700 mb-4">{type.description}</p>
                        
                        <div className="space-y-2">
                          {type.features.map((feature, index) => (
                            <div key={index} className="flex items-center text-sm text-gray-600">
                              <Star className="w-4 h-4 text-orange-400 mr-2" />
                              <span>{feature}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      {userType === type.type && (
                        <div className="absolute top-4 right-4">
                          <div className="w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center">
                            <Check className="w-4 h-4 text-white" />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Autres étapes */}
          {currentStep === 2 && (
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Étape 2 - Informations personnelles
              </h2>
              <p className="text-gray-600 mb-4">
                Profil sélectionné : <span className="font-semibold text-orange-600">{userType}</span>
              </p>
              <p className="text-gray-500">Formulaire à développer...</p>
            </div>
          )}

          {currentStep === 3 && (
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Étape 3 - Localisation</h2>
              <p className="text-gray-600">À développer...</p>
            </div>
          )}

          {currentStep === 4 && (
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Félicitations ! 🎉</h2>
              <p className="text-gray-600">Votre compte a été créé avec succès</p>
            </div>
          )}

          {/* Navigation buttons */}
          <div className="flex justify-between items-center mt-8 pt-6 border-t border-gray-200">
            <button
              onClick={prevStep}
              disabled={currentStep === 1}
              className="flex items-center space-x-2 px-6 py-3 text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Retour</span>
            </button>

            {currentStep < 4 ? (
              <button
                onClick={nextStep}
                className="flex items-center space-x-2 bg-orange-600 text-white px-6 py-3 rounded-lg hover:bg-orange-700 transition-colors font-semibold"
              >
                <span>Continuer</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => alert('Redirection vers l\'application...')}
                className="flex items-center space-x-2 bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors font-semibold"
              >
                <span>Accéder à Social Immo</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SocialImmoSignup;
