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
  close_low?: number;
  close_high?: number;
  confidence?: number;
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
          tooltip: {
            trigger: "axis",
            formatter: (params: { name: string; seriesName: string; value: (string | number)[]; marker: string }[]) => {
              if (!params || params.length === 0) return "";
              const row = params[0].value as (string | number)[];
              // 提取 OHLCV (日K: [date, open, close, low, high, vol], 分钟: [time, close, vol])
              const o = Number(row[1] ?? 0), c = Number(row[2] ?? 0);
              const l = Number(row[3] ?? 0), h = Number(row[4] ?? 0);
              const v = Number(row[5] ?? 0);
              const pre = Number(row[6] ?? o);  // 昨收, 用于计算真实涨跌幅
              const pct = pre > 0 ? ((c - pre) / pre * 100) : 0;
              const pctColor = pct >= 0 ? "#ef4444" : "#10b981";
              const pctSign = pct >= 0 ? "+" : "";
              const seriesName = params[0]?.seriesName || "";
              const isPred = seriesName === "AI推演";
              const isMinute = seriesName === "分时线" || seriesName === "成交量";

              let html = `<div style="font-size:12px">`;
              if (isPred) {
                const lowBand = Number(row[7] ?? 0);
                const highBand = Number(row[8] ?? 0);
                const confidence = Number(row[9] ?? 0);
                html += `<div style="font-weight:bold;margin-bottom:4px;color:#f59e0b">${row[0]} (AI推演)</div>`;
                html += `<div>开盘: <b>${o.toFixed(2)}</b></div>`;
                html += `<div>收盘: <b>${c.toFixed(2)}</b></div>`;
                html += `<div>最高: <b style="color:#ef4444">${h.toFixed(2)}</b></div>`;
                html += `<div>最低: <b style="color:#10b981">${l.toFixed(2)}</b></div>`;
                html += `<div>涨跌幅: <b style="color:${pctColor}">${pctSign}${pct.toFixed(2)}%</b></div>`;
                if (lowBand > 0 && highBand > 0) {
                  html += `<div>推演区间: ${lowBand.toFixed(2)} ~ ${highBand.toFixed(2)}</div>`;
                }
                if (confidence > 0) {
                  html += `<div>置信度: ${(confidence * 100).toFixed(0)}%</div>`;
                }
              } else if (isMinute) {
                html += `<div style="font-weight:bold;margin-bottom:4px">${row[0]}</div>`;
                html += `<div>价格: <b>${c.toFixed(2)}</b></div>`;
                html += `<div>量: ${v ? (v/1000000).toFixed(0)+"万手" : "-"}</div>`;
              } else {
                html += `<div style="font-weight:bold;margin-bottom:4px">${row[0]}</div>`;
                html += `<div>开盘: <b>${o.toFixed(2)}</b></div>`;
                html += `<div>收盘: <b>${c.toFixed(2)}</b></div>`;
                html += `<div>最高: <b style="color:#ef4444">${h.toFixed(2)}</b></div>`;
                html += `<div>最低: <b style="color:#10b981">${l.toFixed(2)}</b></div>`;
                html += `<div>涨跌幅: <b style="color:${pctColor}">${pctSign}${pct.toFixed(2)}%</b></div>`;
                html += `<div>成交量: ${v ? (v/1000000).toFixed(0)+"万手" : "-"}</div>`;
              }
              html += `</div>`;
              return html;
            },
          },
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
        // 日K — 蜡烛图 (含前一天收盘价用于计算真实涨跌幅)
        const sourceData = data.map((item, idx) => {
          const preClose = idx > 0 ? data[idx - 1].close : item.open;
          return [
            item.date ?? "",
            item.open ?? "-",
            item.close ?? "-",
            item.low ?? "-",
            item.high ?? "-",
            item.vol ?? "-",
            preClose ?? "-",
          ];
        });

        const opts: Record<string, unknown> = {
          backgroundColor: "transparent",
          tooltip: {
            trigger: "axis",
            formatter: (params: { name: string; seriesName: string; value: (string | number)[]; marker: string }[]) => {
              if (!params || params.length === 0) return "";
              const row = params[0].value as (string | number)[];
              // 提取 OHLCV (日K: [date, open, close, low, high, vol], 分钟: [time, close, vol])
              const o = Number(row[1] ?? 0), c = Number(row[2] ?? 0);
              const l = Number(row[3] ?? 0), h = Number(row[4] ?? 0);
              const v = Number(row[5] ?? 0);
              const pre = Number(row[6] ?? o);  // 昨收, 用于计算真实涨跌幅
              const pct = pre > 0 ? ((c - pre) / pre * 100) : 0;
              const pctColor = pct >= 0 ? "#ef4444" : "#10b981";
              const pctSign = pct >= 0 ? "+" : "";
              const seriesName = params[0]?.seriesName || "";
              const isPred = seriesName === "AI推演";
              const isMinute = seriesName === "分时线" || seriesName === "成交量";

              let html = `<div style="font-size:12px">`;
              if (isPred) {
                const lowBand = Number(row[7] ?? 0);
                const highBand = Number(row[8] ?? 0);
                const confidence = Number(row[9] ?? 0);
                html += `<div style="font-weight:bold;margin-bottom:4px;color:#f59e0b">${row[0]} (AI推演)</div>`;
                html += `<div>开盘: <b>${o.toFixed(2)}</b></div>`;
                html += `<div>收盘: <b>${c.toFixed(2)}</b></div>`;
                html += `<div>最高: <b style="color:#ef4444">${h.toFixed(2)}</b></div>`;
                html += `<div>最低: <b style="color:#10b981">${l.toFixed(2)}</b></div>`;
                html += `<div>涨跌幅: <b style="color:${pctColor}">${pctSign}${pct.toFixed(2)}%</b></div>`;
                if (lowBand > 0 && highBand > 0) {
                  html += `<div>推演区间: ${lowBand.toFixed(2)} ~ ${highBand.toFixed(2)}</div>`;
                }
                if (confidence > 0) {
                  html += `<div>置信度: ${(confidence * 100).toFixed(0)}%</div>`;
                }
              } else if (isMinute) {
                html += `<div style="font-weight:bold;margin-bottom:4px">${row[0]}</div>`;
                html += `<div>价格: <b>${c.toFixed(2)}</b></div>`;
                html += `<div>量: ${v ? (v/1000000).toFixed(0)+"万手" : "-"}</div>`;
              } else {
                html += `<div style="font-weight:bold;margin-bottom:4px">${row[0]}</div>`;
                html += `<div>开盘: <b>${o.toFixed(2)}</b></div>`;
                html += `<div>收盘: <b>${c.toFixed(2)}</b></div>`;
                html += `<div>最高: <b style="color:#ef4444">${h.toFixed(2)}</b></div>`;
                html += `<div>最低: <b style="color:#10b981">${l.toFixed(2)}</b></div>`;
                html += `<div>涨跌幅: <b style="color:${pctColor}">${pctSign}${pct.toFixed(2)}%</b></div>`;
                html += `<div>成交量: ${v ? (v/1000000).toFixed(0)+"万手" : "-"}</div>`;
              }
              html += `</div>`;
              return html;
            },
          },
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

        // 预测柱子叠加（仅日K）
        if (prediction && prediction.length > 0) {
          const categoryDates = [
            ...sourceData.map((row) => row[0]),
            ...prediction.map((p) => p.date),
          ];
          const predData = prediction.map((p, idx) => {
            const preClose = idx > 0 ? prediction[idx - 1].close : p.open;
            return [p.date, p.open, p.close, p.low, p.high, 0, preClose, p.close_low, p.close_high, p.confidence];
          });
          const predBandData = prediction.map((p) => [
            p.date,
            p.close_low ?? p.close,
            Math.max(0, (p.close_high ?? p.close) - (p.close_low ?? p.close)),
          ]);
          opts.dataset = [
            { source: sourceData },
            { source: predData },
            { source: predBandData },
          ];
          (opts.xAxis as Record<string, unknown>[])[0].data = categoryDates;
          (opts.xAxis as Record<string, unknown>[])[1].data = categoryDates;
          (opts.series as Record<string, unknown>[]).push(
            {
              type: "line",
              name: "置信下沿",
              datasetIndex: 2,
              encode: { x: 0, y: 1 },
              lineStyle: { opacity: 0 },
              stack: "confidence-band",
              symbol: "none",
              tooltip: { show: false },
            },
            {
              type: "line",
              name: "推演区间",
              datasetIndex: 2,
              encode: { x: 0, y: 2 },
              lineStyle: { opacity: 0 },
              areaStyle: { color: "rgba(245,158,11,0.14)" },
              stack: "confidence-band",
              symbol: "none",
              tooltip: { show: false },
            },
          );
          // 预测蜡烛柱（正常涨跌色）
          (opts.series as Record<string, unknown>[]).push({
            type: "candlestick",
            name: "AI推演",
            datasetIndex: 1,
            encode: { x: 0, y: [1, 2, 3, 4] },
            itemStyle: {
              color: upColor, color0: downColor,
              borderColor: upColor, borderColor0: downColor,
            },
          });
          // 淡灰色方框 + 标签标注预测区间
          const predStartIdx = sourceData.length;
          const predEndIdx = predStartIdx + prediction.length - 1;
          opts.markAreas = [
            {
              silent: true,
              label: { show: true, position: "insideTop", color: "#94a3b8", fontSize: 10, formatter: "AI推演" },
              itemStyle: { color: "rgba(148,163,184,0.10)" },
              data: [[{ coord: [predStartIdx - 0.5, "min"] }, { coord: [predEndIdx + 0.5, "max"] }]],
            },
          ];
        }

        chart.setOption(opts);
      }
    });

    return () => {
      disposed = true;
      if (chartRef.current) {
        import("echarts").then(() => {
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
