import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { NewsItem } from "@/types/models";

interface Props {
  news: NewsItem[] | undefined;
  isLoading: boolean;
}

function levelVariant(level: string | null) {
  if (level === "政策级") return "destructive" as const;
  if (level === "行业级") return "default" as const;
  return "secondary" as const;
}

export function NewsFeed({ news, isLoading }: Props) {
  if (isLoading) {
    return (
      <Card className="p-4 space-y-3 h-full">
        <h3 className="font-semibold text-sm text-gray-900 dark:text-white mb-2">财经快讯</h3>
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </Card>
    );
  }

  return (
    <Card className="flex flex-col h-full overflow-hidden">
      <div className="p-4 pb-2 shrink-0">
        <h3 className="font-semibold text-sm text-gray-900 dark:text-white flex items-center gap-2">
          财经快讯
          {news && news.length > 0 && (
            <span className="text-xs font-normal text-gray-400">{news.length}条</span>
          )}
        </h3>
      </div>

      {!news || news.length === 0 ? (
        <div className="p-4 pt-0">
          <p className="text-gray-500 dark:text-gray-400 text-sm">暂无新闻</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-1">
          {news.map((item, idx) => {
            const tagVariant = item.sentiment_label === "利好"
              ? "default" as const
              : item.sentiment_label === "利空"
              ? "destructive" as const
              : "secondary" as const;

            return (
              <a
                key={`${item.id}-${idx}`}
                href={item.url || "#"}
                target={item.url ? "_blank" : undefined}
                rel="noopener noreferrer"
                className={`block group border-b border-slate-100 dark:border-slate-800 last:border-0 ${
                  item.is_breaking ? "bg-red-50/50 dark:bg-red-950/20 -mx-2 px-2 rounded" : ""
                }`}
              >
                <div className="py-2.5">
                  {/* 标签行 */}
                  <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                    {item.is_breaking && (
                      <Badge className="text-[10px] px-1.5 py-0 h-4 shrink-0 bg-red-500 hover:bg-red-600">
                        重磅
                      </Badge>
                    )}
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 font-normal text-gray-400 dark:text-gray-500 shrink-0">
                      {item.source}
                    </Badge>
                    {item.sentiment_label !== "中性" && (
                      <Badge variant={tagVariant} className="text-[10px] px-1.5 py-0 h-4 shrink-0">
                        {item.sentiment_label}
                      </Badge>
                    )}
                    {item.impact_level && item.impact_level !== "一般" && (
                      <Badge variant={levelVariant(item.impact_level)} className="text-[10px] px-1.5 py-0 h-4 shrink-0">
                        {item.impact_level}
                      </Badge>
                    )}
                    {item.impact_sectors && (
                      <span className="text-[10px] text-blue-500 dark:text-blue-400">
                        {item.impact_sectors}
                      </span>
                    )}
                  </div>

                  {/* 标题 */}
                  <p className="text-xs leading-relaxed text-gray-700 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400 line-clamp-2">
                    {item.title}
                  </p>

                  {/* 摘要 / 投资解读 */}
                  {item.investment_note && (
                    <p className="text-[10px] text-orange-600 dark:text-orange-400 mt-1 leading-relaxed line-clamp-1">
                      {item.investment_note}
                    </p>
                  )}
                  {!item.investment_note && item.summary && (
                    <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 leading-relaxed line-clamp-1">
                      {item.summary}
                    </p>
                  )}
                </div>
              </a>
            );
          })}
        </div>
      )}
    </Card>
  );
}
