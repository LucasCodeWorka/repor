import type { ReactNode } from "react";

type MetricTone = "pink" | "blue" | "amber" | "gray" | "green" | "red";

type MetricCardProps = {
  title: string;
  value: number | string;
  subtitle?: string;
  tone: MetricTone;
  percentage?: number;
  icon?: ReactNode;
};

export function formatNumber(value: number | null | undefined) {
  return Math.round(value ?? 0).toLocaleString("pt-BR");
}

export function formatPercent(value: number | null | undefined) {
  return `${(value ?? 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`;
}

export function MetricCard({ title, value, subtitle, tone, percentage, icon }: MetricCardProps) {
  return (
    <article className={`metricCard ${tone}`}>
      <div className="metricCardTop">
        <span>{title}</span>
        {icon ? <div className="metricCardIcon">{icon}</div> : null}
      </div>
      <strong>{typeof value === "number" ? formatNumber(value) : value}</strong>
      {subtitle ? <p>{subtitle}</p> : null}
      {percentage !== undefined ? <em>{formatPercent(percentage)} do total</em> : null}
    </article>
  );
}
