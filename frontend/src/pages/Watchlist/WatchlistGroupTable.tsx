import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAppStore } from "@/store/useAppStore";
import { formatPct, getChangeColorClass } from "@/utils/format";
import type { WatchlistGroup } from "@/types/models";
import { Pencil, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface Props {
  group: WatchlistGroup;
  onEdit: (stock: NonNullable<WatchlistGroup["stocks"][number]>) => void;
  onDelete: (stock: NonNullable<WatchlistGroup["stocks"][number]>) => void;
}

export function WatchlistGroupTable({ group, onEdit, onDelete }: Props) {
  const colorMode = useAppStore((s) => s.colorMode);
  const navigate = useNavigate();

  return (
    <Card>
      <div className="p-4 border-b border-slate-200 dark:border-slate-800">
        <h3 className="font-semibold text-gray-900 dark:text-white">
          {group.group_name}
          <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
            ({group.stocks.length}只)
          </span>
        </h3>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>代码</TableHead>
            <TableHead>名称</TableHead>
            <TableHead className="text-right">现价</TableHead>
            <TableHead className="text-right">涨跌幅</TableHead>
            <TableHead className="text-right">成本价</TableHead>
            <TableHead className="text-right">盈亏</TableHead>
            <TableHead>备注</TableHead>
            <TableHead className="w-20">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {group.stocks.map((s) => (
            <TableRow key={s.ts_code}>
              <TableCell className="font-mono text-xs">{s.ts_code}</TableCell>
              <TableCell>
                <button
                  className="text-blue-600 dark:text-blue-400 hover:underline text-sm"
                  onClick={() => navigate(`/stock/${s.ts_code}`)}
                >
                  {s.name}
                </button>
              </TableCell>
              <TableCell className="text-right font-medium">{s.price?.toFixed(2) ?? "--"}</TableCell>
              <TableCell className={`text-right ${getChangeColorClass(s.pct_chg ?? 0, colorMode)}`}>
                {formatPct(s.pct_chg)}
              </TableCell>
              <TableCell className="text-right text-sm">{s.cost_price?.toFixed(2) ?? "--"}</TableCell>
              <TableCell className={`text-right font-medium ${s.pnl_pct ? (s.pnl_pct >= 0 ? "text-red-500" : "text-green-500") : "text-gray-500"}`}>
                {s.pnl_pct != null ? formatPct(s.pnl_pct) : "--"}
              </TableCell>
              <TableCell className="text-xs text-gray-500 dark:text-gray-400 max-w-[100px] truncate">
                {s.note ?? ""}
              </TableCell>
              <TableCell>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(s)}>
                    <Pencil size={14} />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onDelete(s)}>
                    <Trash2 size={14} />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

export function WatchlistTableSkeleton() {
  return (
    <Card className="p-4 space-y-2">
      <Skeleton className="h-5 w-24" />
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </Card>
  );
}
