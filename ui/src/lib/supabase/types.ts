export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      events: {
        Row: {
          id: string
          stream_id: string
          timestamp: string
          event_type: string
          payload: Json
          config_hash: string
          created_at: string
        }
        Insert: {
          id?: string
          stream_id: string
          timestamp: string
          event_type: string
          payload: Json
          config_hash: string
          created_at?: string
        }
        Update: {
          id?: string
          stream_id?: string
          timestamp?: string
          event_type?: string
          payload?: Json
          config_hash?: string
          created_at?: string
        }
      }
      trades: {
        Row: {
          id: string
          stream_id: string
          entry_time: string
          exit_time: string | null
          direction: string
          contracts: number
          entry_price: number
          exit_price: number | null
          pnl_usd: number | null
          template_id: string
          euc_score: number
          attribution_code: string | null
          created_at: string
        }
        Insert: {
          id?: string
          stream_id: string
          entry_time: string
          exit_time?: string | null
          direction: string
          contracts: number
          entry_price: number
          exit_price?: number | null
          pnl_usd?: number | null
          template_id: string
          euc_score: number
          attribution_code?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          stream_id?: string
          entry_time?: string
          exit_time?: string | null
          direction?: string
          contracts?: number
          entry_price?: number
          exit_price?: number | null
          pnl_usd?: number | null
          template_id?: string
          euc_score?: number
          attribution_code?: string | null
          created_at?: string
        }
      }
      daily_summary: {
        Row: {
          id: string
          stream_id: string
          date: string
          trades_count: number
          wins: number
          losses: number
          total_pnl: number
          win_rate: number
          avg_win: number
          avg_loss: number
          sharpe_ratio: number | null
          max_drawdown: number | null
          created_at: string
        }
        Insert: {
          id?: string
          stream_id: string
          date: string
          trades_count: number
          wins: number
          losses: number
          total_pnl: number
          win_rate: number
          avg_win: number
          avg_loss: number
          sharpe_ratio?: number | null
          max_drawdown?: number | null
          created_at?: string
        }
        Update: {
          id?: string
          stream_id?: string
          date?: string
          trades_count?: number
          wins?: number
          losses?: number
          total_pnl?: number
          win_rate?: number
          avg_win?: number
          avg_loss?: number
          sharpe_ratio?: number | null
          max_drawdown?: number | null
          created_at?: string
        }
      }
      decision_journal: {
        Row: {
          id: string
          stream_id: string
          timestamp: string
          action: string
          setup_scores: Json
          euc_score: number | null
          reasons: Json
          plain_english: string
          context: Json
          created_at: string
        }
        Insert: {
          id?: string
          stream_id: string
          timestamp: string
          action: string
          setup_scores: Json
          euc_score?: number | null
          reasons: Json
          plain_english: string
          context: Json
          created_at?: string
        }
        Update: {
          id?: string
          stream_id?: string
          timestamp?: string
          action?: string
          setup_scores?: Json
          euc_score?: number | null
          reasons?: Json
          plain_english?: string
          context?: Json
          created_at?: string
        }
      }
      schema_migrations: {
        Row: {
          version: string
          name: string | null
          executed_at: string | null
        }
        Insert: {
          version: string
          name?: string | null
          executed_at?: string | null
        }
        Update: {
          version?: string
          name?: string | null
          executed_at?: string | null
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
  }
}
