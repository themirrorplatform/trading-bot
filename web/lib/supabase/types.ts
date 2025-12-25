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
          date: string
          stream_id: string
          starting_equity: number
          ending_equity: number
          pnl_usd: number
          trade_count: number
          win_count: number
          loss_count: number
          max_drawdown: number
          config_hash: string
          created_at: string
        }
        Insert: {
          id?: string
          date: string
          stream_id: string
          starting_equity: number
          ending_equity: number
          pnl_usd: number
          trade_count: number
          win_count: number
          loss_count: number
          max_drawdown: number
          config_hash: string
          created_at?: string
        }
        Update: {
          id?: string
          date?: string
          stream_id?: string
          starting_equity?: number
          ending_equity?: number
          pnl_usd?: number
          trade_count?: number
          win_count?: number
          loss_count?: number
          max_drawdown?: number
          config_hash?: string
          created_at?: string
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
