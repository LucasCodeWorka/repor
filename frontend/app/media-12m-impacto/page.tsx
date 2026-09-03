"use client";

import { AlertTriangle, BarChart3, ChevronDown, ChevronRight, PackageSearch, RefreshCw, Search, Store, Target, X } from "lucide-react";
import { Fragment, useEffect, useMemo, useState } from "react";
import { MetricCard, formatNumber } from "../../components/cards/MetricCard";
import { PageContainer } from "../../components/layout/PageContainer";
import { api } from "../../services/api";
import type { Media12mImpacto, Media12mImpactoRow } from "../../types/reposicao";

const CURRENT_MONTH = "2026-08";
const CURRENT_YEAR = 2026;
type MediaMatrixLevel = "loja" | "curva" | "referencia" | "sku";

const emptyData: Media12mImpacto = {
  resumo: {
    skus_analisados: 0,
    lojas: 0,
    referencias: 0,
    skus_com_gap: 0,
    ruptura_silenciosa: 0,
    subestimados: 0,
    gap_pecas: 0,
    media_antiga_total: 0,
    media_12m_total: 0,
    media_sem_ruptura_total: 0,
    estoque_minimo_3m_total: 0,
    estoque_minimo_12m_total: 0,
    gap_estoque_minimo_total: 0,
    estoque_cd_skus_gap: 0,
    qtd_recuperavel: 0,
    deficit_pos_estoque: 0,
  },
  por_loja: [],
  por_referencia: [],
  por_curva: [],
  por_curva_loja: [],
  rows: [],
};

