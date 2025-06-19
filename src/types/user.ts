export type UserType = 'professional' | 'seller' | 'buyer' | 'investor';

export interface User {
  id: string;
  email: string;
  nom: string;
  prenom: string;
  role: 'admin' | 'agent' | 'externe';
  statut_externe: string;
  societe?: string;
  ville?: string;
  code_postal?: string;
  region?: string;
  profile_completed: boolean;
  actif: boolean;
  created_at: string;
}

export interface SignupFormData {
  email: string;
  password: string;
  confirmPassword: string;
  firstName: string;
  lastName: string;
  phone?: string;
  userType: UserType;
  subCategory?: string;
  company?: string;
  siret?: string;
  city: string;
  postalCode: string;
  region: string;
  address?: string;
  budget?: string;
  propertyType?: string;
  investmentType?: string;
  notifications: boolean;
  newsletter: boolean;
  publicProfile: boolean;
  questionnaire: Record<string, any>;
}
