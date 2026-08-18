"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { use, useEffect, useState } from "react";
import { MetricCard, formatNumber, formatPercent } from "../../../components/cards/MetricCard";
import { EvolucaoMensal } from "../../../components/charts/EvolucaoMensal";
import { PageContainer } from "../../../components/layout/PageContainer";
import { api } from "../../../services/api";
import type { AnaliseLojaMesRow, EvolucaoMensalRow } from "../../../types/reposicao";

type LojaDetalheProps = {
  params: Promise<{ id: string }>;
};

export default function LojaDetalhePage({ params }: LojaDetalheProps) {
  const { id } = use(params);
  const cdLoja = Number(id);
  const [rows, setRows] = useState<AnaliseLojaMesRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      setRows(await api.getAnalisePorLoja(cdLoja, 2026));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar loja");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cdLoja]);

  const latest = rows[rows.length - 1];
  const chartData: EvolucaoMensalRow[] = rows.map((row) => ({
    mes: row.mes,
    necessidade: row.necessidade_total,
    entrada_periodo: row.entrada_periodo,
    entrada_atrasada: row.entrada_atrasada,
    entrada_sem_lote: row.entrada_sem_lote,
    entrada_total: row.entrada_total,
    faltou: row.faltou,
    skus_demanda: row.qtd_skus_demanda,
    skus_atendidos: row.skus_atendidos ?? row.skus_ok,
    skus_faltantes: row.skus_faltantes ?? row.skus_parcial + row.skus_zerados,
    taxa_atendimento: row.taxa_atendimento,
  }));

  return (
    <PageContainer
      eyebrow="Detalhe da Loja"
      title={latest?.nome_loja ?? `Loja ${cdLoja}`}
      description="Evolucao mensal da necessidade, entrada e falta."
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
      <section className="metricGrid four">
        <MetricCard title="Necessidade" value={latest?.necessidade_total ?? 0} tone="pink" />
        <MetricCard title="Entrada Total" value={latest?.entrada_total ?? 0} tone="green" />
        <MetricCard title="Faltou" value={latest?.faltou ?? 0} tone="red" />
        <MetricCard title="Taxa" value={formatPercent(latest?.taxa_atendimento)} tone="blue" />
      </section>
      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Evolucao da Loja</h2>
            <p>{loading ? "Carregando..." : `${rows.length} meses analisados`}</p>
          </div>
        </div>
        <EvolucaoMensal data={chartData} />
      </section>
      <section className="panel">
        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                <th>Mes</th>
                <th>Necessidade</th>
                <th>Periodo</th>
                <th>Atrasada</th>
                <th>Sem lote</th>
                <th>Faltou</th>
                <th>Taxa</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.mes}>
                  <td>{row.mes}</td>
                  <td>{formatNumber(row.necessidade_total)}</td>
                  <td>{formatNumber(row.entrada_periodo)}</td>
                  <td>{formatNumber(row.entrada_atrasada)}</td>
                  <td>{formatNumber(row.entrada_sem_lote)}</td>
                  <td className="bad">{formatNumber(row.faltou)}</td>
                  <td>{formatPercent(row.taxa_atendimento)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </PageContainer>
  );
}
