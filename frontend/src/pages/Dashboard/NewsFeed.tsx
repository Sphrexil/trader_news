import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { NewsItem } from "@/types/models";
import { ExternalLink } from "lucide-react";

interface Props {
  news: NewsItem[] | undefined;
  isLoading: boolean;
}

export function NewsFeed({ news, isLoading }: Props) {
  if (isLoading) {
    return (
      <Card className="p-4 space-y-3">
        <h3 className="font-semibold text-sm text-gray-900 dark:text-white mb-2">最新新闻</h3>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <h3 className="font-semibold text-sm text-gray-900 dark:text-white mb-3">最新新闻</h3>
      {!news || news.length === 0 ? (
        <p className="text-gray-500 dark:text-gray-400 text-sm">暂无新闻</p>
      ) : (
        <div className="space-y-3 max-h-[400px] overflow-y-auto">
          {news.map((item) => (
            <a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block group"
            >
              <div className="flex items-start gap-2">
                <Badge variant="secondary" className="shrink-0 mt-0.5 text-[10px]">
                  {item.source}
                </Badge>
                <span className="text-xs text-gray-700 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400 line-clamp-2 flex-1">
                  {item.title}
                </span>
                <ExternalLink size={12} className="shrink-0 mt-0.5 text-gray-400" />
              </div>
            </a>
          ))}
        </div>
      )}
    </Card>
  );
}
