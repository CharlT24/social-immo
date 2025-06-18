'use client'

import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { Heart, MessageCircle, Share2, MoreHorizontal } from 'lucide-react';

interface Post {
  id: string;
  content: string;
  user_id: string;
  created_at: string;
  likes_count: number;
  comments_count: number;
}

const WallComponent: React.FC = () => {
  const [posts, setPosts] = useState<Post[]>([]);
  const [newPost, setNewPost] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPosts();
  }, []);

  const fetchPosts = async () => {
    try {
      const { data, error } = await supabase
        .from('posts')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setPosts(data || []);
    } catch (error) {
      console.error('Erreur lors du chargement des posts:', error);
    } finally {
      setLoading(false);
    }
  };

  const createPost = async () => {
    if (!newPost.trim()) return;

    try {
      const { data, error } = await supabase
        .from('posts')
        .insert([
          { 
            content: newPost, 
            user_id: 'user-demo-id',
            likes_count: 0,
            comments_count: 0
          }
        ])
        .select()
        .single();

      if (error) throw error;
      
      setPosts([data, ...posts]);
      setNewPost('');
    } catch (error) {
      console.error('Erreur lors de la création du post:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Créer un post */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="space-y-4">
          <textarea
            value={newPost}
            onChange={(e) => setNewPost(e.target.value)}
            placeholder="Quoi de neuf dans l'immobilier ?"
            className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={3}
          />
          <div className="flex justify-between items-center">
            <div className="flex space-x-2">
              <button className="text-gray-500 hover:text-blue-600 transition-colors">
                📷 Photo
              </button>
              <button className="text-gray-500 hover:text-blue-600 transition-colors">
                🏠 Bien
              </button>
            </div>
            <button
              onClick={createPost}
              disabled={!newPost.trim()}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Publier
            </button>
          </div>
        </div>
      </div>

      {/* Liste des posts */}
      <div className="space-y-4">
        {posts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <MessageCircle className="mx-auto h-12 w-12 mb-4 text-gray-300" />
            <p>Aucun post pour le moment. Soyez le premier à publier !</p>
          </div>
        ) : (
          posts.map((post) => (
            <div key={post.id} className="bg-white rounded-lg shadow-md">
              {/* En-tête du post */}
              <div className="flex items-center justify-between p-4 border-b">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
                    U
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900">Utilisateur Demo</h4>
                    <p className="text-sm text-gray-500">
                      {new Date(post.created_at).toLocaleDateString('fr-FR', {
                        day: 'numeric',
                        month: 'long',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                  </div>
                </div>
                <button className="text-gray-400 hover:text-gray-600">
                  <MoreHorizontal className="h-5 w-5" />
                </button>
              </div>

              {/* Contenu du post */}
              <div className="p-4">
                <p className="text-gray-900 whitespace-pre-wrap">{post.content}</p>
              </div>

              {/* Actions du post */}
              <div className="px-4 py-3 border-t bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex space-x-6">
                    <button className="flex items-center space-x-2 text-gray-600 hover:text-red-600 transition-colors">
                      <Heart className="h-5 w-5" />
                      <span className="text-sm">{post.likes_count}</span>
                    </button>
                    <button className="flex items-center space-x-2 text-gray-600 hover:text-blue-600 transition-colors">
                      <MessageCircle className="h-5 w-5" />
                      <span className="text-sm">{post.comments_count}</span>
                    </button>
                    <button className="flex items-center space-x-2 text-gray-600 hover:text-green-600 transition-colors">
                      <Share2 className="h-5 w-5" />
                      <span className="text-sm">Partager</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default WallComponent;
