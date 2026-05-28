import { useQuery } from "@tanstack/react-query";
import { stocksApi } from "@/api/stocks";

export function useKline(tsCode: string, period: string = "daily", adjust: string = "qfq") {
  return useQuery({
    queryKey: ["kline", tsCode, period, adjust],
    queryFn: () => stocksApi.getKline(tsCode, { period, adjust }),
    staleTime: 0,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
  });
}
