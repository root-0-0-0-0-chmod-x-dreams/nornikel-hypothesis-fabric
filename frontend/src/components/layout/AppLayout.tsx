import { type ReactNode, useState, useRef, useCallback, useEffect } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

interface AppLayoutProps {
  children: ReactNode;
  sidebarContent: ReactNode;
  detailContent?: ReactNode;
  activeTab: "chat" | "documents" | "roadmap";
  onTabChange: (tab: "chat" | "documents" | "roadmap") => void;
  onAddDocument: () => void;
}

const MIN_SIDEBAR = 260;
const MAX_SIDEBAR = 500;
const MIN_DETAIL = 320;
const MAX_DETAIL = 600;

export function AppLayout({
  children,
  sidebarContent,
  detailContent,
  activeTab,
  onTabChange,
  onAddDocument,
}: AppLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarWidth, setSidebarWidth] = useState(320);
  const [detailWidth, setDetailWidth] = useState(480);

  const draggingSidebar = useRef(false);
  const draggingDetail = useRef(false);

  const onMouseMove = useCallback((e: MouseEvent) => {
    if (draggingSidebar.current) {
      setSidebarWidth(Math.min(MAX_SIDEBAR, Math.max(MIN_SIDEBAR, e.clientX)));
    }
    if (draggingDetail.current) {
      setDetailWidth(Math.min(MAX_DETAIL, Math.max(MIN_DETAIL, window.innerWidth - e.clientX)));
    }
  }, []);

  const onMouseUp = useCallback(() => {
    draggingSidebar.current = false;
    draggingDetail.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, [onMouseMove, onMouseUp]);

  const startResizeSidebar = () => {
    draggingSidebar.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  const startResizeDetail = () => {
    draggingDetail.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  return (
    <div className="h-dvh flex flex-col overflow-hidden">
      <Header
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        sidebarOpen={sidebarOpen}
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
            className="w-1 cursor-col-resize bg-border hover:bg-accent/50 transition-colors flex-shrink-0 relative group"
            onMouseDown={startResizeSidebar}
          >
            <div className="absolute inset-y-0 -left-1 -right-1" />
          </div>
        )}

        <main className="flex-1 overflow-hidden flex flex-col min-w-0">{children}</main>

        {detailContent && (
          <>
            <div
              className="w-1 cursor-col-resize bg-border hover:bg-accent/50 transition-colors flex-shrink-0 relative group"
              onMouseDown={startResizeDetail}
            >
              <div className="absolute inset-y-0 -left-1 -right-1" />
            </div>
            <aside
              className="flex-shrink-0 bg-white border-l border-border flex flex-col overflow-hidden"
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
