import { useState } from "react";
import { useParams } from "react-router-dom";
import { Select } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { KLineChart } from "@/components/charts/KLineChart";
import { useAnnouncements } from "@/hooks/useAnnouncements";
import { useFinancials } from "@/hooks/useFinancials";
import { useKline } from "@/hooks/useKline";
import { useStockQuote } from "@/hooks/useStockQuote";
import { AnnouncementList } from "./AnnouncementList";
import { FinancialTable } from "./FinancialTable";
import { QuoteHeader } from "./QuoteHeader";

export function StockDetail() {
  const { code } = useParams<{ code: string }>();
  const tsCode = code ?? "";

  const [period, setPeriod] = useState("daily");
  const [adjust, setAdjust] = useState("qfq");

  const { data: quote, isLoading: quoteLoading } = useStockQuote(tsCode);
  const { data: kline, isLoading: klineLoading } = useKline(tsCode, period, adjust);
  const { data: financials, isLoading: finLoading } = useFinancials(tsCode);
  const { data: announcements, isLoading: annLoading } = useAnnouncements(tsCode);

  return (
    <div className="p-6 space-y-6">
      <QuoteHeader quote={quote} isLoading={quoteLoading} />

      <Card className="p-4">
        <div className="flex items-center gap-4 mb-4">
          <Select value={period} onChange={(e) => setPeriod(e.target.value)} className="w-24">
            <option value="daily">日K</option>
            <option value="weekly">周K</option>
            <option value="monthly">月K</option>
          </Select>
          <Select value={adjust} onChange={(e) => setAdjust(e.target.value)} className="w-32">
            <option value="qfq">前复权</option>
            <option value="hfq">后复权</option>
            <option value="none">不复权</option>
          </Select>
        </div>
        {klineLoading ? (
          <div className="h-[500px] bg-slate-100 dark:bg-slate-800 animate-pulse rounded-md" />
        ) : kline?.items && kline.items.length > 0 ? (
          <KLineChart data={kline.items} />
        ) : (
          <div className="h-[500px] flex items-center justify-center text-gray-500 dark:text-gray-400">
            暂无K线数据
          </div>
        )}
      </Card>

      <FinancialTable
        analysis={financials?.analysis}
        isLoading={finLoading}
      />

      <AnnouncementList
        items={announcements?.list}
        isLoading={annLoading}
      />
    </div>
  );
}
