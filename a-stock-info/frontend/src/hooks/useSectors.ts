import { useQuery } from "@tanstack/react-query";
import { marketApi } from "@/api/market";

export function useSectors(type: string = "industry") {
  return useQuery({
    queryKey: ["market", "sectors", type],
    queryFn: () => marketApi.getSectors(type),
    staleTime: 120_000,
  });
}
