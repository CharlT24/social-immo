import React from 'react';
import { Building, Home, Search, TrendingUp, Users } from 'lucide-react';

interface UserBadgeProps {
  type: 'professional' | 'seller' | 'buyer' | 'investor';
  className?: string;
}

const UserBadge: React.FC<UserBadgeProps> = ({ type, className = '' }) => {
  const badges = {
    'professional': { 
      label: 'Pro Immo', 
      color: 'bg-green-100 text-green-800 border-green-200', 
      icon: Building 
    },
    'seller': { 
      label: 'Vendeur', 
      color: 'bg-blue-100 text-blue-800 border-blue-200', 
      icon: Home 
    },
    'buyer': { 
      label: 'Acheteur', 
      color: 'bg-orange-100 text-orange-800 border-orange-200', 
      icon: Search 
    },
    'investor': { 
      label: 'Investisseur', 
      color: 'bg-purple-100 text-purple-800 border-purple-200', 
      icon: TrendingUp 
    }
  };

  const badge = badges[type] || badges.professional;
  const IconComponent = badge.icon;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${badge.color} ${className}`}>
      <IconComponent className="w-3 h-3 mr-1" />
      {badge.label}
    </span>
  );
};

export default UserBadge;
