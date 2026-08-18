"use client";

import {
  AlertTriangle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Database,
  LayoutDashboard,
  PackageCheck,
  Settings,
  Store,
  TrendingDown,
  Minus,
  Plus,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

// Menu organizado por seções como no Plano de Produção
const menuSections = [
  {
    title: "ESSENCIAIS",
    items: [
      { icon: LayoutDashboard, label: "Dashboard", href: "/" },
      { icon: ClipboardList, label: "Processo", href: "/processo-reposicao" },
      { icon: PackageCheck, label: "Acompanhamento", href: "/acompanhamento" },
      { icon: Store, label: "Lojas", href: "/lojas" },
      { icon: Calendar, label: "Meses", href: "/meses" },
      { icon: AlertTriangle, label: "Alertas", href: "/alertas" },
      { icon: TrendingDown, label: "SKUs sem reposição", href: "/skus-mortos" },
    ],
  },
  {
    title: "CONFIGURAÇÕES",
    items: [
      { icon: Settings, label: "Configurações", href: "/configuracoes" },
      { icon: Database, label: "Admin / Cache", href: "/cache" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [fontScale, setFontScale] = useState(1);
  const [zoomScale, setZoomScale] = useState(1);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const savedFont = Number(window.localStorage.getItem("reposicao_font_scale") || 1);
    const savedZoom = Number(window.localStorage.getItem("reposicao_zoom_scale") || 1);
    setFontScale(Number.isFinite(savedFont) ? Math.max(0.9, Math.min(1.25, savedFont)) : 1);
    setZoomScale(Number.isFinite(savedZoom) ? Math.max(0.9, Math.min(1.15, savedZoom)) : 1);
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.style.fontSize = `${16 * fontScale}px`;
    window.localStorage.setItem("reposicao_font_scale", String(fontScale));
  }, [fontScale]);

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.body.style.zoom = String(zoomScale);
    window.localStorage.setItem("reposicao_zoom_scale", String(zoomScale));
  }, [zoomScale]);

  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebarBrand">
        {!collapsed ? (
          <div>
            <h1>LIEBE</h1>
            <p>REPOSICAO</p>
          </div>
        ) : null}
        <button
          aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
          className="sidebarCollapse"
          onClick={() => setCollapsed((current) => !current)}
          type="button"
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <nav className="sidebarNav" aria-label="Principal">
        {menuSections.map((section) => (
          <div key={section.title} className="sidebarSection">
            {!collapsed ? <span className="sidebarSectionTitle">{section.title}</span> : null}
            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));

              return (
                <Link
                  className={`sidebarLink ${isActive ? "active" : ""}`}
                  href={item.href}
                  key={item.href}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon size={18} />
                  {!collapsed ? <span>{item.label}</span> : null}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Controles de acessibilidade como no Plano de Produção */}
      {!collapsed ? (
      <div className="sidebarAccessibility">
        <span className="sidebarSectionTitle">Acessibilidade</span>
        <div className="accessibilityControl">
          <span>Fonte</span>
          <div className="accessibilityButtons">
            <button onClick={() => setFontScale((current) => Math.max(0.9, Number((current - 0.05).toFixed(2))))}>
              <Minus size={12} />
            </button>
            <span>{Math.round(fontScale * 100)}%</span>
            <button onClick={() => setFontScale((current) => Math.min(1.25, Number((current + 0.05).toFixed(2))))}>
              <Plus size={12} />
            </button>
          </div>
        </div>
        <div className="accessibilityControl">
          <span>Zoom</span>
          <div className="accessibilityButtons">
            <button onClick={() => setZoomScale((current) => Math.max(0.9, Number((current - 0.05).toFixed(2))))}>
              <Minus size={12} />
            </button>
            <span>{Math.round(zoomScale * 100)}%</span>
            <button onClick={() => setZoomScale((current) => Math.min(1.15, Number((current + 0.05).toFixed(2))))}>
              <Plus size={12} />
            </button>
          </div>
        </div>
      </div>
      ) : null}

      {!collapsed ? <div className="sidebarFoot">
        <span>Sistema PCP</span>
        <strong>Reposicao inteligente</strong>
      </div> : null}
    </aside>
  );
}
