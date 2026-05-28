import { useMarketOverview } from "@/hooks/useMarketOverview";
import { useNews } from "@/hooks/useNews";
import { useSectors } from "@/hooks/useSectors";
import { IndexCards } from "./IndexCards";
import { MarketStats } from "./MarketStats";
import { NewsFeed } from "./NewsFeed";
import { SectorList } from "./SectorList";

export function Dashboard() {
  const { data: overview, isLoading: overviewLoading } = useMarketOverview();
  const { data: sectorsData, isLoading: sectorsLoading } = useSectors("industry");
  const { data: newsData, isLoading: newsLoading } = useNews({ page_size: 10 });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">大盘总览</h1>

      <IndexCards indices={overview?.indices} isLoading={overviewLoading} />

      <MarketStats stats={overview?.market_stats} isLoading={overviewLoading} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SectorList sectors={sectorsData?.items} isLoading={sectorsLoading} />
        </div>
        <div>
          <NewsFeed news={newsData?.list} isLoading={newsLoading} />
        </div>
      </div>
    </div>
  );
}
