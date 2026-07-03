import { Beaker, PanelRight, Menu } from "lucide-react";
import { Button, Tooltip } from "@/components/ui";

interface HeaderProps {
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
}

export function Header({ onToggleSidebar, sidebarOpen }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-4 py-3 bg-white border-b border-border flex-shrink-0">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-lg hover:bg-gray-100 text-text-muted transition-colors cursor-pointer"
        >
          {sidebarOpen ? <PanelRight size={18} /> : <Menu size={18} />}
        </button>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
            <Beaker size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-text leading-tight">Фабрика гипотез</h1>
            <p className="text-[10px] text-text-muted leading-tight">Nornikel R&D</p>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Tooltip content="Экспертная настройка">
          <Button variant="ghost" size="sm">
            Настройки
          </Button>
        </Tooltip>
      </div>
    </header>
  );
}
