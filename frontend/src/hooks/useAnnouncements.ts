import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { stocksApi } from "@/api/stocks";

export function useAnnouncements(tsCode: string, page: number = 1, pageSize: number = 20) {
  return useQuery({
    queryKey: ["announcements", tsCode, page, pageSize],
    queryFn: () => stocksApi.getAnnouncements(tsCode, { page, page_size: pageSize }),
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });
}