function formatDecimal(value: number | null | undefined) {
  return Number(value || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

function formatPercent(value: number | null | undefined) {
  return `${Number(value || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`;
}

function formatSignedNumber(value: number | null | undefined) {
  const numeric = Number(value || 0);
  return `${numeric > 0 ? "+" : ""}${formatNumber(numeric)}`;
}

function formatSignedPercent(value: number | null | undefined) {
  const numeric = Number(value || 0);
  return `${numeric > 0 ? "+" : ""}${formatPercent(numeric)}`;
}

function mediaJumpPercent(row: Media12mImpactoRow) {
  const oldMedia = Number(row.media_antiga_3m || 0);
  const newMedia = Number(row.media_nova_12m || 0);
  if (oldMedia <= 0) return newMedia > 0 ? null : 0;
  return ((newMedia - oldMedia) / oldMedia) * 100;
}

function formatJumpPercent(value: number | null) {
  if (value === null) return "novo";
  return formatPercent(value);
}

function sizeRank(size: string | null | undefined) {
  const order = ["PP", "P", "M", "G", "GG", "XG", "XGG", "EG", "EGG"];
  const normalized = String(size || "").trim().toUpperCase();
  const index = order.indexOf(normalized);
  return index >= 0 ? index : order.length;
}

function summarizeRows(rows: Media12mImpactoRow[]) {
  const media3 = rows.reduce((sum, row) => sum + Number(row.media_antiga_3m || 0), 0);
  const media12 = rows.reduce((sum, row) => sum + Number(row.media_nova_12m || 0), 0);
  const mediaSemRuptura = rows.reduce((sum, row) => sum + Number(row.media_sem_ruptura_12m || 0), 0);
  return {
    skus: rows.length,
    media3,
    media12,
    mediaSemRuptura,
    salto: media3 > 0 ? ((media12 - media3) / media3) * 100 : media12 > 0 ? null : 0,
    necessidadeAntiga: rows.reduce((sum, row) => sum + Number(row.necessidade_antiga || 0), 0),
    necessidade12m: rows.reduce((sum, row) => sum + Number(row.necessidade_12m || 0), 0),
    gap: rows.reduce((sum, row) => sum + Number(row.gap_necessidade || 0), 0),
    estoqueCd: rows.reduce((sum, row) => sum + Number(row.estoque_disponivel_cd || 0), 0),
    recuperavel: rows.reduce((sum, row) => sum + Number(row.qtd_recuperavel_rateada || 0), 0),
  };
}

function groupMediaRows(rows: Media12mImpactoRow[]) {
  const lojaMap = new Map<string, Media12mImpactoRow[]>();
  rows.forEach((row) => {
    const key = `${row.cd_loja}|${row.nome_loja}`;
    lojaMap.set(key, [...(lojaMap.get(key) || []), row]);
  });

  return Array.from(lojaMap.entries())
    .map(([lojaKey, lojaRows]) => {
      const curvaMap = new Map<string, Media12mImpactoRow[]>();
      lojaRows.forEach((row) => {
        const key = row.curva_completa || "Sem curva";
        curvaMap.set(key, [...(curvaMap.get(key) || []), row]);
      });

      return {
        key: lojaKey,
        label: lojaRows[0]?.nome_loja || lojaKey,
        totals: summarizeRows(lojaRows),
        curvas: Array.from(curvaMap.entries())
          .map(([curvaKey, curvaRows]) => {
            const referenciaMap = new Map<string, Media12mImpactoRow[]>();
            curvaRows.forEach((row) => {
              const key = `${row.referencia}|${row.cor || "Sem cor"}`;
              referenciaMap.set(key, [...(referenciaMap.get(key) || []), row]);
            });

            return {
              key: `${lojaKey}|${curvaKey}`,
              label: curvaKey,
              totals: summarizeRows(curvaRows),
              referencias: Array.from(referenciaMap.entries())
                .map(([referenciaKey, referenciaRows]) => ({
                  key: `${lojaKey}|${curvaKey}|${referenciaKey}`,
                  label: `${referenciaRows[0]?.referencia || referenciaKey} - ${referenciaRows[0]?.descricao_produto || ""}`,
                  cor: referenciaRows[0]?.cor || "Sem cor",
                  totals: summarizeRows(referenciaRows),
                  rows: referenciaRows.sort((a, b) => {
                    const rankDiff = sizeRank(a.tamanho) - sizeRank(b.tamanho);
                    if (rankDiff !== 0) return rankDiff;
                    return String(a.tamanho || "").localeCompare(String(b.tamanho || ""));
                  }),
                }))
                .sort((a, b) => b.totals.gap - a.totals.gap),
            };
          })
          .sort((a, b) => b.totals.gap - a.totals.gap),
      };
    })
    .sort((a, b) => b.totals.gap - a.totals.gap);
}

function statusClass(status: string) {
  const normalized = status.trim().toUpperCase();
  if (normalized === "RUPTURA SILENCIOSA") return "riskCritical";
  if (normalized === "SUBESTIMADO") return "riskHigh";
  if (normalized === "REGRA ATUAL PEGA") return "riskKnown";
  return "riskNeutral";
}

function BarList<T extends { gap_pecas: number; qtd_recuperavel: number }>({
  title,
  subtitle,
  rows,
  label,
}: {
  title: string;
  subtitle: string;
  rows: T[];
  label: (row: T) => string;
}) {
  const max = Math.max(1, ...rows.map((row) => Number(row.gap_pecas || 0)));

  return (
    <section className="panel media12Panel">
      <div className="panelHeader">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <span className="badge">{rows.length} linhas</span>
      </div>
      <div className="media12Bars">
        {rows.slice(0, 12).map((row) => {
          const gap = Number(row.gap_pecas || 0);
          const recover = Number(row.qtd_recuperavel || 0);
          return (
            <div className="media12BarRow" key={label(row)}>
              <div className="media12BarLabel">
                <strong>{label(row)}</strong>
                <span>{formatNumber(gap)} pecas no gap · {formatNumber(recover)} recuperaveis</span>
              </div>
              <div className="media12BarTrack">
                <span className="media12BarFill" style={{ width: `${Math.max(4, (gap / max) * 100)}%` }} />
                <span className="media12BarRecover" style={{ width: `${Math.max(0, (Math.min(recover, gap) / max) * 100)}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function SkuDetail({ row }: { row: Media12mImpactoRow }) {
  const media3Formula = row.formula_media_antiga_3m || `${formatDecimal(row.vendas_3m)} vendas / 3 meses`;

  return (
    <div className="media12Detail">
      <strong>Media 3m atual</strong>
      <span>{media3Formula}</span>
      <span>Meses: {row.meses_utilizados_media_3m || "-"}</span>
      <span>Valores: {row.valores_utilizados_media_3m || "-"}</span>
      <strong>Media 12m consideravel</strong>
      <span>{row.formula_media_nova || "Formula 12m indisponivel"}</span>
      <span>Meses: {row.meses_utilizados_media || "-"}</span>
      <span>Valores: {row.valores_utilizados_media || "-"}</span>
      <span className="media12RuleNote">{row.explicacao_media_12m || "Regra base indisponivel."}</span>
      <strong>Media 12m sem ruptura</strong>
      <span>{row.formula_media_sem_ruptura || "Formula sem ruptura indisponivel"}</span>
      <span>Meses: {row.meses_utilizados_media_sem_ruptura || "-"}</span>
      <span>Valores: {row.valores_utilizados_media_sem_ruptura || "-"}</span>
      <span className="media12RuleNote">{row.explicacao_media_sem_ruptura || "Regra sem ruptura indisponivel."}</span>
    </div>
  );
}

function MediaJumpCard({
  row,
  maxGap,
  onOpenMemory,
}: {
  row: Media12mImpactoRow;
  maxGap: number;
  onOpenMemory: (row: Media12mImpactoRow) => void;
}) {
  const oldMedia = Number(row.media_antiga_3m || 0);
  const newMedia = Number(row.media_nova_12m || 0);
  const noRuptureMedia = Number(row.media_sem_ruptura_12m || 0);
  const gapMedia = Math.max(0, newMedia - oldMedia);
  const pct = mediaJumpPercent(row);

  return (
    <article
      className="media12JumpCard"
      role="button"
      tabIndex={0}
      onClick={() => onOpenMemory(row)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") onOpenMemory(row);
      }}
    >
      <div className="media12JumpTop">
        <div>
          <strong>{row.referencia}</strong>
          <span>{row.cor || "Sem cor"} / {row.tamanho || "Sem tam."}</span>
        </div>
        <em className={statusClass(row.diagnostico)}>{row.diagnostico}</em>
      </div>
      <p>{row.nome_loja}</p>
      <div className="media12Compare">
        <span>
          <small>Media 3m</small>
          <b>{formatDecimal(oldMedia)}</b>
        </span>
        <span>
          <small>Media 12m</small>
          <b>{formatDecimal(newMedia)}</b>
        </span>
        <span>
          <small>Sem ruptura</small>
          <b>{formatDecimal(noRuptureMedia)}</b>
        </span>
        <span>
          <small>Salto</small>
          <b>{formatJumpPercent(pct)}</b>
        </span>
      </div>
      <div className="media12JumpTrack">
        <span style={{ width: `${Math.max(5, (gapMedia / Math.max(1, maxGap)) * 100)}%` }} />
      </div>
      <div className="media12JumpFoot">
        <span>+{formatDecimal(gapMedia)} media</span>
        <span>{formatNumber(row.gap_necessidade)} pecas no gap</span>
      </div>
    </article>
  );
}

function MediaMemoryModal({ row, onClose }: { row: Media12mImpactoRow; onClose: () => void }) {
  const media3Formula = row.formula_media_antiga_3m || `${formatDecimal(row.vendas_3m)} vendas / 3 meses`;
  const oldMedia = Number(row.media_antiga_3m || 0);
  const newMedia = Number(row.media_nova_12m || 0);
  const gapMedia = Math.max(0, newMedia - oldMedia);

  return (
    <div className="modalBackdrop" role="dialog" aria-modal="true" onClick={onClose}>
      <section className="modalPanel media12MemoryModal" onClick={(event) => event.stopPropagation()}>
        <div className="media12MemoryHeader">
          <div>
            <span>Memoria de calculo</span>
            <h2>{row.referencia} - {row.cor || "Sem cor"} / {row.tamanho || "Sem tam."}</h2>
            <p>{row.nome_loja} - SKU {row.cd_produto}</p>
          </div>
          <button type="button" aria-label="Fechar" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="media12MemoryKeys">
          <span>Loja: <strong>{row.cd_loja}</strong></span>
          <span>Produto: <strong>{row.cd_produto}</strong></span>
          <span>Referencia: <strong>{row.referencia}</strong></span>
          <span>Cor: <strong>{row.cor || "-"}</strong></span>
          <span>Tamanho: <strong>{row.tamanho || "-"}</strong></span>
        </div>

        <div className="media12MemoryGrid">
          <article>
            <h3>Media atual 3m</h3>
            <strong>{formatDecimal(row.media_antiga_3m)}</strong>
            <dl>
              <div>
                <dt>Formula</dt>
                <dd>{media3Formula}</dd>
              </div>
              <div>
                <dt>Meses usados</dt>
                <dd>{row.meses_utilizados_media_3m || "-"}</dd>
              </div>
              <div>
                <dt>Valores usados</dt>
                <dd>{row.valores_utilizados_media_3m || "-"}</dd>
              </div>
              <div>
                <dt>Vendas 3m</dt>
                <dd>{formatDecimal(row.vendas_3m)}</dd>
              </div>
              <div>
                <dt>Necessidade pela regra atual</dt>
                <dd>{formatNumber(row.necessidade_antiga)}</dd>
              </div>
              <div>
                <dt>Estoque minimo atual</dt>
                <dd>{formatNumber(row.estoque_minimo_antigo)}</dd>
              </div>
            </dl>
          </article>

          <article>
            <h3>Media consideravel 12m</h3>
            <strong>{formatDecimal(row.media_nova_12m)}</strong>
            <dl>
              <div>
                <dt>Formula</dt>
                <dd>{row.formula_media_nova || "Formula indisponivel"}</dd>
              </div>
              <div>
                <dt>Meses usados</dt>
                <dd>{row.meses_utilizados_media || "-"}</dd>
              </div>
              <div>
                <dt>Valores usados</dt>
                <dd>{row.valores_utilizados_media || "-"}</dd>
              </div>
              <div>
                <dt>Meses considerados</dt>
                <dd>{formatNumber(row.meses_considerados)}</dd>
              </div>
              <div>
                <dt>Regra aplicada</dt>
                <dd>{row.explicacao_media_12m || "Regra base indisponivel."}</dd>
              </div>
            </dl>
          </article>

          <article>
            <h3>Media sem ruptura 12m</h3>
            <strong>{formatDecimal(row.media_sem_ruptura_12m)}</strong>
            <dl>
              <div>
                <dt>Formula</dt>
                <dd>{row.formula_media_sem_ruptura || "Formula indisponivel"}</dd>
              </div>
              <div>
                <dt>Meses usados</dt>
                <dd>{row.meses_utilizados_media_sem_ruptura || "-"}</dd>
              </div>
              <div>
                <dt>Valores usados</dt>
                <dd>{row.valores_utilizados_media_sem_ruptura || "-"}</dd>
              </div>
              <div>
                <dt>Meses considerados</dt>
                <dd>{formatNumber(row.meses_considerados_sem_ruptura)}</dd>
              </div>
              <div>
                <dt>Meses removidos</dt>
                <dd>{row.meses_excluidos_media_sem_ruptura || "Nenhum mes removido."}</dd>
              </div>
              <div>
                <dt>Regra aplicada</dt>
                <dd>{row.explicacao_media_sem_ruptura || "Regra sem ruptura indisponivel."}</dd>
              </div>
            </dl>
          </article>
        </div>

        <div className="media12MemoryResult">
          <div>
            <span>Salto da media</span>
            <strong>+{formatDecimal(gapMedia)}</strong>
            <em>{formatJumpPercent(mediaJumpPercent(row))}</em>
          </div>
          <div>
            <span>Necessidade 12m</span>
            <strong>{formatNumber(row.necessidade_12m)}</strong>
            <em>gap {formatNumber(row.gap_necessidade)}</em>
          </div>
          <div>
            <span>Estoque CD</span>
            <strong>{formatNumber(row.estoque_disponivel_cd)}</strong>
            <em>recup. {formatNumber(row.qtd_recuperavel_rateada)}</em>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function Media12mImpactoPage() {
  const [data, setData] = useState<Media12mImpacto>(emptyData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [diagnostico, setDiagnostico] = useState("TODOS");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [expandedCurva, setExpandedCurva] = useState<string | null>(null);
  const [selectedMemory, setSelectedMemory] = useState<Media12mImpactoRow | null>(null);
  const [matrixLevel, setMatrixLevel] = useState<MediaMatrixLevel>("sku");

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getMedia12mImpacto(CURRENT_YEAR, CURRENT_MONTH, 1200);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar analise 12m");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const filteredRows = useMemo(() => {
    const term = search.trim().toUpperCase();
    return data.rows.filter((row) => {
      const matchSearch =
        !term ||
        row.referencia.toUpperCase().includes(term) ||
        row.nome_loja.toUpperCase().includes(term) ||
        String(row.cd_produto).includes(term) ||
        row.descricao_produto.toUpperCase().includes(term);
      const matchDiagnostico = diagnostico === "TODOS" || row.diagnostico === diagnostico;
      return matchSearch && matchDiagnostico;
    });
  }, [data.rows, diagnostico, search]);

  const groupedRows = useMemo(() => groupMediaRows(filteredRows), [filteredRows]);
  const lojasPorCurva = useMemo(() => {
    const map = new Map<string, typeof data.por_curva_loja>();
    for (const row of data.por_curva_loja) {
      const key = row.curva_completa || "Sem curva";
      map.set(key, [...(map.get(key) ?? []), row]);
    }
    return map;
  }, [data.por_curva_loja]);

  const biggestMediaJumps = useMemo(() => {
    return [...data.rows]
      .filter((row) => Number(row.media_nova_12m || 0) > Number(row.media_antiga_3m || 0))
      .sort((a, b) => {
        const aJump = Number(a.media_nova_12m || 0) - Number(a.media_antiga_3m || 0);
        const bJump = Number(b.media_nova_12m || 0) - Number(b.media_antiga_3m || 0);
        if (bJump !== aJump) return bJump - aJump;
        return Number(b.gap_necessidade || 0) - Number(a.gap_necessidade || 0);
      })
      .slice(0, 8);
  }, [data.rows]);

  const maxMediaJump = Math.max(
    1,
    ...biggestMediaJumps.map((row) => Number(row.media_nova_12m || 0) - Number(row.media_antiga_3m || 0)),
  );

  const recuperavelPct = data.resumo.gap_pecas > 0 ? (data.resumo.qtd_recuperavel / data.resumo.gap_pecas) * 100 : 0;
  const incrementoMedia =
    data.resumo.media_antiga_total > 0
      ? ((data.resumo.media_12m_total - data.resumo.media_antiga_total) / data.resumo.media_antiga_total) * 100
      : 0;
  const reducaoSemRuptura =
    data.resumo.media_12m_total > 0
      ? ((data.resumo.media_sem_ruptura_total - data.resumo.media_12m_total) / data.resumo.media_12m_total) * 100
      : 0;
  const gapEstoqueMinimoPct =
    data.resumo.estoque_minimo_3m_total > 0
      ? (data.resumo.gap_estoque_minimo_total / data.resumo.estoque_minimo_3m_total) * 100
      : data.resumo.estoque_minimo_12m_total > 0 ? 100 : 0;

  return (
    <PageContainer
      eyebrow="Media 12m"
      title="Impacto da Regra 12m"
      description={`Comparativo entre a media atual de 3 meses e a media 12m consideravel para ${CURRENT_MONTH}, com capacidade de recuperacao pelo estoque atual do CD.`}
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

      {loading ? <section className="loadingBand">Carregando impacto da media 12m...</section> : null}

      <section className="metricGrid dashboardMetrics">
        <MetricCard title="Ruptura silenciosa" value={data.resumo.ruptura_silenciosa} subtitle="Regra antiga nao pediria" tone="red" icon={<AlertTriangle size={17} />} />
        <MetricCard title="Subestimados" value={data.resumo.subestimados} subtitle="Media 3m ficou baixa" tone="amber" icon={<BarChart3 size={17} />} />
        <MetricCard title="Gap de pecas" value={data.resumo.gap_pecas} subtitle="Necessidade adicional 12m" tone="pink" icon={<Target size={17} />} />
        <MetricCard title="Recuperavel agora" value={data.resumo.qtd_recuperavel} subtitle={`${formatPercent(recuperavelPct)} do gap`} tone="green" icon={<PackageSearch size={17} />} />
        <MetricCard title="Media 12m vs 3m" value={formatPercent(incrementoMedia)} subtitle="Aumento da demanda lida" tone="blue" />
        <MetricCard title="Media sem ruptura" value={formatPercent(reducaoSemRuptura)} subtitle="Variacao contra media 12m" tone="green" />
      </section>

      <section className="panel media12ScenarioPanel">
        <div className="panelHeader">
          <div>
            <h2>Cenario de Calculo</h2>
            <p>Totalizadores de media usados nesta analise para {CURRENT_MONTH}</p>
          </div>
        </div>
        <div className="media12ScenarioGrid">
          <article className="media12ScenarioCard">
            <span className="media12ScenarioLabel">Media 3m</span>
            <strong className="media12ScenarioValue">{formatDecimal(data.resumo.media_antiga_total)}</strong>
            <p className="media12ScenarioDesc">Total de pecas/mes pela regra atual</p>
            <div className="media12ScenarioMeta">
              <span>Estoque minimo geral</span>
              <b>{formatNumber(data.resumo.estoque_minimo_3m_total)}</b>
            </div>
          </article>
          <article className="media12ScenarioCard media12ScenarioActive">
            <span className="media12ScenarioLabel">Media 12m Protegida</span>
            <strong className="media12ScenarioValue">{formatDecimal(data.resumo.media_12m_total)}</strong>
            <p className="media12ScenarioDesc">Total de pecas/mes com meses consideraveis</p>
            <div className="media12ScenarioMeta">
              <span>Estoque minimo protegido</span>
              <b>{formatNumber(data.resumo.estoque_minimo_12m_total)}</b>
            </div>
            <em className="media12ScenarioBadge">Cenario ativo</em>
          </article>
          <article className="media12ScenarioCard">
            <span className="media12ScenarioLabel">Dif. de Estoque Minimo</span>
            <strong className="media12ScenarioValue">{formatSignedNumber(data.resumo.gap_estoque_minimo_total)}</strong>
            <p className="media12ScenarioDesc">{formatSignedPercent(gapEstoqueMinimoPct)} contra a regra 3m</p>
            <div className="media12ScenarioMeta">
              <span>Media sem ruptura</span>
              <b>{formatDecimal(data.resumo.media_sem_ruptura_total)}</b>
            </div>
          </article>
        </div>
      </section>

      <section className="media12Explain">
        <div>
          <strong>Falha da regra atual</strong>
          <span>Quando o SKU rompe, a venda recente cai e a media 3m passa a dizer que nao existe demanda.</span>
        </div>
        <div>
          <strong>Correcao da media 12m</strong>
          <span>Usa meses com estoque, entrada ou venda relevante para reconstruir uma demanda mais estavel.</span>
        </div>
        <div>
          <strong>Limite operacional</strong>
          <span>A tela separa o gap teorico do que da para corrigir com estoque disponivel hoje.</span>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Maiores Saltos da Media</h2>
            <p>Comparativo direto entre a media 3m atual e a media 12m para localizar onde a regra esta elevando mais a demanda.</p>
          </div>
          <span className="badge">Top {biggestMediaJumps.length}</span>
        </div>
        <div className="media12JumpGrid">
          {biggestMediaJumps.map((row) => (
            <MediaJumpCard
              row={row}
              maxGap={maxMediaJump}
              onOpenMemory={setSelectedMemory}
              key={`${row.cd_loja}-${row.cd_produto}-jump`}
            />
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Diagnostico por Curva</h2>
            <p>Mostra se o problema esta concentrado nos produtos que deveriam ter maior protecao.</p>
          </div>
          <span className="badge">{data.por_curva.length} curvas</span>
        </div>
        <div className="media12CurveGrid">
          {data.por_curva.map((row) => {
            const pct = row.gap_pecas > 0 ? (row.qtd_recuperavel / row.gap_pecas) * 100 : 0;
            const estoqueGapPct =
              Number(row.estoque_minimo_3m_total || 0) > 0
                ? (Number(row.gap_estoque_minimo_total || 0) / Number(row.estoque_minimo_3m_total || 0)) * 100
                : Number(row.estoque_minimo_12m_total || 0) > 0 ? 100 : 0;
            const curvaKey = row.curva_completa || "Sem curva";
            const lojas = lojasPorCurva.get(curvaKey) ?? [];
            const isOpen = expandedCurva === curvaKey;
            return (
              <article className="media12CurveCard" key={curvaKey}>
                <button
                  type="button"
                  className="media12CurveToggle"
                  onClick={() => setExpandedCurva((current) => (current === curvaKey ? null : curvaKey))}
                >
                  <span>{curvaKey}</span>
                  {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </button>
                <strong>{formatNumber(row.estoque_minimo_12m_total)}</strong>
            <p>Est. min. protegido vs {formatNumber(row.estoque_minimo_3m_total)} no 3m</p>
                <div className="media12CurveMetrics">
                  <small><b>{formatSignedNumber(row.gap_estoque_minimo_total)}</b> dif. est. min.</small>
                  <small><b>{formatSignedPercent(estoqueGapPct)}</b> vs 3m</small>
                  <small><b>{formatSignedNumber(row.gap_necessidade_total)}</b> dif. necessidade</small>
                  <small><b>{formatPercent(pct)}</b> recuperavel</small>
                </div>
                <p>{formatNumber(row.skus_com_gap)} SKUs com gap · {formatNumber(row.ruptura_silenciosa)} silenciosos</p>
                <em>{formatNumber(lojas.length)} lojas para validar</em>
                {isOpen ? (
                  <div className="media12CurveStores">
                    <table>
                      <thead>
                        <tr>
                          <th>Loja</th>
                          <th>Est. min. 3m</th>
                          <th>Est. min. prot.</th>
                          <th>Dif.</th>
                          <th>Nec. 3m</th>
                          <th>Nec. 12m</th>
                          <th>Dif. nec.</th>
                          <th>SKUs gap</th>
                        </tr>
                      </thead>
                      <tbody>
                        {lojas.map((loja) => (
                          <tr key={`${curvaKey}-${loja.cd_loja}`}>
                            <td>
                              <span>{loja.cd_loja}</span>
                              <strong title={loja.nome_loja}>{loja.nome_loja}</strong>
                            </td>
                            <td>{formatNumber(loja.estoque_minimo_3m_total)}</td>
                            <td>{formatNumber(loja.estoque_minimo_12m_total)}</td>
                            <td>{formatSignedNumber(loja.gap_estoque_minimo_total)}</td>
                            <td>{formatNumber(loja.necessidade_3m_total)}</td>
                            <td>{formatNumber(loja.necessidade_12m_total)}</td>
                            <td>{formatSignedNumber(loja.gap_necessidade_total)}</td>
                            <td>{formatNumber(loja.skus_com_gap)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>SKUs que a Regra 12m Recupera</h2>
            <p>Lista priorizada pelo maior gap de necessidade e pela ruptura silenciosa.</p>
          </div>
          <span className="badge">{filteredRows.length} registros</span>
        </div>

        <div className="media12Filters">
          <label>
            <Search size={16} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar loja, referencia ou SKU" />
          </label>
          <select value={diagnostico} onChange={(event) => setDiagnostico(event.target.value)}>
            <option value="TODOS">Todos os diagnosticos</option>
            <option value="RUPTURA SILENCIOSA">Ruptura silenciosa</option>
            <option value="SUBESTIMADO">Subestimado</option>
            <option value="REGRA ATUAL PEGA">Regra atual pega</option>
          </select>
          <div className="media12LevelControl" aria-label="Nivel da matriz">
            {[
              ["loja", "Loja"],
              ["curva", "Curva"],
              ["referencia", "Ref/Cor"],
              ["sku", "SKU"],
            ].map(([level, label]) => (
              <button
                type="button"
                className={matrixLevel === level ? "active" : ""}
                onClick={() => setMatrixLevel(level as MediaMatrixLevel)}
                key={level}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="tableWrap media12TableWrap">
          <table className="media12Table">
            <thead>
              <tr>
                <th>Loja</th>
                <th>Referencia</th>
                <th>SKU</th>
                <th>Cor/Tam.</th>
                <th>Curva</th>
                <th>Diagnostico</th>
                <th>Media 3m</th>
                <th>Media 12m atual</th>
                <th>Media 12m s/ ruptura</th>
                <th>Salto</th>
                <th>Nec. atual</th>
                <th>Nec. 12m</th>
                <th>Gap</th>
                <th>Estoque CD</th>
                <th>Recup.</th>
                <th>Cobertura</th>
              </tr>
            </thead>
            <tbody>
              {groupedRows.map((loja) => (
                <Fragment key={loja.key}>
                  <tr className="media12GroupRow media12StoreGroup">
                    <td colSpan={6}>
                      <strong><Store size={14} /> {loja.label}</strong>
                      <span>{formatNumber(loja.totals.skus)} SKUs agrupados por curva e referencia/cor</span>
                    </td>
                    <td>{formatDecimal(loja.totals.media3)}</td>
                    <td>{formatDecimal(loja.totals.media12)}</td>
                    <td>{formatDecimal(loja.totals.mediaSemRuptura)}</td>
                    <td>{formatJumpPercent(loja.totals.salto)}</td>
                    <td>{formatNumber(loja.totals.necessidadeAntiga)}</td>
                    <td>{formatNumber(loja.totals.necessidade12m)}</td>
                    <td className="bad">{formatNumber(loja.totals.gap)}</td>
                    <td>{formatNumber(loja.totals.estoqueCd)}</td>
                    <td>{formatNumber(loja.totals.recuperavel)}</td>
                    <td>-</td>
                  </tr>
                  {matrixLevel !== "loja" ? loja.curvas.map((curva) => (
                    <Fragment key={curva.key}>
                      <tr className="media12GroupRow media12CurveGroup">
                        <td colSpan={6}>
                          <strong>{curva.label}</strong>
                          <span>{formatNumber(curva.totals.skus)} SKUs em {loja.label}</span>
                        </td>
                        <td>{formatDecimal(curva.totals.media3)}</td>
                        <td>{formatDecimal(curva.totals.media12)}</td>
                        <td>{formatDecimal(curva.totals.mediaSemRuptura)}</td>
                        <td>{formatJumpPercent(curva.totals.salto)}</td>
                        <td>{formatNumber(curva.totals.necessidadeAntiga)}</td>
                        <td>{formatNumber(curva.totals.necessidade12m)}</td>
                        <td className="bad">{formatNumber(curva.totals.gap)}</td>
                        <td>{formatNumber(curva.totals.estoqueCd)}</td>
                        <td>{formatNumber(curva.totals.recuperavel)}</td>
                        <td>-</td>
                      </tr>
                      {matrixLevel !== "curva" ? curva.referencias.map((referencia) => (
                        <Fragment key={referencia.key}>
                          <tr className="media12GroupRow media12RefGroup">
                            <td colSpan={6}>
                              <strong>{referencia.label}</strong>
                              <span>Cor {referencia.cor} - {formatNumber(referencia.totals.skus)} tamanhos/SKUs</span>
                            </td>
                            <td>{formatDecimal(referencia.totals.media3)}</td>
                            <td>{formatDecimal(referencia.totals.media12)}</td>
                            <td>{formatDecimal(referencia.totals.mediaSemRuptura)}</td>
                            <td>{formatJumpPercent(referencia.totals.salto)}</td>
                            <td>{formatNumber(referencia.totals.necessidadeAntiga)}</td>
                            <td>{formatNumber(referencia.totals.necessidade12m)}</td>
                            <td className="bad">{formatNumber(referencia.totals.gap)}</td>
                            <td>{formatNumber(referencia.totals.estoqueCd)}</td>
                            <td>{formatNumber(referencia.totals.recuperavel)}</td>
                            <td>-</td>
                          </tr>
                          {matrixLevel === "sku" ? referencia.rows.map((row) => {
                            const key = `${row.cd_loja}-${row.cd_produto}`;
                            return (
                              <Fragment key={key}>
                                <tr className="media12SkuRow" onClick={() => setExpanded((current) => (current === key ? null : key))}>
                                  <td className="media12SkuIndent">Tam. {row.tamanho || "-"}</td>
                                  <td>
                                    <strong>{row.referencia}</strong>
                                    <span>{row.descricao_produto}</span>
                                  </td>
                                  <td>{row.cd_produto}</td>
                                  <td>{row.cor || "-"} / {row.tamanho || "-"}</td>
                                  <td>{row.curva_completa || "-"}</td>
                                  <td><em className={statusClass(row.diagnostico)}>{row.diagnostico}</em></td>
                                  <td>{formatDecimal(row.media_antiga_3m)}</td>
                                  <td>{formatDecimal(row.media_nova_12m)}</td>
                                  <td>{formatDecimal(row.media_sem_ruptura_12m)}</td>
                                  <td>{formatJumpPercent(mediaJumpPercent(row))}</td>
                                  <td>{formatNumber(row.necessidade_antiga)}</td>
                                  <td>{formatNumber(row.necessidade_12m)}</td>
                                  <td className="bad">{formatNumber(row.gap_necessidade)}</td>
                                  <td>{formatNumber(row.estoque_disponivel_cd)}</td>
                                  <td>{formatNumber(row.qtd_recuperavel_rateada)}</td>
                                  <td>{formatDecimal(row.cobertura_potencial_meses)}m</td>
                                </tr>
                                {expanded === key ? (
                                  <tr className="media12Expanded" key={`${key}-detail`}>
                                    <td colSpan={16}>
                                      <SkuDetail row={row} />
                                    </td>
                                  </tr>
                                ) : null}
                              </Fragment>
                            );
                          }) : null}
                        </Fragment>
                      )) : null}
                    </Fragment>
                  )) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {selectedMemory ? <MediaMemoryModal row={selectedMemory} onClose={() => setSelectedMemory(null)} /> : null}
    </PageContainer>
  );
}
