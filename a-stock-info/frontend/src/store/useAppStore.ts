import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AppState {
  theme: "light" | "dark";
  colorMode: "red-up-green-down" | "green-up-red-down";
  toggleTheme: () => void;
  setColorMode: (mode: "red-up-green-down" | "green-up-red-down") => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: "light",
      colorMode: "red-up-green-down",
      toggleTheme: () =>
        set((state) => ({ theme: state.theme === "light" ? "dark" : "light" })),
      setColorMode: (mode) => set({ colorMode: mode }),
    }),
    { name: "astock-preferences" },
  ),
);
