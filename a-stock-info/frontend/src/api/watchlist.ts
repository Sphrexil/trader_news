import type {
  WatchlistCreate,
  WatchlistCreated,
  WatchlistData,
  WatchlistUpdate,
} from "@/types/models";
import client from "./client";

export const watchlistApi = {
  getAll: () => client.get<WatchlistData>("/watchlist"),
  add: (body: WatchlistCreate) => client.post<WatchlistCreated>("/watchlist", body),
  update: (id: number, body: WatchlistUpdate) =>
    client.put<WatchlistCreated>(`/watchlist/${id}`, body),
  remove: (id: number) =>
    client.delete<{ deleted_id: number }>(`/watchlist/${id}`),
};
