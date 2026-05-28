import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAppStore } from "@/store/useAppStore";
import { formatAmount } from "@/utils/format";
import type { MarketStats as MarketStatsType } from "@/types/models";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";

interface Props {
  stats: MarketStatsType | undefined;
  isLoading: boolean;
}

export function MarketStats({ stats, isLoading }: Props) {
  const colorMode = useAppStore((s) => s.colorMode);

  if (isLoading) {
    return (
      <Card className="p-4">
        <div className="flex gap-6">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-6 w-20" />
          ))}
        </div>
      </Card>
    );
  }

  if (!stats) return null;

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <span className="flex items-center gap-1 text-red-500">
          <ArrowUp size={14} /> {stats.up_count} 涨
        </span>
        <span className="flex items-center gap-1 text-green-500">
          <ArrowDown size={14} /> {stats.down_count} 跌
        </span>
        <span className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
          <Minus size={14} /> {stats.flat_count} 平
        </span>
        <Badge variant="destructive" className="text-xs">{stats.limit_up} 涨停</Badge>
        <Badge variant="secondary" className="text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">{stats.limit_down} 跌停</Badge>
        <span className="text-gray-500 dark:text-gray-400">
          成交额 {formatAmount(stats.total_amount ?? 0)}
        </span>
      </div>
    </Card>
  );
}
