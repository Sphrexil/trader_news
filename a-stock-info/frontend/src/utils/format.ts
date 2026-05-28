/** 涨跌幅格式化，带正负号 */
export const formatPct = (val: number | null | undefined): string => {
  if (val == null) return "--";
  return val > 0 ? `+${val.toFixed(2)}%` : `${val.toFixed(2)}%`;
};

/** 提取涨跌颜色 CSS 类名 (适配 Tailwind) */
export const getChangeColorClass = (
  val: number,
  mode: "red-up-green-down" | "green-up-red-down" = "red-up-green-down",
): string => {
  if (!val || val === 0) return "text-gray-500 dark:text-gray-400";
  if (mode === "red-up-green-down") {
    return val > 0 ? "text-red-500" : "text-green-500";
  }
  return val > 0 ? "text-green-500" : "text-red-500";
};

/** 大额数字格式化：万、亿 */
export const formatAmount = (val: number): string => {
  if (!val) return "--";
  if (val >= 100000000) return `${(val / 100000000).toFixed(2)}亿`;
  if (val >= 10000) return `${(val / 10000).toFixed(2)}万`;
  return val.toFixed(2);
};

/** 成交量格式化：输入股数，输出 手/万手/亿手 */
export const formatVolume = (val: number | null | undefined): string => {
  if (val == null || val === 0) return "--";
  const hands = val / 100; // 股 → 手
  if (hands >= 100000000) return `${(hands / 100000000).toFixed(2)}亿手`;
  if (hands >= 10000) return `${(hands / 10000).toFixed(0)}万手`;
  return `${Math.round(hands)}手`;
};
