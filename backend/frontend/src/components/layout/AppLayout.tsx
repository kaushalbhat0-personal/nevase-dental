import type { ReactNode } from "react";
import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import type { User } from "../../types";
import { useAppMode } from "../../contexts/AppModeContext";
import { cn } from "@/lib/utils";

interface AppLayoutProps {
  children: ReactNode;
  user: User | null;
  onLogout: () => void;
}

export default function AppLayout({ children, user, onLogout }: AppLayoutProps) {
  const { resolvedMode } = useAppMode();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleMenuToggle = () => setMobileOpen(true);
  const handleMobileClose = () => setMobileOpen(false);
  const handleToggleCollapse = () => setIsCollapsed(!isCollapsed);

  return (
    <div
      className={cn(
        "flex min-h-screen w-full overflow-y-auto text-foreground",
        resolvedMode === "admin" && "bg-slate-50/80 dark:bg-slate-950/80",
        resolvedMode === "practice" && "bg-background"
      )}
    >
      <div className="hidden flex-shrink-0 self-stretch lg:block">
        <div
          className={`h-full min-h-screen transition-all duration-300 ${isCollapsed ? 'w-20' : 'w-64'}`}
        >
          <Sidebar
            user={user}
            isCollapsed={isCollapsed}
            onToggleCollapse={handleToggleCollapse}
          />
        </div>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
            onClick={handleMobileClose}
            aria-hidden
          />
          <div className="absolute left-0 top-0 h-full w-64 border-r border-border bg-card shadow-2xl animate-in slide-in-from-left duration-300">
            <Sidebar
              user={user}
              onClose={handleMobileClose}
              isCollapsed={false}
              onToggleCollapse={() => {}}
            />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Header user={user} onLogout={onLogout} onMenuToggle={handleMenuToggle} />
        <main
          className={cn(
            "flex-1 p-4 md:p-6 lg:p-8",
            resolvedMode === "admin" && "max-w-7xl mx-auto w-full"
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
