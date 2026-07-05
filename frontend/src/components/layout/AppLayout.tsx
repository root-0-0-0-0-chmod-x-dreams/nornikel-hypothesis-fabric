import { type ReactNode, useState, useEffect, useRef } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

interface AppLayoutProps {
  children: ReactNode;
  sidebarContent: ReactNode;
  detailContent?: ReactNode;
  activeTab: "chat" | "documents" | "roadmap";
  onTabChange: (tab: "chat" | "documents" | "roadmap") => void;
  onAddDocument: () => void;
  onSettingsClick: () => void;
}

const MIN_SIDEBAR = 260;
const MAX_SIDEBAR_PCT = 0.35;
const MIN_DETAIL = 320;
const MAX_DETAIL_PCT = 0.45;

function maxSidebar(): number {
  return Math.max(500, Math.round(window.innerWidth * MAX_SIDEBAR_PCT));
}

function maxDetail(): number {
  return Math.max(600, Math.round(window.innerWidth * MAX_DETAIL_PCT));
}

export function AppLayout({
  children,
  sidebarContent,
  detailContent,
  activeTab,
  onTabChange,
  onAddDocument,
  onSettingsClick,
}: AppLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarWidth, setSidebarWidth] = useState(320);
  const [detailWidth, setDetailWidth] = useState(480);
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem("theme");
    if (saved) return saved === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  const draggingSidebar = useRef(false);
  const draggingDetail = useRef(false);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (draggingSidebar.current) {
        setSidebarWidth(Math.min(maxSidebar(), Math.max(MIN_SIDEBAR, e.clientX)));
      }
      if (draggingDetail.current) {
        setDetailWidth(Math.min(maxDetail(), Math.max(MIN_DETAIL, window.innerWidth - e.clientX)));
      }
    };
    const onMouseUp = () => {
      draggingSidebar.current = false;
      draggingDetail.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  return (
    <div className={`h-dvh flex flex-col overflow-hidden ${dark ? "dark" : ""}`}>
      <Header
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        sidebarOpen={sidebarOpen}
        dark={dark}
        onToggleDark={() => setDark(!dark)}
        onSettingsClick={onSettingsClick}
      />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          open={sidebarOpen}
          width={sidebarWidth}
          activeTab={activeTab}
          onTabChange={onTabChange}
          onAddDocument={onAddDocument}
        >
          {sidebarContent}
        </Sidebar>

        {sidebarOpen && (
          <div
            className="w-[3px] cursor-col-resize bg-border hover:bg-accent/40 transition-colors flex-shrink-0 relative group"
            onMouseDown={() => {
              draggingSidebar.current = true;
              document.body.style.cursor = "col-resize";
              document.body.style.userSelect = "none";
            }}
          >
            <div className="absolute inset-y-0 -left-1 -right-1" />
          </div>
        )}

        <main className="flex-1 overflow-hidden flex flex-col min-w-0">{children}</main>

        {detailContent && (
          <>
            <div
              className="w-[3px] cursor-col-resize bg-border hover:bg-accent/40 transition-colors flex-shrink-0 relative group"
              onMouseDown={() => {
                draggingDetail.current = true;
                document.body.style.cursor = "col-resize";
                document.body.style.userSelect = "none";
              }}
            >
              <div className="absolute inset-y-0 -left-1 -right-1" />
            </div>
            <aside
              className="flex-shrink-0 glass-strong border-l border-border flex flex-col overflow-hidden shadow-lg"
              style={{ width: detailWidth }}
            >
              {detailContent}
            </aside>
          </>
        )}
      </div>
    </div>
  );
}
