"use client";

import { AlertTriangle, RefreshCw, SearchX } from "lucide-react";
import { useEffect, useState } from "react";
import { MetricCard, formatNumber } from "../../components/cards/MetricCard";
import { PageContainer } from "../../components/layout/PageContainer";
import { MatrizSkusSemReposicao } from "../../components/tables/MatrizSkusSemReposicao";
import { api } from "../../services/api";
import type { SkuSemReposicaoResumo, SkuSemReposicaoRow } from "../../types/reposicao";

export default function SKUsMortosPage() {
  const [data, setData] = useState<SkuSemReposicaoRow[]>([]);
  const [resumo, setResumo] = useState<SkuSemReposicaoResumo>({
    total: 0,
    perdidos: 0,
    risco: 0,
    recuperando: 0,
    empresas: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [resumoData, rows] = await Promise.all([
        api.getSkusSemReposicaoResumo(2026),
        api.getSkusSemReposicao(2026, undefined, 1000),
      ]);
      setResumo(resumoData);
      setData(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar SKUs sem reposicao");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <PageContainer
      eyebrow="Ruptura Silenciosa"
      title="SKUs sem Reposicao"
      description="SKUs que tinham necessidade, ficaram abaixo do mínimo e não foram devidamente repostos por empresa."
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

      {loading ? <section className="loadingBand">Carregando SKUs sem reposicao...</section> : null}

      <section className="metricGrid four">
        <MetricCard title="SKUs analisados" value={resumo.total} subtitle="Com necessidade e falta identificada" tone="pink" />
        <MetricCard title="Perdidos" value={resumo.perdidos} subtitle="Venda caiu após ruptura" tone="red" />
        <MetricCard title="Em risco" value={resumo.risco} subtitle="Ainda sem reposição suficiente" tone="amber" />
        <MetricCard title="Empresas" value={resumo.empresas} subtitle="Contextos loja/SKU afetados" tone="gray" />
      </section>

      {!loading && data.length === 0 ? (
        <section className="notice success">
          <SearchX size={20} />
          <span>Nenhum SKU sem reposição encontrado no recorte atual.</span>
        </section>
      ) : null}

      {data.length > 0 ? (
        <section className="panel">
          <div className="panelHeader">
            <div>
              <h2>Matriz de SKUs sem Reposição</h2>
              <p>Regra inicial para estruturar dados. Ainda não é a fórmula definitiva de saúde.</p>
            </div>
            <span className="badge">{data.length} registros</span>
          </div>
          <MatrizSkusSemReposicao data={data} resumo={resumo} />
        </section>
      ) : null}
    </PageContainer>
  );
}
