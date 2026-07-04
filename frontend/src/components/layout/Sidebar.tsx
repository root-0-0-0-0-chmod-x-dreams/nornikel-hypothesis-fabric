import { type ReactNode } from "react";
import { Plus, FolderOpen, MessageSquare, Map } from "lucide-react";
import { Button } from "@/components/ui";

interface SidebarProps {
  open: boolean;
  width: number;
  children: ReactNode;
  activeTab: "chat" | "documents" | "roadmap";
  onTabChange: (tab: "chat" | "documents" | "roadmap") => void;
  onAddDocument: () => void;
}

const navItems: { id: "chat" | "documents" | "roadmap"; label: string; icon: typeof MessageSquare }[] = [
  { id: "chat", label: "Чат", icon: MessageSquare },
  { id: "documents", label: "Документы", icon: FolderOpen },
  { id: "roadmap", label: "Роадмапа", icon: Map },
];

export function Sidebar({ open, width, children, activeTab, onTabChange, onAddDocument }: SidebarProps) {
  return (
    <aside
      className="flex-shrink-0 glass-strong border-r border-border flex flex-col overflow-hidden transition-[width] duration-200 z-10"
      style={{ width: open ? width : 0, borderRightWidth: open ? 1 : 0 }}
    >
      <div className="flex flex-col h-full" style={{ width }}>
        <nav className="flex gap-1 p-3 border-b border-border flex-shrink-0">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-xl transition-all duration-200 cursor-pointer whitespace-nowrap
                  ${activeTab === item.id
                    ? "bg-accent-bg text-accent shadow-sm"
                    : "text-text-muted hover:text-text hover:bg-black/5"
                  }`}
              >
                <Icon size={16} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-3">{children}</div>
        <div className="py-4 px-3 border-t border-border flex-shrink-0">
          <Button
            variant="primary"
            size="sm"
            className="w-full"
            icon={<Plus size={14} />}
            onClick={onAddDocument}
          >
            Добавить документ
          </Button>
        </div>
      </div>
    </aside>
  );
}
