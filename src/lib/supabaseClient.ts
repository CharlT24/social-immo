import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseKey)

// Types pour TypeScript
export type Database = {
  public: {
    Tables: {
      posts: {
        Row: {
          id: string
          content: string
          user_id: string
          created_at: string
          likes_count?: number
          comments_count?: number
        }
        Insert: {
          content: string
          user_id: string
        }
        Update: {
          content?: string
          likes_count?: number
          comments_count?: number
        }
      }
      messages: {
        Row: {
          id: string
          content: string
          user_id: string
          chat_id: string
          created_at: string
        }
        Insert: {
          content: string
          user_id: string
          chat_id: string
        }
        Update: {
          content?: string
        }
      }
      friends: {
        Row: {
          id: string
          user_id: string
          friend_id: string
          status: 'pending' | 'accepted' | 'blocked'
          created_at: string
        }
        Insert: {
          user_id: string
          friend_id: string
          status?: 'pending' | 'accepted' | 'blocked'
        }
        Update: {
          status?: 'pending' | 'accepted' | 'blocked'
        }
      }
    }
  }
}
