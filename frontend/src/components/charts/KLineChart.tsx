import { useEffect, useRef } from "react";
import { useAppStore } from "@/store/useAppStore";
import type { KlineItem } from "@/types/models";

interface PredictPoint {
  day: number;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface KLineChartProps {
  data: KlineItem[];
  prediction?: PredictPoint[];
}

export function KLineChart({ data, prediction }: KLineChartProps) {
  const { colorMode } = useAppStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<unknown>(null);

  const upColor = colorMode === "red-up-green-down" ? "#ef4444" : "#10b981";
  const downColor = colorMode === "red-up-green-down" ? "#10b981" : "#ef4444";

  useEffect(() => {
    let disposed = false;
    let chart: { setOption: (o: object, n?: object) => void; dispose: () => void; clear: () => void } | null = null;

    import("echarts").then((echarts) => {
      if (disposed || !containerRef.current) return;

      const el = containerRef.current;
      if (!chart) {
        chart = echarts.init(el, undefined, { renderer: "canvas" });
        chartRef.current = chart;
      }

      if (!data || data.length === 0) {
        chart.clear();
        return;
      }

      const isMinute = data.length > 0 && String(data[0].date).includes(" ");

      if (isMinute) {
        // 分时图 — 收盘价折线 + 成交量柱
        const sourceData = data.map((item) => [
          (String(item.date ?? "").split(" ")[1] || item.date) ?? "",
          item.close ?? "-",
          item.vol ?? "-",
        ]);

        const opts: Record<string, unknown> = {
          backgroundColor: "transparent",
          tooltip: { trigger: "axis" },
          dataset: { source: sourceData },
          grid: [
            { left: "5%", right: "5%", top: "5%", height: "60%" },
            { left: "5%", right: "5%", top: "70%", height: "20%" },
          ],
          xAxis: [
            { type: "category", gridIndex: 0 },
            { type: "category", gridIndex: 1, show: false },
          ],
          yAxis: [
            { scale: true, gridIndex: 0 },
            { scale: true, gridIndex: 1, splitNumber: 2 },
          ],
          dataZoom: [
            { type: "inside", xAxisIndex: [0, 1], start: 0, end: 100 },
          ],
          series: [
            {
              type: "line",
              smooth: true,
              encode: { x: 0, y: 1 },
              lineStyle: { color: upColor, width: 1.5 },
              areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{ offset: 0, color: upColor + "30" }, { offset: 1, color: upColor + "05" }] } },
              showSymbol: false,
            },
            {
              type: "bar",
              xAxisIndex: 1, yAxisIndex: 1,
              encode: { x: 0, y: 2 },
              itemStyle: { color: upColor + "60" },
            },
          ],
        };
        chart.setOption(opts);
      } else {
        // 日K — 蜡烛图
        const sourceData = data.map((item) => [
          item.date ?? "",
          item.open ?? "-",
          item.close ?? "-",
          item.low ?? "-",
          item.high ?? "-",
          item.vol ?? "-",
        ]);

        const opts: Record<string, unknown> = {
          backgroundColor: "transparent",
          tooltip: { trigger: "axis" },
          dataset: { source: sourceData },
          grid: [
            { left: "5%", right: "5%", top: "5%", height: "60%" },
            { left: "5%", right: "5%", top: "70%", height: "20%" },
          ],
          xAxis: [
            { type: "category", gridIndex: 0 },
            { type: "category", gridIndex: 1, show: false },
          ],
          yAxis: [
            { scale: true, gridIndex: 0 },
            { scale: true, gridIndex: 1, splitNumber: 2 },
          ],
          dataZoom: [
            { type: "inside", xAxisIndex: [0, 1], start: 50, end: 100 },
          ],
          series: [
            {
              type: "candlestick",
              encode: { x: 0, y: [1, 2, 3, 4] },
              itemStyle: {
                color: upColor, color0: downColor,
                borderColor: upColor, borderColor0: downColor,
              },
            },
            {
              type: "bar",
              xAxisIndex: 1, yAxisIndex: 1,
              encode: { x: 0, y: 5 },
              itemStyle: {
                color: (p: { data: unknown[] }) => {
                  const r = p.data as number[];
                  return r[2] > r[1] ? upColor : downColor;
                },
              },
            },
          ],
        };

        // 预测线叠加（仅日K）
        if (prediction && prediction.length > 0) {
          const predData = prediction.map((p) => [p.date, p.open, p.close, p.low, p.high, 0]);
          opts.dataset = [
            { source: sourceData },
            { source: predData },
          ];
          opts.series.push({
            type: "line",
            name: "AI预测",
            datasetIndex: 1,
            encode: { x: 0, y: 2 },
            lineStyle: { color: "#f59e0b", type: "dashed", width: 2 },
            itemStyle: { color: "#f59e0b" },
            symbol: "diamond",
            symbolSize: 8,
          });
          // 预测区域标注
          opts.markAreas = [
            {
              silent: true,
              label: { show: true, position: "insideTop", color: "#f59e0b", fontSize: 11, formatter: "AI预测" },
              data: [[{ xAxis: prediction[0].date }, { xAxis: prediction[prediction.length - 1].date }]],
              itemStyle: { color: "rgba(245,158,11,0.08)" },
            },
          ];
        }

        chart.setOption(opts);
      }
    });

    return () => {
      disposed = true;
      if (chartRef.current) {
        import("echarts").then((echarts) => {
          const inst = chartRef.current as { isDisposed?: () => boolean; dispose: () => void } | null;
          if (inst && !inst.isDisposed?.()) {
            inst.dispose();
          }
        });
        chartRef.current = null;
      }
    };
  }, [data, prediction, upColor, downColor]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "500px" }}
    />
  );
}
