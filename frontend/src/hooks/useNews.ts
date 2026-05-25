import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { newsApi } from "@/api/news";

export function useNews(params?: { ts_code?: string; source?: string; page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ["news", params],
    queryFn: () => newsApi.search(params ?? {}),
    staleTime: 120_000,
    placeholderData: keepPreviousData,
  });
}
