import { useEffect, useRef } from "react";
import { useAppStore } from "@/store/useAppStore";
import type { KlineItem } from "@/types/models";

interface KLineChartProps {
  data: KlineItem[];
}

export function KLineChart({ data }: KLineChartProps) {
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

      chart.setOption(opts);
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
  }, [data, upColor, downColor]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "500px" }}
    />
  );
}
