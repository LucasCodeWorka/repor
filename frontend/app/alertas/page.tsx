"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { StatusBadge } from "../../components/cards/StatusBadge";
import { PageContainer } from "../../components/layout/PageContainer";
import { api } from "../../services/api";
import type { Alerta } from "../../types/reposicao";

export default function AlertasPage() {
  const [month, setMonth] = useState("2026-06");
  const [tipo, setTipo] = useState("TODOS");
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData(selectedMonth = month) {
    setLoading(true);
    setError(null);
    try {
      setAlertas(await api.getAlertas(selectedMonth));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar alertas");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(
    () => (tipo === "TODOS" ? alertas : alertas.filter((alerta) => alerta.tipo === tipo)),
    [alertas, tipo],
  );

  const tipos = ["TODOS", ...Array.from(new Set(alertas.map((alerta) => alerta.tipo)))];

  return (
    <PageContainer
      eyebrow="Alertas"
      title="Ruptura e Morte Silenciosa"
      description="Sinais automaticos de loja critica, curva A zerada e referencias morrendo."
      actions={
        <>
          <select
            value={month}
            onChange={(event) => {
              setMonth(event.target.value);
              loadData(event.target.value);
            }}
          >
            {["2026-06", "2026-07", "2026-08", "2026-05"].map((item) => (
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
      <section className="filterBar">
        {tipos.map((item) => (
          <button className={tipo === item ? "selected" : ""} key={item} type="button" onClick={() => setTipo(item)}>
            {item.replaceAll("_", " ")}
          </button>
        ))}
      </section>
      <section className="alertGrid">
        {filtered.map((alerta, index) => (
          <article className={`alertCard ${alerta.severidade}`} key={`${alerta.tipo}-${index}`}>
            <div>
              <StatusBadge value={alerta.severidade} />
              <strong>{alerta.tipo.replaceAll("_", " ")}</strong>
            </div>
            <p>{alerta.mensagem}</p>
          </article>
        ))}
        {!filtered.length ? <div className="emptyState">Nenhum alerta para o filtro selecionado.</div> : null}
      </section>
    </PageContainer>
  );
}
