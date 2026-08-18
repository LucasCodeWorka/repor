import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Sidebar } from "../components/layout/Sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "LIEBE Reposicao",
  description: "Sistema de inteligencia de reposicao das lojas LIEBE",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>
        <div className="appShell">
          <Sidebar />
          <main className="contentShell">{children}</main>
        </div>
      </body>
    </html>
  );
}
