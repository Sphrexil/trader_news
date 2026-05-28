import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatAmount, formatPct } from "@/utils/format";
import type { FinancialAnalysis } from "@/types/models";
import { AlertTriangle, TrendingUp } from "lucide-react";

interface Props {
  analysis: FinancialAnalysis | null | undefined;
  isLoading: boolean;
}

export function FinancialTable({ analysis, isLoading }: Props) {
  if (isLoading) {
    return (
      <Card className="p-4">
        <Skeleton className="h-6 w-24 mb-4" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-8 w-full mb-2" />
        ))}
      </Card>
    );
  }

  if (!analysis || !analysis.items || analysis.items.length === 0) {
    return (
      <Card className="p-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">财务数据</h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm">暂无财务数据</p>
      </Card>
    );
  }

  return (
    <Card>
      <div className="p-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">财务数据</h2>
          <Badge variant={analysis.earnings_verdict.includes("超预期") ? "default" : "secondary"}>
            <TrendingUp size={12} className="mr-1" />
            {analysis.earnings_verdict}
          </Badge>
        </div>
        {analysis.latest_summary && (
          <p className="text-sm text-gray-600 dark:text-gray-400">{analysis.latest_summary}</p>
        )}
      </div>

      {analysis.risk_flags.length > 0 && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-950 border-b border-red-200 dark:border-red-900">
          {analysis.risk_flags.map((flag, i) => (
            <div key={i} className="flex items-center gap-1 text-sm text-red-700 dark:text-red-300">
              <AlertTriangle size={14} />
              {flag}
            </div>
          ))}
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>报告期</TableHead>
            <TableHead className="text-right">营收</TableHead>
            <TableHead className="text-right">同比</TableHead>
            <TableHead className="text-right">净利润</TableHead>
            <TableHead className="text-right">同比</TableHead>
            <TableHead className="text-right">EPS</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {analysis.items.map((f) => (
            <TableRow key={f.period}>
              <TableCell className="font-medium">{f.period}</TableCell>
              <TableCell className="text-right">{formatAmount(f.revenue ?? 0)}</TableCell>
              <TableCell className={`text-right ${(f.revenue_yoy ?? 0) >= 0 ? "text-red-500" : "text-green-500"}`}>
                {formatPct(f.revenue_yoy)}
              </TableCell>
              <TableCell className="text-right">{formatAmount(f.net_profit ?? 0)}</TableCell>
              <TableCell className={`text-right ${(f.net_profit_yoy ?? 0) >= 0 ? "text-red-500" : "text-green-500"}`}>
                {formatPct(f.net_profit_yoy)}
              </TableCell>
              <TableCell className="text-right">{f.eps?.toFixed(4) ?? "--"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
