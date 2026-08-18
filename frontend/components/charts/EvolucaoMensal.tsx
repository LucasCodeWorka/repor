"use client";

import {
  CartesianGrid,
  Legend,
  LabelList,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EvolucaoMensalRow } from "../../types/reposicao";
import { formatNumber } from "../cards/MetricCard";

const monthLabels = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

function compact(value: number) {
  if (Math.abs(value) >= 1000) return `${(value / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}k`;
  return formatNumber(value);
}

export function EvolucaoMensal({ data }: { data: EvolucaoMensalRow[] }) {
  const chartData = data.map((item) => ({
    ...item,
    mesLabel: monthLabels[Number(item.mes.slice(5)) - 1] ?? item.mes,
  }));

  if (!chartData.length) {
    return <div className="emptyState">Sem dados mensais para exibir.</div>;
  }

  return (
    <div className="lineChart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 24, right: 18, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#edf0f2" strokeDasharray="3 3" />
          <XAxis dataKey="mesLabel" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => formatNumber(Number(value))} width={72} />
          <Tooltip
            formatter={(value) => formatNumber(Number(value))}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.mes ?? ""}
          />
          <Legend />
          <Line dataKey="necessidade" dot={{ r: 3 }} name="Necessidade" stroke="#B3838C" strokeWidth={2}>
            <LabelList dataKey="necessidade" position="top" formatter={(value: unknown) => compact(Number(value || 0))} fontSize={11} />
          </Line>
          <Line dataKey="entrada_total" dot={{ r: 3 }} name="Entrada total" stroke="#168057" strokeWidth={2}>
            <LabelList dataKey="entrada_total" position="top" formatter={(value: unknown) => compact(Number(value || 0))} fontSize={11} />
          </Line>
          <Line dataKey="faltou" dot={{ r: 3 }} name="Faltou" stroke="#C2413A" strokeWidth={2}>
            <LabelList dataKey="faltou" position="bottom" formatter={(value: unknown) => compact(Number(value || 0))} fontSize={11} />
          </Line>
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
