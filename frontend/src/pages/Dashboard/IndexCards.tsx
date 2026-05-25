import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAppStore } from "@/store/useAppStore";
import { formatPct, getChangeColorClass } from "@/utils/format";
import type { IndexItem } from "@/types/models";

interface Props {
  indices: IndexItem[] | undefined;
  isLoading: boolean;
}

export function IndexCards({ indices, isLoading }: Props) {
  const colorMode = useAppStore((s) => s.colorMode);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <Skeleton className="h-4 w-16 mb-2" />
              <Skeleton className="h-8 w-24 mb-1" />
              <Skeleton className="h-4 w-20" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!indices || indices.length === 0) {
    return <p className="text-gray-500 dark:text-gray-400 text-sm">暂无指数数据</p>;
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {indices.map((idx) => (
        <Card key={idx.code}>
          <CardContent className="p-4">
            <p className="text-xs text-gray-500 dark:text-gray-400">{idx.name}</p>
            <p className="text-xl font-bold mt-1 text-gray-900 dark:text-white">
              {idx.price?.toFixed(2) ?? "--"}
            </p>
            <p className={`text-sm mt-1 ${getChangeColorClass(idx.pct_chg ?? 0, colorMode)}`}>
              {formatPct(idx.pct_chg)}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
