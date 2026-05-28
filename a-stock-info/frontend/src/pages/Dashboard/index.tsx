import { useState } from "react";
import { useMarketOverview } from "@/hooks/useMarketOverview";
import { useNews } from "@/hooks/useNews";
import { useSectors } from "@/hooks/useSectors";
import { IndexCards } from "./IndexCards";
import { MarketStats } from "./MarketStats";
import { NewsFeed } from "./NewsFeed";
import { SectorList } from "./SectorList";
import client from "@/api/client";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import toast from "react-hot-toast";

export function Dashboard() {
  const { data: overview, isLoading: overviewLoading, refetch: refetchOverview } = useMarketOverview();
  const { data: sectorsData, isLoading: sectorsLoading, refetch: refetchSectors } = useSectors("industry");
  const { data: newsData, isLoading: newsLoading, refetch: refetchNews } = useNews({ page_size: 30 });
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await client.post<{ results: Record<string, string>; elapsed_seconds: number }>("/system/refresh");
      toast.success(`刷新完成 (${res.elapsed_seconds}s)`);
      // 延迟一下再刷新前端数据，等缓存更新
      setTimeout(() => {
        refetchOverview();
        refetchSectors();
        refetchNews();
      }, 500);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "刷新失败");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">大盘总览</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
          className="gap-1.5"
        >
          <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
          {refreshing ? "刷新中..." : "刷新数据"}
        </Button>
      </div>

      <IndexCards indices={overview?.indices} isLoading={overviewLoading} />

      <MarketStats stats={overview?.market_stats} isLoading={overviewLoading} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SectorList sectors={sectorsData?.items} isLoading={sectorsLoading} />
        </div>
        <div className="lg:row-span-1" style={{ maxHeight: "calc(100vh - 280px)" }}>
          <NewsFeed news={newsData?.list} isLoading={newsLoading} />
        </div>
      </div>
    </div>
  );
}
