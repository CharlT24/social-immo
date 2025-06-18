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
  const [debugInfo, setDebugInfo] = useState<string>('');
  const [expandedComments, setExpandedComments] = useState<{ [key: number]: boolean }>({});
  const [comments, setComments] = useState<{ [key: number]: Comment[] }>({});
  const [newComment, setNewComment] = useState<{ [key: number]: string }>({});
  const [refreshing, setRefreshing] = useState(false);
  const [tableExists, setTableExists] = useState<boolean | null>(null);
  const [lastRefresh, setLastRefresh] = useState<number>(Date.now());
  const [autoRefreshEnabled] = useState(true);

  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [imagePreview, setImagePreview] = useState<string[]>([]);
  const [uploadingImages, setUploadingImages] = useState(false);
  const [expandedImages, setExpandedImages] = useState<{ [key: number]: boolean }>({});

  const fileInputRef = useRef<HTMLInputElement>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (autoRefreshEnabled && !loading && !isPosting && tableExists) {
      if (intervalRef.current) clearInterval(intervalRef.current);

      intervalRef.current = setInterval(() => {
        fetchPosts(true);
        setLastRefresh(Date.now());
      }, 30000);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefreshEnabled, loading, isPosting, tableExists]);

  useEffect(() => {
    initializeComponent();
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const initializeComponent = async () => {
    try {
      setError(null);
      setDebugInfo('Initialisation Social Immo...');
      await getCurrentUser();
      await checkTableExists();
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

  const checkTableExists = async () => {
    const { error } = await supabase
      .from('posts')
      .select('id')
      .limit(1);

    if (error) {
      if (error.code === 'PGRST116') throw new Error('Table \"posts\" introuvable');
      throw new Error(`Erreur table posts: ${error.message}`);
    }
    setTableExists(true);
  };

  const getFriendIds = async (): Promise<string[]> => {
    if (!currentUser) return [];

    const { data, error } = await supabase
      .from('demandes_contact')
      .select('expediteur_id, destinataire_id')
      .or(`expediteur_id.eq.${currentUser.id},destinataire_id.eq.${currentUser.id}`)
      .eq('statut', 'accepte');

    if (error) return [currentUser.id];

    const friendIds = new Set<string>();
    data?.forEach((d) => {
      if (d.expediteur_id !== currentUser.id) friendIds.add(d.expediteur_id);
      if (d.destinataire_id !== currentUser.id) friendIds.add(d.destinataire_id);
    });

    return [currentUser.id, ...Array.from(friendIds)];
  };

  const fetchPosts = async (silent = false) => {
    if (!tableExists) return;

    if (!silent) setRefreshing(true);
    try {
      const authorIds = await getFriendIds();
      const { data, error } = await supabase
        .from('posts')
        .select(`
          id, contenu, auteur_id, auteur_nom, auteur_prenom,
          created_at, bien_id, type_post, metadata, images
        `)
        .in('auteur_id', authorIds)
        .order('created_at', { ascending: false })
        .limit(20);

      if (error) throw new Error(error.message);

      const enrichedPosts = await Promise.all(
        (data || []).map(async (post) => {
          const [likes, commentsCount] = await Promise.all([
            getLikesForPost(post.id),
            getCommentsCount(post.id)
          ]);

          let processedImages: string[] = [];
          try {
            if (typeof post.images === 'string') processedImages = JSON.parse(post.images);
            else if (Array.isArray(post.images)) processedImages = post.images;
          } catch {}

          return {
            ...post,
            images: processedImages,
            likes_count: likes.count,
            is_liked: likes.isLiked,
            commentaires_count: commentsCount
          };
        })
      );

      setPosts(enrichedPosts);
    } catch (error: any) {
      if (!silent) setError(`Impossible de charger les publications: ${error.message}`);
      setPosts([]);
    } finally {
      setRefreshing(false);
    }
  };
  const getLikesForPost = async (postId: number) => {
    try {
      const { count, error: countError } = await supabase
        .from('likes_posts')
        .select('*', { count: 'exact', head: true })
        .eq('post_id', postId);

      if (countError) return { count: 0, isLiked: false };

      let isLiked = false;
      if (currentUser) {
        const { data, error } = await supabase
          .from('likes_posts')
          .select('id')
          .eq('post_id', postId)
          .eq('user_id', currentUser.id)
          .single();

        if (data) isLiked = true;
      }

      return { count: count || 0, isLiked };
    } catch {
      return { count: 0, isLiked: false };
    }
  };

  const getCommentsCount = async (postId: number) => {
    try {
      const { count, error } = await supabase
        .from('commentaires_posts')
        .select('*', { count: 'exact', head: true })
        .eq('post_id', postId);

      return count || 0;
    } catch {
      return 0;
    }
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []).slice(0, 4);
    setSelectedImages(files);
    setImagePreview(files.map(file => URL.createObjectURL(file)));
  };

  const removeImage = (index: number) => {
    const newFiles = selectedImages.filter((_, i) => i !== index);
    const newPreviews = imagePreview.filter((_, i) => i !== index);
    URL.revokeObjectURL(imagePreview[index]);
    setSelectedImages(newFiles);
    setImagePreview(newPreviews);
  };

  const uploadImages = async (): Promise<string[]> => {
    if (selectedImages.length === 0) return [];

    setUploadingImages(true);
    const uploadedUrls: string[] = [];

    try {
      for (let i = 0; i < selectedImages.length; i++) {
        const file = selectedImages[i];
        const fileName = `posts/${Date.now()}_${i}_${file.name}`;

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
if (typeof window === 'undefined') return []; // sécurité build

const img = document.createElement('img');

await new Promise<void>((resolve, reject) => {
  img.onload = () => resolve();
  img.onerror = () => reject(new Error('Erreur chargement image'));
  img.src = URL.createObjectURL(file);
});


        const maxWidth = 1200;
        const maxHeight = 800;
        let { width, height } = img;

        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width *= ratio;
          height *= ratio;
        }

        canvas.width = width;
        canvas.height = height;
        ctx?.drawImage(img, 0, 0, width, height);

const blob: Blob = await new Promise((resolve, reject) => {
  canvas.toBlob((result) => {
    if (result) resolve(result);
    else reject(new Error('Échec de la conversion en blob'));
  }, 'image/jpeg', 0.8);
});

        const { data, error } = await supabase.storage
          .from('photos')
          .upload(fileName, blob, { upsert: true });

        if (!error) {
          const { data: urlData } = supabase.storage.from('photos').getPublicUrl(fileName);
          if (urlData?.publicUrl) uploadedUrls.push(urlData.publicUrl);
        }

        URL.revokeObjectURL(img.src);
      }
    } catch (e) {
      console.error('Erreur upload images', e);
    } finally {
      setUploadingImages(false);
    }

    return uploadedUrls;
  };

  const handleCreatePost = async () => {
    if ((!newPost.trim() && selectedImages.length === 0) || !currentUser) return;
    if (!tableExists) {
      alert('La table posts est manquante.');
      return;
    }

    setIsPosting(true);
    try {
      const imageUrls = await uploadImages();

      const { data, error } = await supabase
        .from('posts')
        .insert([{
          contenu: newPost.trim() || '📷 Photo',
          auteur_id: currentUser.id,
          auteur_nom: currentUser.nom,
          auteur_prenom: currentUser.prenom,
          type_post: imageUrls.length > 0 ? 'photo' : 'texte',
          images: imageUrls.length > 0 ? JSON.stringify(imageUrls) : null
        }])
        .select()
        .single();

      if (error) throw error;

      const newPublishedPost: Post = {
        ...data,
        images: imageUrls,
        likes_count: 0,
        is_liked: false,
        commentaires_count: 0
      };

      setPosts(prev => [newPublishedPost, ...prev]);
      setNewPost('');
      setSelectedImages([]);
      setImagePreview([]);
    } catch (e: any) {
      console.error('Erreur création post:', e.message);
      setError(e.message);
    } finally {
      setIsPosting(false);
    }
  };

  const handleLike = async (postId: number) => {
    if (!currentUser) return;

    const post = posts.find(p => p.id === postId);
    if (!post) return;

    try {
      if (post.is_liked) {
        await supabase
          .from('likes_posts')
          .delete()
          .eq('post_id', postId)
          .eq('user_id', currentUser.id);

        setPosts(prev => prev.map(p =>
          p.id === postId
            ? { ...p, likes_count: (p.likes_count || 1) - 1, is_liked: false }
            : p
        ));
      } else {
        await supabase
          .from('likes_posts')
          .insert([{ post_id: postId, user_id: currentUser.id }]);

        setPosts(prev => prev.map(p =>
          p.id === postId
            ? { ...p, likes_count: (p.likes_count || 0) + 1, is_liked: true }
            : p
        ));
      }
    } catch (e) {
      console.error('Erreur gestion like:', e);
    }
  };
  const loadComments = async (postId: number) => {
    try {
      const { data, error } = await supabase
        .from('commentaires_posts')
        .select('id, contenu, auteur_nom, auteur_prenom, created_at')
        .eq('post_id', postId)
        .order('created_at', { ascending: true });

      if (error) throw error;

      setComments(prev => ({ ...prev, [postId]: data || [] }));
    } catch (error) {
      console.error('Erreur chargement commentaires:', error);
    }
  };

  const handleToggleComments = async (postId: number) => {
    const isExpanded = expandedComments[postId];
    if (!isExpanded) await loadComments(postId);
    setExpandedComments(prev => ({ ...prev, [postId]: !isExpanded }));
  };

  const handleAddComment = async (postId: number) => {
    if (!currentUser || !newComment[postId]?.trim()) return;

    try {
      const { data, error } = await supabase
        .from('commentaires_posts')
        .insert([{
          post_id: postId,
          auteur_id: currentUser.id,
          auteur_nom: currentUser.nom,
          auteur_prenom: currentUser.prenom,
          contenu: newComment[postId].trim()
        }])
        .select()
        .single();

      if (error) throw error;

      setComments(prev => ({
        ...prev,
        [postId]: [...(prev[postId] || []), data]
      }));

      setPosts(prev => prev.map(p =>
        p.id === postId
          ? { ...p, commentaires_count: (p.commentaires_count || 0) + 1 }
          : p
      ));

      setNewComment(prev => ({ ...prev, [postId]: '' }));
    } catch (error) {
      console.error('Erreur ajout commentaire:', error);
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

  const getMetadataDisplay = (metadata: any) => {
    if (!metadata || typeof metadata !== 'object') return null;

    try {
      const meta = typeof metadata === 'string' ? JSON.parse(metadata) : metadata;
      return meta;
    } catch {
      return null;
    }
  };
  return (
    <div className={`space-y-6 ${className}`}>

      <div className="flex items-center justify-between bg-white border rounded-lg px-4 py-2">
  <div className="flex items-center space-x-4">
    <button
      className="flex items-center space-x-1 text-gray-700 hover:text-orange-600 transition"
      title="Aimé par mes amis"
    >
      <Heart className="w-5 h-5" />
      <span className="text-sm font-medium">Aimés par mes amis</span>
    </button>
    <button
      className="flex items-center space-x-1 text-gray-700 hover:text-orange-600 transition"
      title="Fil d'actualité"
      onClick={initializeComponent}
    >
      <MessageCircle className="w-5 h-5" />
      <span className="text-sm font-medium">Mur</span>
    </button>
  </div>
</div>

      {/* Formulaire de publication */}
      <div className="bg-white border rounded-lg p-4">
<textarea
  placeholder="Exprimez-vous..."
  value={newPost}
  onChange={(e) => setNewPost(e.target.value)}
  rows={3}
  className="w-full border rounded-md p-2"
/>
{imagePreview.length > 0 && (
  <div className="grid grid-cols-2 gap-2 mt-3">
    {imagePreview.map((src, i) => (
      <div key={i} className="relative">
        <img src={src} alt={`preview-${i}`} className="rounded w-full h-32 object-cover" />
        <button
          className="absolute top-1 right-1 bg-black/50 text-white rounded-full p-1"
          onClick={() => removeImage(i)}
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    ))}
  </div>
)}


        <div className="mt-2 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={selectedImages.length >= 4}
              className="text-sm text-gray-600 hover:text-orange-600"
            >
              <Image className="w-5 h-5 inline" /> Ajouter photo
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={handleImageSelect}
            />
            {selectedImages.length > 0 && (
              <span className="text-xs text-gray-500">
                {selectedImages.length}/4 images sélectionnées
              </span>
            )}
          </div>
          <button
            onClick={handleCreatePost}
            disabled={isPosting || uploadingImages || (!newPost.trim() && selectedImages.length === 0)}
            className="bg-orange-500 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            {isPosting || uploadingImages ? 'Envoi...' : 'Publier'}
          </button>
        </div>

        {/* Previews des images */}
        {imagePreview.length > 0 && (
          <div className="grid grid-cols-2 gap-2 mt-3">
            {imagePreview.map((src, i) => (
              <div key={i} className="relative">
                <img src={src} alt={`preview-${i}`} className="rounded w-full h-32 object-cover" />
                <button
                  className="absolute top-1 right-1 bg-black/50 text-white rounded-full p-1"
                  onClick={() => removeImage(i)}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Liste des posts */}
      {posts.map(post => (
        <div key={post.id} className="bg-white border rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center font-semibold text-orange-700">
              {(post.auteur_prenom?.[0] || 'U')}{(post.auteur_nom?.[0] || '')}
            </div>
            <div>
              <p className="font-semibold">{post.auteur_prenom} {post.auteur_nom}</p>
              <p className="text-sm text-gray-500">{formatDate(post.created_at)}</p>
            </div>
          </div>
          <p className="mt-3 whitespace-pre-line">{post.contenu}</p>

          {/* Images */}
          {post.images && post.images.length > 0 && (
            <div className="mt-3 grid grid-cols-2 gap-2">
              {post.images.map((img: string, i: number) => (
                <img
                  key={i}
                  src={img}
                  alt={`img-${i}`}
                  className="w-full h-40 object-cover rounded"
                />
              ))}
            </div>
          )}

          {/* Métadonnées bien immobilier */}
          {post.metadata && getMetadataDisplay(post.metadata) && (
            <div className="mt-3 p-2 bg-gray-50 rounded border">
              {Object.entries(getMetadataDisplay(post.metadata)!).map(([key, value]) => (
                <div key={key} className="text-sm text-gray-600">
                  <strong>{key}</strong>: {String(value)}
                </div>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center space-x-4 mt-3">
            <button onClick={() => handleLike(post.id)}>
              <Heart
                className={`w-5 h-5 ${
                  post.is_liked ? 'text-red-500 fill-red-500' : 'text-gray-500'
                }`}
              />
            </button>
            <button onClick={() => handleToggleComments(post.id)}>
              <MessageCircle className="w-5 h-5 text-gray-500" />
            </button>
            <button>
              <Share2 className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Stats */}
          <div className="text-sm text-gray-500 mt-1">
            {post.likes_count || 0} j’aime · {post.commentaires_count || 0} commentaire(s)
          </div>

          {/* Commentaires */}
          {expandedComments[post.id] && (
            <div className="mt-3 space-y-3">
              {(comments[post.id] || []).map(comment => (
                <div key={comment.id} className="border-t pt-2">
                  <p className="text-sm">
                    <strong>{comment.auteur_prenom} {comment.auteur_nom}</strong> : {comment.contenu}
                  </p>
                  <p className="text-xs text-gray-400">{formatDate(comment.created_at)}</p>
                </div>
              ))}

              {/* Ajouter un commentaire */}
              <div className="flex items-center space-x-2 pt-2">
                <input
                  type="text"
                  placeholder="Commenter..."
                  value={newComment[post.id] || ''}
                  onChange={(e) => setNewComment(prev => ({ ...prev, [post.id]: e.target.value }))}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddComment(post.id)}
                  className="flex-1 border px-3 py-1 rounded"
                />
                <button
                  onClick={() => handleAddComment(post.id)}
                  className="text-sm text-orange-600 font-medium"
                >
                  Publier
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
