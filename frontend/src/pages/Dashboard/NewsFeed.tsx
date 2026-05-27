import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { NewsItem } from "@/types/models";

interface Props {
  news: NewsItem[] | undefined;
  isLoading: boolean;
}

export function NewsFeed({ news, isLoading }: Props) {
  if (isLoading) {
    return (
      <Card className="p-4 space-y-3 h-full">
        <h3 className="font-semibold text-sm text-gray-900 dark:text-white mb-2">财经快讯</h3>
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-14 w-full" />
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
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block group border-b border-slate-100 dark:border-slate-800 last:border-0"
              >
                <div className="py-2.5">
                  {/* 标签行 */}
                  <div className="flex items-center gap-1.5 mb-1">
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 font-normal text-gray-400 dark:text-gray-500 shrink-0">
                      {item.source}
                    </Badge>
                    {item.sentiment_label !== "中性" && (
                      <Badge variant={tagVariant} className="text-[10px] px-1.5 py-0 h-4 shrink-0">
                        {item.sentiment_label}
                      </Badge>
                    )}
                  </div>

                  {/* 标题 */}
                  <p className="text-xs leading-relaxed text-gray-700 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400 line-clamp-2">
                    {item.title}
                  </p>

                  {/* 匹配关键词 */}
                  {(item.positive_matches?.length > 0 || item.negative_matches?.length > 0) && (
                    <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5 truncate">
                      {[...(item.positive_matches || []), ...(item.negative_matches || [])].slice(0, 4).join(" · ")}
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
