import { useAppStore } from "@/store/useAppStore";

export function Settings() {
  const { theme, toggleTheme, colorMode, setColorMode } = useAppStore();

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">系统设置</h1>

      <div className="mt-6 space-y-4 max-w-md">
        {/* 主题切换 */}
        <div className="flex items-center justify-between rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <span className="text-gray-700 dark:text-gray-300">暗黑模式</span>
          <button
            onClick={toggleTheme}
            className="px-4 py-2 rounded-lg bg-blue-500 text-white text-sm hover:bg-blue-600 transition-colors"
          >
            {theme === "light" ? "切换为深色" : "切换为浅色"}
          </button>
        </div>

        {/* 配色模式 */}
        <div className="flex items-center justify-between rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <span className="text-gray-700 dark:text-gray-300">涨跌配色</span>
          <select
            value={colorMode}
            onChange={(e) =>
              setColorMode(e.target.value as "red-up-green-down" | "green-up-red-down")
            }
            className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
          >
            <option value="red-up-green-down">红涨绿跌（A股习惯）</option>
            <option value="green-up-red-down">绿涨红跌（国际习惯）</option>
          </select>
        </div>
      </div>
    </div>
  );
}
