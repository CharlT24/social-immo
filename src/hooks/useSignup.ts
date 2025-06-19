import { useState } from 'react';
import { supabase } from '../lib/supabaseClient';

interface SignupData {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  userType: string;
  city: string;
  postalCode: string;
  region: string;
  [key: string]: any;
}

export const useSignup = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signup = async (data: SignupData) => {
    setLoading(true);
    setError(null);

    try {
      // 1. Créer l'utilisateur dans Supabase Auth
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email: data.email,
        password: data.password,
        options: {
          data: {
            firstName: data.firstName,
            lastName: data.lastName,
            userType: data.userType
          }
        }
      });

      if (authError) throw authError;

      // 2. Créer le profil utilisateur dans la table utilisateurs
      if (authData.user) {
        const { error: profileError } = await supabase
          .from('utilisateurs')
          .insert([{
            id: authData.user.id,
            email: data.email,
            nom: data.lastName,
            prenom: data.firstName,
            role: 'externe',
            statut_externe: data.userType === 'professional' ? 'agent_immobilier' : data.userType,
            ville: data.city,
            code_postal: data.postalCode,
            region: data.region,
            societe: data.company || null,
            siret: data.siret || null,
            questionnaire_data: data.questionnaire || {},
            profile_completed: true,
            onboarding_step: 4,
            actif: true,
            statut_validation: 'valide'
          }]);

        if (profileError) throw profileError;
      }

      return { success: true, user: authData.user };
    } catch (err: any) {
      setError(err.message || 'Erreur lors de l\'inscription');
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  return { signup, loading, error };
};
