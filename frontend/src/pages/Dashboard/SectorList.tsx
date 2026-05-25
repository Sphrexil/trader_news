import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAppStore } from "@/store/useAppStore";
import { formatPct, getChangeColorClass } from "@/utils/format";
import type { SectorItem } from "@/types/models";
import { useNavigate } from "react-router-dom";

interface Props {
  sectors: SectorItem[] | undefined;
  isLoading: boolean;
}

export function SectorList({ sectors, isLoading }: Props) {
  const colorMode = useAppStore((s) => s.colorMode);
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <Card>
        <div className="p-4 space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </Card>
    );
  }

  if (!sectors || sectors.length === 0) {
    return (
      <Card className="p-4">
        <p className="text-gray-500 dark:text-gray-400 text-sm">暂无板块数据</p>
      </Card>
    );
  }

  const top10 = [...sectors].sort((a, b) => Math.abs(b.pct_chg ?? 0) - Math.abs(a.pct_chg ?? 0)).slice(0, 10);

  return (
    <Card>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>板块</TableHead>
            <TableHead className="text-right">涨跌幅</TableHead>
            <TableHead className="text-right">上涨/下跌</TableHead>
            <TableHead>领涨股</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {top10.map((s) => (
            <TableRow key={s.name}>
              <TableCell className="font-medium">{s.name}</TableCell>
              <TableCell className={`text-right ${getChangeColorClass(s.pct_chg ?? 0, colorMode)}`}>
                {formatPct(s.pct_chg)}
              </TableCell>
              <TableCell className="text-right text-xs text-gray-500 dark:text-gray-400">
                <span className="text-red-500">{s.up_count}</span>
                {" / "}
                <span className="text-green-500">{s.down_count}</span>
              </TableCell>
              <TableCell>
                {s.lead_stock ? (
                  <button
                    className="text-blue-600 dark:text-blue-400 text-xs hover:underline"
                    onClick={() => navigate(`/stock/${s.lead_stock!.ts_code}`)}
                  >
                    {s.lead_stock.name}
                    <span className={`ml-1 ${getChangeColorClass(s.lead_stock.pct_chg ?? 0, colorMode)}`}>
                      {formatPct(s.lead_stock.pct_chg)}
                    </span>
                  </button>
                ) : (
                  <span className="text-gray-400 text-xs">--</span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
