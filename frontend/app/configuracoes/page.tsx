"use client";

import { AlertTriangle, RefreshCw, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { MetricCard } from "../../components/cards/MetricCard";
import { PageContainer } from "../../components/layout/PageContainer";
import { api } from "../../services/api";
import type { CacheStatus, ConfigReposicao } from "../../types/reposicao";

// Meses disponiveis para selecao
const MESES_DISPONIVEIS = [
  "2026-01", "2026-02", "2026-03", "2026-04",
  "2026-05", "2026-06", "2026-07", "2026-08",
];

const LABELS_MESES: Record<string, string> = {
  "2026-01": "Janeiro",
  "2026-02": "Fevereiro",
  "2026-03": "Marco",
  "2026-04": "Abril",
  "2026-05": "Maio",
  "2026-06": "Junho",
  "2026-07": "Julho",
  "2026-08": "Agosto",
};

export default function ConfiguracoesPage() {
  const [config, setConfig] = useState<ConfigReposicao>({
    meses_media: 3,
    multiplicador_estoque_minimo: 1.5,
    multiplicador_curva_aa: 1.5,
    multiplicador_curva_a: 1.5,
    multiplicador_curva_b: 1.0,
    multiplicador_curva_c: 1.0,
    modo_meses: "ultimos_3",
    meses_selecionados: ["2026-05", "2026-06", "2026-07"],
  });
  const [cache, setCache] = useState<CacheStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadData() {
    setBusy(true);
    setError(null);
    try {
      const [configData, cacheData] = await Promise.all([api.getConfig(), api.getCacheStatus()]);
      setConfig(configData);
      setCache(cacheData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar configuracoes");
    } finally {
      setBusy(false);
    }
  }

  async function saveConfig() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setConfig(await api.salvarConfig(config));
      setMessage("Configuracoes salvas.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar configuracoes");
    } finally {
      setBusy(false);
    }
  }

  async function refreshCache() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.atualizarCache();
      setCache(await api.getCacheStatus());
      setMessage("Cache atualizado.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao atualizar cache");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <PageContainer
      eyebrow="Configuracoes"
      title="Parametros e Cache"
      description="Controle do calculo de media e materializacao dos dados de reposicao."
      actions={
        <button type="button" onClick={loadData} disabled={busy}>
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
      {message ? <section className="notice success">{message}</section> : null}

      {/* Selecao de Meses */}
      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Selecao de Meses para Media</h2>
            <p>Escolha quais meses usar no calculo da media de vendas.</p>
          </div>
        </div>

        <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="radio"
              name="modo_meses"
              checked={config.modo_meses === "ultimos_3"}
              onChange={() => setConfig((c) => ({ ...c, modo_meses: "ultimos_3", meses_media: 3 }))}
            />
            <span>Ultimos 3 meses</span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="radio"
              name="modo_meses"
              checked={config.modo_meses === "ultimos_6"}
              onChange={() => setConfig((c) => ({ ...c, modo_meses: "ultimos_6", meses_media: 6 }))}
            />
            <span>Ultimos 6 meses</span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="radio"
              name="modo_meses"
              checked={config.modo_meses === "customizado"}
              onChange={() => setConfig((c) => ({ ...c, modo_meses: "customizado" }))}
            />
            <span>Customizado</span>
          </label>
        </div>

        {config.modo_meses === "customizado" && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 16 }}>
            {MESES_DISPONIVEIS.map((mes) => (
              <label
                key={mes}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "8px 12px",
                  background: config.meses_selecionados?.includes(mes) ? "var(--card-pink)" : "#f5f5f5",
                  border: config.meses_selecionados?.includes(mes) ? "2px solid var(--liebe-primary)" : "2px solid transparent",
                  borderRadius: 8,
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={config.meses_selecionados?.includes(mes) ?? false}
                  onChange={(e) => {
                    const selected = config.meses_selecionados ?? [];
                    if (e.target.checked) {
                      setConfig((c) => ({ ...c, meses_selecionados: [...selected, mes], meses_media: selected.length + 1 }));
                    } else {
                      setConfig((c) => ({ ...c, meses_selecionados: selected.filter((m) => m !== mes), meses_media: Math.max(1, selected.length - 1) }));
                    }
                  }}
                />
                <span style={{ fontWeight: 600 }}>{LABELS_MESES[mes]}</span>
              </label>
            ))}
          </div>
        )}

        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          Meses selecionados: <strong>{config.meses_media}</strong>
        </p>
      </section>

      {/* Multiplicadores por Curva */}
      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Multiplicadores por Curva</h2>
            <p>Defina o multiplicador de estoque minimo para cada curva ABC.</p>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          <label style={{ display: "grid", gap: 8 }}>
            <span style={{ fontWeight: 700, color: "var(--liebe-primary)" }}>CURVA AA</span>
            <input
              type="number"
              min={0.5}
              max={5}
              step={0.1}
              value={config.multiplicador_curva_aa ?? 1.5}
              onChange={(e) => setConfig((c) => ({ ...c, multiplicador_curva_aa: Number(e.target.value) }))}
              style={{ fontSize: 18, fontWeight: 700, textAlign: "center" }}
            />
          </label>
          <label style={{ display: "grid", gap: 8 }}>
            <span style={{ fontWeight: 700, color: "var(--liebe-primary)" }}>CURVA A</span>
            <input
              type="number"
              min={0.5}
              max={5}
              step={0.1}
              value={config.multiplicador_curva_a ?? 1.5}
              onChange={(e) => setConfig((c) => ({ ...c, multiplicador_curva_a: Number(e.target.value) }))}
              style={{ fontSize: 18, fontWeight: 700, textAlign: "center" }}
            />
          </label>
          <label style={{ display: "grid", gap: 8 }}>
            <span style={{ fontWeight: 700, color: "var(--amber)" }}>CURVA B</span>
            <input
              type="number"
              min={0.5}
              max={5}
              step={0.1}
              value={config.multiplicador_curva_b ?? 1.0}
              onChange={(e) => setConfig((c) => ({ ...c, multiplicador_curva_b: Number(e.target.value) }))}
              style={{ fontSize: 18, fontWeight: 700, textAlign: "center" }}
            />
          </label>
          <label style={{ display: "grid", gap: 8 }}>
            <span style={{ fontWeight: 700, color: "var(--gray)" }}>CURVA C</span>
            <input
              type="number"
              min={0.5}
              max={5}
              step={0.1}
              value={config.multiplicador_curva_c ?? 1.0}
              onChange={(e) => setConfig((c) => ({ ...c, multiplicador_curva_c: Number(e.target.value) }))}
              style={{ fontSize: 18, fontWeight: 700, textAlign: "center" }}
            />
          </label>
        </div>

        <div style={{ marginTop: 20 }}>
          <button type="button" onClick={saveConfig} disabled={busy} style={{ background: "var(--liebe-primary)", color: "#fff", border: "none" }}>
            <Save size={17} />
            Salvar Configuracoes
          </button>
        </div>
      </section>

      <section className="dashboardGrid">
        <article className="panel">
          <div className="panelHeader">
            <div>
              <h2>Configuracao Global (Legado)</h2>
              <p>Multiplicador unico para todas as curvas.</p>
            </div>
          </div>
          <div className="formGrid">
            <label>
              Meses para media
              <input
                min={1}
                max={12}
                type="number"
                value={config.meses_media}
                onChange={(event) => setConfig((current) => ({ ...current, meses_media: Number(event.target.value) }))}
              />
            </label>
            <label>
              Multiplicador Global
              <input
                min={0.1}
                step={0.1}
                type="number"
                value={config.multiplicador_estoque_minimo}
                onChange={(event) =>
                  setConfig((current) => ({
                    ...current,
                    multiplicador_estoque_minimo: Number(event.target.value),
                  }))
                }
              />
            </label>
            <button type="button" onClick={saveConfig} disabled={busy}>
              <Save size={17} />
              Salvar
            </button>
          </div>
        </article>

        <article className="panel" id="cache">
          <div className="panelHeader">
            <div>
              <h2>Gerenciamento de Cache</h2>
              <p>Atualizacao sob demanda das tabelas materializadas.</p>
            </div>
          </div>
          <div className="metricGrid two">
            <MetricCard title="Status" value={cache?.status ?? "indefinido"} tone="blue" />
            <MetricCard title="Registros" value={cache?.cache?.registros_resumo ?? 0} tone="pink" />
          </div>
          <p className="cacheMeta">
            Ultima atualizacao: {cache?.cache?.atualizado_em ?? "-"} | Base: {cache?.cache?.primeiro_mes ?? "-"} a{" "}
            {cache?.cache?.ultimo_mes ?? "-"}
          </p>
          <button type="button" onClick={refreshCache} disabled={busy}>
            <RefreshCw size={17} />
            Atualizar Tudo
          </button>
        </article>
      </section>
    </PageContainer>
  );
}
