"use client";

import { AlertTriangle, CheckCircle2, Database, RefreshCw, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { PageContainer } from "../../components/layout/PageContainer";
import { api } from "../../services/api";

interface CacheStatusData {
  status: string;
  iniciado_em: string | null;
  finalizado_em: string | null;
  erro: string | null;
  cache: {
    atualizado_em: string | null;
    registros_resumo: number;
    primeiro_mes: string | null;
    ultimo_mes: string | null;
  };
}

export default function CachePage() {
  const [cacheStatus, setCacheStatus] = useState<CacheStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function loadStatus() {
    setLoading(true);
    try {
      const status = await api.getCacheStatus();
      setCacheStatus(status as CacheStatusData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar status");
    } finally {
      setLoading(false);
    }
  }

  async function handleAtualizar() {
    setUpdating(true);
    setError(null);
    setSuccess(null);
    try {
      await api.atualizarCache();
      setSuccess("Cache atualizado com sucesso!");
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao atualizar cache");
    } finally {
      setUpdating(false);
    }
  }

  useEffect(() => {
    loadStatus();
  }, []);

  function formatDate(dateStr: string | null) {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString("pt-BR");
  }

  return (
    <PageContainer
      eyebrow="Administracao"
      title="Gerenciamento de Cache"
      description="Controle do cache de dados para otimizar performance das consultas."
    >
      {error ? (
        <section className="notice error">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </section>
      ) : null}

      {success ? (
        <section className="notice success">
          <CheckCircle2 size={20} />
          <span>{success}</span>
        </section>
      ) : null}

      {loading ? (
        <section className="loadingBand">Carregando status do cache...</section>
      ) : null}

      <section className="metricGrid four">
        <article className="metricCard blue">
          <div className="metricCardTop">
            <span>Status</span>
            <div className="metricCardIcon">
              <Database size={18} />
            </div>
          </div>
          <strong style={{ fontSize: 20 }}>
            {cacheStatus?.status === "ok" ? "ATIVO" : cacheStatus?.status?.toUpperCase() || "-"}
          </strong>
        </article>
        <article className="metricCard green">
          <div className="metricCardTop">
            <span>Registros</span>
          </div>
          <strong>{cacheStatus?.cache?.registros_resumo?.toLocaleString("pt-BR") || 0}</strong>
        </article>
        <article className="metricCard pink">
          <div className="metricCardTop">
            <span>Periodo</span>
          </div>
          <strong style={{ fontSize: 18 }}>
            {cacheStatus?.cache?.primeiro_mes || "-"} a {cacheStatus?.cache?.ultimo_mes || "-"}
          </strong>
        </article>
        <article className="metricCard gray">
          <div className="metricCardTop">
            <span>Ultima Atualizacao</span>
          </div>
          <strong style={{ fontSize: 14 }}>
            {formatDate(cacheStatus?.cache?.atualizado_em || null)}
          </strong>
        </article>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Acoes do Cache</h2>
            <p>Atualize o cache quando houver novos dados na base.</p>
          </div>
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          <button
            type="button"
            onClick={handleAtualizar}
            disabled={updating}
            style={{
              minHeight: 44,
              padding: "0 20px",
              background: updating ? "#e5e7eb" : "#be185d",
              color: updating ? "#6b7280" : "#fff",
              border: "none",
              borderRadius: 8,
              fontWeight: 700,
              cursor: updating ? "wait" : "pointer",
            }}
          >
            {updating ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
            {updating ? "Atualizando..." : "Atualizar Cache Completo"}
          </button>

          <button
            type="button"
            onClick={loadStatus}
            disabled={loading}
            style={{
              minHeight: 44,
              padding: "0 20px",
            }}
          >
            <RefreshCw size={17} />
            Verificar Status
          </button>
        </div>

        {cacheStatus?.iniciado_em ? (
          <div className="cacheMeta">
            <p>
              <strong>Iniciado em:</strong> {formatDate(cacheStatus.iniciado_em)}
            </p>
            {cacheStatus.finalizado_em ? (
              <p>
                <strong>Finalizado em:</strong> {formatDate(cacheStatus.finalizado_em)}
              </p>
            ) : null}
            {cacheStatus.erro ? (
              <p style={{ color: "var(--red)" }}>
                <strong>Erro:</strong> {cacheStatus.erro}
              </p>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Sobre o Cache</h2>
            <p>Entenda como funciona o sistema de cache.</p>
          </div>
        </div>

        <div style={{ fontSize: 14, color: "var(--muted)", lineHeight: 1.7 }}>
          <p>
            O cache armazena dados pre-calculados das tabelas de reposicao para acelerar as
            consultas do dashboard. Isso evita recalcular os agregados a cada requisicao.
          </p>
          <br />
          <p>
            <strong>Quando atualizar:</strong>
          </p>
          <ul style={{ marginTop: 8, paddingLeft: 20 }}>
            <li>Apos carregar novos meses na tabela analitica</li>
            <li>Quando houver correcoes nos dados de entrada</li>
            <li>Periodicamente (ex: uma vez por dia)</li>
          </ul>
          <br />
          <p>
            <strong>Tempo estimado:</strong> 15-30 segundos para atualizacao completa.
          </p>
        </div>
      </section>
    </PageContainer>
  );
}
