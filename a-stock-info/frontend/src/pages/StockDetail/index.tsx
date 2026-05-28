import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { KLineChart } from "@/components/charts/KLineChart";
import { useAnnouncements } from "@/hooks/useAnnouncements";
import { useFinancials } from "@/hooks/useFinancials";
import { useKline } from "@/hooks/useKline";
import { useStockQuote } from "@/hooks/useStockQuote";
import { stocksApi } from "@/api/stocks";
import { AnnouncementList } from "./AnnouncementList";
import { FinancialTable } from "./FinancialTable";
import { QuoteHeader } from "./QuoteHeader";
import { Sparkles } from "lucide-react";

interface PredictData {
  predictions: Array<{
    day: number;
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    close_low?: number;
    close_high?: number;
    pct_change: number;
    confidence: number;
  }>;
  backtest?: { avg_error_pct: number | null; direction_accuracy: string };
  p1_meta?: { volatility_label: string; market_label: string; vote_result: string };
  model: string;
  current_price: number;
}

export function StockDetail() {
  const { code } = useParams<{ code: string }>();
  const tsCode = code ?? "";

  const [period, setPeriod] = useState("daily");
  const [adjust, setAdjust] = useState("qfq");
  const [prediction, setPrediction] = useState<PredictData | null>(null);
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictError, setPredictError] = useState("");

  const { data: quote, isLoading: quoteLoading } = useStockQuote(tsCode);
  const { data: kline, isLoading: klineLoading } = useKline(tsCode, period, adjust);
  const { data: financials, isLoading: finLoading } = useFinancials(tsCode);
  const { data: announcements, isLoading: annLoading } = useAnnouncements(tsCode);

  const handlePredict = async () => {
    setPredictLoading(true);
    setPredictError("");
    try {
      const data = await stocksApi.predict(tsCode, 5);
      if ("predictions" in data) {
        setPrediction(data as unknown as PredictData);
      }
    } catch (e) {
      setPredictError(e instanceof Error ? e.message : "预测失败");
    } finally {
      setPredictLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <QuoteHeader quote={quote} isLoading={quoteLoading} />

      <Card className="p-4">
        <div className="flex items-center gap-4 mb-4">
          <Select value={period} onChange={(e) => { setPeriod(e.target.value); setPrediction(null); }} className="w-24">
            <option value="daily">日K</option>
            <option value="weekly">周K</option>
            <option value="monthly">月K</option>
            <option value="1">1分</option>
            <option value="5">5分</option>
            <option value="15">15分</option>
            <option value="30">30分</option>
            <option value="60">60分</option>
          </Select>
          {period === "daily" && (
            <Select value={adjust} onChange={(e) => setAdjust(e.target.value)} className="w-32">
              <option value="qfq">前复权</option>
              <option value="hfq">后复权</option>
              <option value="none">不复权</option>
            </Select>
          )}
          {period === "daily" && (
            <Button
              variant="outline"
              size="sm"
              onClick={handlePredict}
              disabled={predictLoading}
              className="ml-auto gap-1"
            >
              <Sparkles size={14} />
              {predictLoading ? "推演中..." : "AI推演"}
            </Button>
          )}
        </div>

        {prediction?.p1_meta && (
          <div className="mb-1 flex items-center gap-3 text-[11px] text-gray-500 dark:text-gray-400">
            <span>{prediction.p1_meta.volatility_label}</span>
            <span>·</span>
            <span>{prediction.p1_meta.market_label}</span>
            <span>·</span>
            <span>投票: <b className="text-gray-700 dark:text-gray-300">{prediction.p1_meta.vote_result}</b></span>
          </div>
        )}
        {prediction?.backtest && (
          <div className="mb-2 flex items-center gap-3 text-[11px] text-gray-500 dark:text-gray-400">
            <span>回测方向准确率: <b className="text-gray-700 dark:text-gray-300">{prediction.backtest.direction_accuracy}</b></span>
            {prediction.backtest.avg_error_pct != null && (
              <span>平均误差: <b className="text-gray-700 dark:text-gray-300">±{prediction.backtest.avg_error_pct}%</b></span>
            )}
          </div>
        )}
        {predictError && (
          <div className="mb-2 text-xs text-red-500">{predictError}</div>
        )}

        {klineLoading ? (
          <div className="h-[500px] bg-slate-100 dark:bg-slate-800 animate-pulse rounded-md" />
        ) : kline?.items && kline.items.length > 0 ? (
          <KLineChart data={kline.items} prediction={prediction?.predictions ?? undefined} />
        ) : (
          <div className="h-[500px] flex items-center justify-center text-gray-500 dark:text-gray-400">
            暂无K线数据
          </div>
        )}
      </Card>

      <FinancialTable analysis={financials?.analysis} isLoading={finLoading} />
      <AnnouncementList items={announcements?.list} isLoading={annLoading} />
    </div>
  );
}
