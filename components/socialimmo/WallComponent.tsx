import React, { useState, useEffect, useRef } from 'react';
import { supabase } from '../../lib/supabaseClient';
import {
  Heart, MessageCircle, Share2, MoreHorizontal, User,
  AlertCircle, RefreshCw, Image, X
} from 'lucide-react';

interface Post {
  id: number;
  contenu: string;
  auteur_id: string;
  auteur_nom?: string;
  auteur_prenom?: string;
  created_at: string;
  bien_id?: number;
  type_post?: string;
  metadata?: any;
  images?: string[];
  likes_count?: number;
  is_liked?: boolean;
  commentaires_count?: number;
}

interface Comment {
  id: number;
  contenu: string;
  auteur_nom: string;
  auteur_prenom: string;
  created_at: string;
}

interface User {
  id: string;
  prenom: string;
  nom: string;
}

interface WallComponentProps {
  userId?: string;
  className?: string;
}

export const WallComponent: React.FC<WallComponentProps> = ({
  userId,
  className = ""
}) => {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [newPost, setNewPost] = useState('');
  const [isPosting, setIsPosting] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initializeComponent();
  }, []);

  const initializeComponent = async () => {
    try {
      setError(null);
      await getCurrentUser();
      await fetchPosts();
    } catch (error: any) {
      setError(`Erreur lors du chargement: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getCurrentUser = async () => {
    const { data: { session }, error: sessionError } = await supabase.auth.getSession();
    if (sessionError || !session?.user) throw new Error('Aucune session valide');

    const { data: userData, error: userError } = await supabase
      .from('utilisateurs')
      .select('id, prenom, nom')
      .eq('id', session.user.id)
      .single();

    if (userError) throw new Error(userError.message);
    setCurrentUser(userData);
  };

  const fetchPosts = async () => {
    try {
      const { data, error } = await supabase
        .from('posts')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(20);

      if (error) throw error;
      setPosts(data || []);
    } catch (error: any) {
      console.error('Erreur chargement posts:', error);
      setPosts([]);
    }
  };

  const handleCreatePost = async () => {
    if (!newPost.trim() || !currentUser) return;

    setIsPosting(true);
    try {
      const { data, error } = await supabase
        .from('posts')
        .insert([{
          contenu: newPost.trim(),
          auteur_id: currentUser.id,
          auteur_nom: currentUser.nom,
          auteur_prenom: currentUser.prenom,
          type_post: 'texte'
        }])
        .select()
        .single();

      if (error) throw error;

      setPosts(prev => [data, ...prev]);
      setNewPost('');
    } catch (e: any) {
      console.error('Erreur création post:', e);
      setError(e.message);
    } finally {
      setIsPosting(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffMins < 1) return 'À l\'instant';
      if (diffMins < 60) return `Il y a ${diffMins}min`;
      if (diffHours < 24) return `Il y a ${diffHours}h`;
      if (diffDays < 7) return `Il y a ${diffDays}j`;

      return date.toLocaleDateString('fr-FR', {
        day: 'numeric',
        month: 'short'
      });
    } catch {
      return 'Date invalide';
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
    <div className={`space-y-6 ${className}`}>
      {/* Formulaire de publication */}
      <div className="bg-white border rounded-lg p-4">
        <textarea
          placeholder="Que voulez-vous partager ?"
          value={newPost}
          onChange={(e) => setNewPost(e.target.value)}
          rows={3}
          className="w-full border rounded-md p-3 resize-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
        />
        
        <div className="mt-3 flex justify-between items-center">
          <div className="flex items-center space-x-2 text-gray-500">
            <Image className="w-5 h-5" />
            <span className="text-sm">Photo</span>
          </div>
          <button
            onClick={handleCreatePost}
            disabled={isPosting || !newPost.trim()}
            className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-2 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isPosting ? 'Publication...' : 'Publier'}
          </button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Liste des posts */}
      {posts.length === 0 ? (
        <div className="bg-white border rounded-lg p-8 text-center">
          <MessageCircle className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Aucune publication
          </h3>
          <p className="text-gray-600">
            Soyez le premier à partager quelque chose !
          </p>
        </div>
      ) : (
        posts.map(post => (
          <div key={post.id} className="bg-white border rounded-lg p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center font-semibold text-orange-700">
                {(post.auteur_prenom?.[0] || 'U')}{(post.auteur_nom?.[0] || '')}
              </div>
              <div>
                <p className="font-semibold text-gray-900">
                  {post.auteur_prenom} {post.auteur_nom}
                </p>
                <p className="text-sm text-gray-500">{formatDate(post.created_at)}</p>
              </div>
            </div>
            
            <p className="text-gray-800 whitespace-pre-line mb-4">{post.contenu}</p>

            {/* Actions */}
            <div className="flex items-center space-x-6 pt-3 border-t border-gray-100">
              <button className="flex items-center space-x-2 text-gray-500 hover:text-red-500 transition-colors">
                <Heart className="w-5 h-5" />
                <span className="text-sm">J'aime</span>
              </button>
              <button className="flex items-center space-x-2 text-gray-500 hover:text-blue-500 transition-colors">
                <MessageCircle className="w-5 h-5" />
                <span className="text-sm">Commenter</span>
              </button>
              <button className="flex items-center space-x-2 text-gray-500 hover:text-green-500 transition-colors">
                <Share2 className="w-5 h-5" />
                <span className="text-sm">Partager</span>
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
