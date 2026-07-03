import { Beaker, PanelRight, Menu, Sun, Moon } from "lucide-react";
import { Button, Tooltip } from "@/components/ui";

interface HeaderProps {
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
  dark: boolean;
  onToggleDark: () => void;
}

export function Header({ onToggleSidebar, sidebarOpen, dark, onToggleDark }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-4 py-3 glass-strong border-b border-border flex-shrink-0 z-10">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-xl hover:bg-black/5 text-text-muted transition-colors cursor-pointer"
        >
          {sidebarOpen ? <PanelRight size={18} /> : <Menu size={18} />}
        </button>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-accent/90 backdrop-blur-sm flex items-center justify-center shadow-sm">
            <Beaker size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-text leading-tight">Фабрика гипотез</h1>
            <p className="text-[10px] text-text-muted leading-tight">Nornikel R&D</p>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Tooltip content={dark ? "Светлая тема" : "Тёмная тема"}>
          <button
            onClick={onToggleDark}
            className="p-2 rounded-xl hover:bg-black/5 text-text-muted hover:text-accent transition-colors cursor-pointer"
          >
            {dark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </Tooltip>
        <Tooltip content="Экспертная настройка">
          <Button variant="ghost" size="sm">
            Настройки
          </Button>
        </Tooltip>
      </div>
    </header>
  );
}
