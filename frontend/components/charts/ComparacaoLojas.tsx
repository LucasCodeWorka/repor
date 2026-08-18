"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { LojaRankingRow } from "../../types/reposicao";
import { formatNumber } from "../cards/MetricCard";

export function ComparacaoLojas({ data }: { data: LojaRankingRow[] }) {
  const chartData = data.slice(0, 10).map((loja) => ({
    loja: loja.nome_loja.replace("LIEBE", "").trim().slice(0, 18),
    faltou: loja.faltou,
    taxa: loja.taxa_atendimento ?? 0,
  }));

  if (!chartData.length) {
    return <div className="emptyState">Sem lojas para comparar.</div>;
  }

  return (
    <div className="barChart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#edf0f2" strokeDasharray="3 3" />
          <XAxis dataKey="loja" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => formatNumber(Number(value))} width={72} />
          <Tooltip formatter={(value) => formatNumber(Number(value))} />
          <Bar dataKey="faltou" fill="#ef4444" name="Faltou" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
