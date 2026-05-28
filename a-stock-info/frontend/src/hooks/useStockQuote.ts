import { useQuery } from "@tanstack/react-query";
import { stocksApi } from "@/api/stocks";

export function useStockQuote(tsCode: string) {
  return useQuery({
    queryKey: ["quote", tsCode],
    queryFn: () => stocksApi.getQuote(tsCode),
    refetchInterval: (query) => (query.state.data?.is_trading ? 3000 : false),
    staleTime: 3000,
    refetchOnWindowFocus: true,
  });
}
