import type {
  AnnouncementItem,
  FinancialData,
  KlineData,
  Quote,
  StockBrief,
  StockInfo,
} from "@/types/models";
import type { PaginatedData } from "@/types/api";
import client from "./client";

export const stocksApi = {
  search: (params: Record<string, unknown>) =>
    client.get<PaginatedData<StockBrief>>("/stocks", { params }),

  getInfo: (tsCode: string) => client.get<StockInfo>(`/stocks/${tsCode}`),

  getQuote: (tsCode: string) => client.get<Quote>(`/stocks/${tsCode}/quote`),

  getKline: (tsCode: string, params: Record<string, unknown>) =>
    client.get<KlineData>(`/stocks/${tsCode}/kline`, { params }),

  getFinancials: (tsCode: string, params: Record<string, unknown>) =>
    client.get<FinancialData>(`/stocks/${tsCode}/financials`, { params }),

  getAnnouncements: (tsCode: string, params: Record<string, unknown>) =>
    client.get<PaginatedData<AnnouncementItem>>(`/stocks/${tsCode}/announcements`, { params }),

  predict: (tsCode: string, days: number = 5) =>
    client.get<{ predictions: Array<{ day: number; date: string; open: number; high: number; low: number; close: number }>; model: string }>(
      `/stocks/${tsCode}/predict?days=${days}`
    ),
};
