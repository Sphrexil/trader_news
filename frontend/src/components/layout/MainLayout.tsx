import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { BarChart3, Bell, Search, Settings, Star } from "lucide-react";

const navItems = [
  { to: "/", label: "大盘", icon: BarChart3 },
  { to: "/watchlist", label: "自选", icon: Star },
  { to: "/alerts", label: "告警", icon: Bell },
  { to: "/settings", label: "设置", icon: Settings },
];

export function MainLayout() {
  const [searchCode, setSearchCode] = useState("");
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const code = searchCode.trim();
    if (code) {
      navigate(`/stock/${code}`);
      setSearchCode("");
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-slate-950">
      {/* Sidebar */}
      <aside className="w-16 flex flex-col items-center border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 py-4 gap-2">
        {/* Search */}
        <form onSubmit={handleSearch} className="relative w-10">
          <input
            type="text"
            placeholder="代码"
            value={searchCode}
            onChange={(e) => setSearchCode(e.target.value)}
            className="w-full h-8 px-1 text-[10px] text-center rounded-md border border-slate-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </form>

        {/* Nav */}
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 p-2 rounded-lg text-xs transition-colors ${
                isActive
                  ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950"
                  : "text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-800"
              }`
            }
          >
            <Icon size={20} />
            <span>{label}</span>
          </NavLink>
        ))}
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
