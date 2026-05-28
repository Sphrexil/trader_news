/** 获取涨跌对应的颜色值（hex） */
export const getChangeColor = (
  val: number,
  mode: "red-up-green-down" | "green-up-red-down" = "red-up-green-down",
): string => {
  if (!val || val === 0) return "#6b7280";
  if (mode === "red-up-green-down") {
    return val > 0 ? "#ef4444" : "#10b981";
  }
  return val > 0 ? "#10b981" : "#ef4444";
};
