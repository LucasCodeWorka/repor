"use client";

import Link from "next/link";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { MetricCard, formatNumber, formatPercent } from "../../components/cards/MetricCard";
import { EvolucaoMensal } from "../../components/charts/EvolucaoMensal";
import { PageContainer } from "../../components/layout/PageContainer";
import { api } from "../../services/api";
import type { EvolucaoMensalRow } from "../../types/reposicao";

export default function MesesPage() {
  const [rows, setRows] = useState<EvolucaoMensalRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      setRows(await api.getEvolucaoMensal(2026));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar meses");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <PageContainer
      eyebrow="Meses"
      title="Evolucao Mensal"
      description="Compare necessidade, entrada e falta por mes de reposicao."
      actions={
        <button type="button" onClick={loadData} disabled={loading}>
          <RefreshCw size={17} />
          Atualizar
        </button>
      }
    >
      {error ? (
        <section className="notice error">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </section>
      ) : null}
      <section className="panel">
        <EvolucaoMensal data={rows} />
      </section>
      <section className="monthCardGrid">
        {rows.map((row) => (
          <Link className="monthCard" href={`/meses/${row.mes}`} key={row.mes}>
            <MetricCard
              title={row.mes}
              value={formatNumber(row.necessidade)}
              subtitle={`Faltou ${formatNumber(row.faltou)} | Taxa ${formatPercent(row.taxa_atendimento)}`}
              tone={(row.taxa_atendimento ?? 0) >= 100 ? "green" : "red"}
            />
          </Link>
        ))}
      </section>
    </PageContainer>
  );
}
