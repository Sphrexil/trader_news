import { useQuery } from "@tanstack/react-query";
import { stocksApi } from "@/api/stocks";

export function useFinancials(tsCode: string, reportType: string = "Q", limit: number = 12) {
  return useQuery({
    queryKey: ["financials", tsCode, reportType, limit],
    queryFn: () => stocksApi.getFinancials(tsCode, { report_type: reportType, limit }),
    staleTime: 5 * 60_000,
  });
}
