import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAppStore } from "@/store/useAppStore";
import { formatAmount, formatPct, formatVolume, getChangeColorClass } from "@/utils/format";
import type { Quote } from "@/types/models";
import { Badge } from "@/components/ui/badge";
import { watchlistApi } from "@/api/watchlist";
import { useWatchlist } from "@/hooks/useWatchlist";
import { Star, StarOff } from "lucide-react";
import toast from "react-hot-toast";

interface Props {
  quote: Quote | undefined;
  isLoading: boolean;
}

export function QuoteHeader({ quote, isLoading }: Props) {
  const colorMode = useAppStore((s) => s.colorMode);
  const [adding, setAdding] = useState(false);
  const { data: wlData, deleteMutation } = useWatchlist();

  // 检查是否已在自选中
  const wlEntry = useMemo(() => {
    if (!quote || !wlData?.groups) return null;
    for (const g of wlData.groups) {
      for (const s of g.stocks) {
        if (s.ts_code === quote.ts_code) return s;
      }
    }
    return null;
  }, [quote, wlData]);

  const inWatchlist = !!wlEntry;

  if (isLoading) {
    return (
      <Card className="p-6 space-y-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-10 w-32" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <Skeleton key={i} className="h-6 w-16" />
          ))}
        </div>
      </Card>
    );
  }

  if (!quote) return null;

  const pctClass = getChangeColorClass(quote.pct_chg ?? 0, colorMode);

  const handleAddWatchlist = async () => {
    setAdding(true);
    try {
      await watchlistApi.add({ ts_code: quote.ts_code, group_name: "默认" });
      toast.success(`已添加 ${quote.name} 到自选股`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "添加失败");
    } finally {
      setAdding(false);
    }
  };

  const handleRemoveWatchlist = () => {
    if (!wlEntry) return;
    deleteMutation.mutate(wlEntry.id);
  };

  return (
    <Card className="p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">{quote.name}</h1>
            <span className="text-sm text-gray-500 dark:text-gray-400">{quote.ts_code}</span>
            {quote.is_trading ? (
              <Badge variant="default" className="text-[10px] bg-green-500">交易中</Badge>
            ) : (
              <Badge variant="secondary" className="text-[10px]">已收盘</Badge>
            )}
          </div>
        </div>
        {inWatchlist ? (
          <Button
            variant="destructive"
            size="sm"
            onClick={handleRemoveWatchlist}
            className="gap-1 shrink-0"
          >
            <StarOff size={14} />
            删除自选
          </Button>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={handleAddWatchlist}
            disabled={adding}
            className="gap-1 shrink-0"
          >
            <Star size={14} className={adding ? "animate-pulse" : ""} />
            {adding ? "添加中..." : "加入自选"}
          </Button>
        )}
      </div>

      <div className="flex items-baseline gap-3 mb-4">
        <span className="text-3xl font-bold text-gray-900 dark:text-white">
          {quote.price?.toFixed(2) ?? "--"}
        </span>
        <span className={`text-lg font-semibold ${pctClass}`}>
          {formatPct(quote.pct_chg)}
        </span>
        <span className={`text-sm ${pctClass}`}>
          {quote.change != null ? (quote.change > 0 ? "+" : "") + quote.change.toFixed(2) : "--"}
        </span>
      </div>

      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-4 text-sm">
        <div><p className="text-gray-500 dark:text-gray-400">开盘</p><p className="font-medium text-gray-900 dark:text-white">{quote.open?.toFixed(2) ?? "--"}</p></div>
        <div><p className="text-gray-500 dark:text-gray-400">最高</p><p className="font-medium text-red-500">{quote.high?.toFixed(2) ?? "--"}</p></div>
        <div><p className="text-gray-500 dark:text-gray-400">最低</p><p className="font-medium text-green-500">{quote.low?.toFixed(2) ?? "--"}</p></div>
        <div><p className="text-gray-500 dark:text-gray-400">昨收</p><p className="font-medium text-gray-900 dark:text-white">{quote.pre_close?.toFixed(2) ?? "--"}</p></div>
        <div><p className="text-gray-500 dark:text-gray-400">成交量</p><p className="font-medium text-gray-900 dark:text-white">{formatVolume(quote.vol)}</p></div>
        <div><p className="text-gray-500 dark:text-gray-400">成交额</p><p className="font-medium text-gray-900 dark:text-white">{formatAmount(quote.amount ?? 0)}</p></div>
        <div><p className="text-gray-500 dark:text-gray-400">换手率</p><p className="font-medium text-gray-900 dark:text-white">{formatPct(quote.turnover_rate)}</p></div>
        <div><p className="text-gray-500 dark:text-gray-400">总市值</p><p className="font-medium text-gray-900 dark:text-white">{formatAmount(quote.total_mv ?? 0)}</p></div>
        <div><p className="text-gray-500 dark:text-gray-400">流通市值</p><p className="font-medium text-gray-900 dark:text-white">{formatAmount(quote.circ_mv ?? 0)}</p></div>
      </div>
    </Card>
  );
}
