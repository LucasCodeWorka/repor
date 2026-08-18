"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { use, useEffect, useState } from "react";
import { MetricCard, formatNumber, formatPercent } from "../../../components/cards/MetricCard";
import { PageContainer } from "../../../components/layout/PageContainer";
import { TabelaLojas } from "../../../components/tables/TabelaLojas";
import { api } from "../../../services/api";
import type { AnaliseLojaMesRow, LojaRankingRow, ResumoGeral } from "../../../types/reposicao";

type MesDetalheProps = {
  params: Promise<{ mes: string }>;
};

export default function MesDetalhePage({ params }: MesDetalheProps) {
  const { mes } = use(params);
  const [resumo, setResumo] = useState<ResumoGeral | null>(null);
  const [rows, setRows] = useState<AnaliseLojaMesRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [resumoData, rowsData] = await Promise.all([
        api.getResumoGeral(2026, mes),
        api.getAnalisePorMes(mes),
      ]);
      setResumo(resumoData);
      setRows(rowsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar mes");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mes]);

  const lojas: LojaRankingRow[] = rows.map((row) => ({
    cd_loja: row.cd_loja,
    nome_loja: row.nome_loja,
    necessidade: row.necessidade_total,
    entrada_total: row.entrada_total,
    faltou: row.faltou,
    taxa_atendimento: row.taxa_atendimento,
    skus_demanda: row.qtd_skus_demanda,
    skus_atendidos: row.skus_atendidos ?? row.skus_ok,
    skus_faltantes: row.skus_faltantes ?? row.skus_parcial + row.skus_zerados,
    skus_entrada_periodo: row.skus_entrada_periodo ?? 0,
    skus_entrada_atrasada: row.skus_entrada_atrasada ?? 0,
    skus_entrada_sem_lote: row.skus_entrada_sem_lote ?? 0,
    skus_zerados: row.skus_zerados,
  }));

  return (
    <PageContainer
      eyebrow="Analise Mensal"
      title={mes}
      description="Detalhamento por loja e tipo de entrada."
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
      <section className="metricGrid">
        <MetricCard title="Necessidade" value={resumo?.necessidade ?? 0} tone="pink" />
        <MetricCard title="Periodo" value={resumo?.entrada_periodo ?? 0} percentage={resumo?.pct_periodo ?? 0} tone="blue" />
        <MetricCard title="Atrasada" value={resumo?.entrada_atrasada ?? 0} percentage={resumo?.pct_atrasada ?? 0} tone="amber" />
        <MetricCard title="Sem Lote" value={resumo?.entrada_sem_lote ?? 0} percentage={resumo?.pct_sem_lote ?? 0} tone="gray" />
        <MetricCard title="Faltou" value={resumo?.faltou ?? 0} subtitle={`Taxa ${formatPercent(resumo?.taxa_atendimento)}`} tone="red" />
      </section>
      <section className="panel">
        <TabelaLojas data={lojas} />
      </section>
      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Entradas por Tipo</h2>
            <p>{loading ? "Carregando..." : `${rows.length} lojas`}</p>
          </div>
        </div>
        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                <th>Loja</th>
                <th>Periodo</th>
                <th>Atrasada</th>
                <th>Sem lote</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.cd_loja}>
                  <td>{row.nome_loja}</td>
                  <td>{formatNumber(row.entrada_periodo)}</td>
                  <td>{formatNumber(row.entrada_atrasada)}</td>
                  <td>{formatNumber(row.entrada_sem_lote)}</td>
                  <td>{formatNumber(row.entrada_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </PageContainer>
  );
}
