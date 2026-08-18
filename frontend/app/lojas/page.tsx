"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { ComparacaoLojas } from "../../components/charts/ComparacaoLojas";
import { PageContainer } from "../../components/layout/PageContainer";
import { TabelaLojas } from "../../components/tables/TabelaLojas";
import { api } from "../../services/api";
import type { LojaRankingRow } from "../../types/reposicao";

export default function LojasPage() {
  const [month, setMonth] = useState("2026-06");
  const [lojas, setLojas] = useState<LojaRankingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData(selectedMonth = month) {
    setLoading(true);
    setError(null);
    try {
      setLojas(await api.getLojasRanking(2026, selectedMonth, 100));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar lojas");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <PageContainer
      eyebrow="Lojas"
      title="Atendimento por Loja"
      description="Priorize lojas com baixa taxa de atendimento e alto volume faltante."
      actions={
        <>
          <select
            value={month}
            onChange={(event) => {
              setMonth(event.target.value);
              loadData(event.target.value);
            }}
          >
            {["2026-06", "2026-07", "2026-08", "2026-05", "2026-04", "2026-03"].map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <button type="button" onClick={() => loadData()} disabled={loading}>
            <RefreshCw size={17} />
            Atualizar
          </button>
        </>
      }
    >
      {error ? (
        <section className="notice error">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </section>
      ) : null}
      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Maiores Faltas</h2>
            <p>{loading ? "Carregando..." : `${lojas.length} lojas encontradas`}</p>
          </div>
        </div>
        <ComparacaoLojas data={lojas} />
      </section>
      <section className="panel">
        <TabelaLojas data={lojas} />
      </section>
    </PageContainer>
  );
}
