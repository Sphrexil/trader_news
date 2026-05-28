import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { watchlistApi } from "@/api/watchlist";
import type { WatchlistCreate, WatchlistUpdate } from "@/types/models";
import toast from "react-hot-toast";

export function useWatchlist() {
  const qc = useQueryClient();
  const KEY = ["watchlist"];

  const query = useQuery({
    queryKey: KEY,
    queryFn: watchlistApi.getAll,
    staleTime: 30_000,
  });

  const addMutation = useMutation({
    mutationFn: (body: WatchlistCreate) => watchlistApi.add(body),
    onSuccess: () => {
      toast.success("添加成功");
      qc.invalidateQueries({ queryKey: KEY });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: WatchlistUpdate }) =>
      watchlistApi.update(id, body),
    onSuccess: () => {
      toast.success("修改成功");
      qc.invalidateQueries({ queryKey: KEY });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => watchlistApi.remove(id),
    onSuccess: () => {
      toast.success("删除成功");
      qc.invalidateQueries({ queryKey: KEY });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return { ...query, addMutation, updateMutation, deleteMutation };
}
