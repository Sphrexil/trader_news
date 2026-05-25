import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { AnnouncementItem } from "@/types/models";
import { AlertTriangle, ArrowDown, ExternalLink, TrendingUp } from "lucide-react";

interface Props {
  items: AnnouncementItem[] | undefined;
  isLoading: boolean;
}

export function AnnouncementList({ items, isLoading }: Props) {
  if (isLoading) {
    return (
      <Card className="p-4">
        <Skeleton className="h-6 w-20 mb-4" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-8 w-full mb-2" />
        ))}
      </Card>
    );
  }

  if (!items || items.length === 0) {
    return (
      <Card className="p-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">公告列表</h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm">暂无公告</p>
      </Card>
    );
  }

  const tagIcon = (tag: string) => {
    switch (tag) {
      case "重大违法": return <AlertTriangle size={10} />;
      case "股东减持": return <ArrowDown size={10} />;
      case "重大利好": return <TrendingUp size={10} />;
      default: return null;
    }
  };

  const tagVariant = (tag: string) => {
    switch (tag) {
      case "重大违法": return "destructive" as const;
      case "股东减持": return "secondary" as const;
      case "重大利好": return "default" as const;
      default: return "outline" as const;
    }
  };

  return (
    <Card>
      <div className="p-4 border-b border-slate-200 dark:border-slate-800">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          公告列表
          <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
            ({items.length}条)
          </span>
        </h2>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>标题</TableHead>
            <TableHead className="w-24">分类</TableHead>
            <TableHead className="w-28">日期</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((a) => (
            <TableRow key={`${a.pub_date}-${a.title.substring(0, 20)}`}>
              <TableCell>
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1 text-sm"
                >
                  {a.title}
                  <ExternalLink size={12} />
                </a>
                {a.classification && a.classification !== "其他公告" && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{a.classification}</p>
                )}
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {a.tags.map((tag) => (
                    <Badge key={tag} variant={tagVariant(tag)} className="text-[10px] gap-0.5">
                      {tagIcon(tag)}
                      {tag}
                    </Badge>
                  ))}
                  {a.tags.length === 0 && (
                    <span className="text-xs text-gray-400">--</span>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-xs text-gray-500 dark:text-gray-400">
                {a.pub_date}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
