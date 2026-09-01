"use client";

import { AlertTriangle, ChevronDown, ChevronRight, ClipboardList, FileSearch, PackageCheck, RefreshCw, Send, Store, Target, X } from "lucide-react";
import { Fragment, useEffect, useMemo, useState } from "react";
import { MetricCard, formatNumber } from "../../components/cards/MetricCard";
import { StatusBadge } from "../../components/cards/StatusBadge";
import { PageContainer } from "../../components/layout/PageContainer";
import { api } from "../../services/api";
import type {
  ClassificacaoFiltros,
  ProcessoReposicaoResumo,
  ProcessoReposicaoRow,
  ReposicaoFiltros,
  TotvsPedidoPreview,
} from "../../types/reposicao";

// Usar mês fixo até que dados mais recentes estejam disponíveis
const CURRENT_MONTH = "2026-08";
const CURRENT_YEAR = 2026;
const MONTH_OPTIONS = ["2026-09", "2026-08", "2026-07", "2026-06"];
const emptyClassificacoes: ClassificacaoFiltros = {
  status_produto: [],
  continuidade: [],
  linha: [],
  familia: [],
};

const emptyResumo: ProcessoReposicaoResumo = {
  skus_sugeridos: 0,
  lojas: 0,
  pecas_sugeridas: 0,
  necessidade: 0,
  entrada_total: 0,
  criticos: 0,
  altos: 0,
  normais: 0,
};

type PedidoReposicaoRow = ProcessoReposicaoRow & {
  qtd_pedido: number;
};

type PedidoReposicao = {
  titulo: string;
  subtitulo: string;
  tipo: "CURVA_A_AA" | "CURVA_BC_1" | "CURVA_BC_2";
  rows: PedidoReposicaoRow[];
};

type TotvsOrderPreview = NonNullable<TotvsPedidoPreview["orders"]>[number];
type MediaScenarioKey = "media3m" | "media6m" | "media12m";

const mediaScenarios: Array<{ key: MediaScenarioKey; title: string; subtitle: string }> = [
  { key: "media3m", title: "Media 3m", subtitle: "Ultimos 3 meses antes do periodo" },
  { key: "media6m", title: "Media 6m sem abr/mai", subtitle: "Ultimos 6 meses, removendo abril e maio" },
  { key: "media12m", title: "Media 12m", subtitle: "Meses consideraveis dos ultimos 12 meses" },
];

function curvaNormalizada(curva: string) {
  return curva.trim().toUpperCase();
}

function isCurvaAAA(curva: string) {
  const value = curvaNormalizada(curva);
  return value === "CURVA A" || value === "CURVA AA";
}

function isCurvaBC(curva: string) {
  const value = curvaNormalizada(curva);
  return value === "CURVA B" || value === "CURVA C";
}

function formatDecimal(value: number) {
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

function coverage(stock: number, monthlyAverage: number) {
  if (monthlyAverage <= 0) return 0;
  return stock / monthlyAverage;
}

function scenarioMedia(row: ProcessoReposicaoRow, scenario: MediaScenarioKey) {
  const media3m = Number(row.media_mensal || 0);
  if (scenario === "media12m") return Math.max(media3m, Number(row.media_12m_consideravel || 0));
  if (scenario === "media6m") return Math.max(media3m, Number(row.media_6m_sem_abr_mai || 0));
  return media3m;
}

function scenarioNeed(row: ProcessoReposicaoRow, scenario: MediaScenarioKey) {
  if (scenario === "media12m") return Number(row.necessidade_12m || 0);
  if (scenario === "media6m") return Number(row.necessidade_6m || 0);
  return Number(row.necessidade || 0);
}

function scenarioOrderQty(row: ProcessoReposicaoRow, scenario: MediaScenarioKey) {
  if (scenario === "media12m") return Number(row.qtd_sugerida_12m || 0);
  if (scenario === "media6m") return Number(row.qtd_sugerida_6m || 0);
  return Number(row.qtd_sugerida || 0);
}

function applyScenario(row: ProcessoReposicaoRow, scenario: MediaScenarioKey): PedidoReposicaoRow {
  const necessidade = scenarioNeed(row, scenario);
  const entradaTotal = Number(row.entrada_total || 0);
  const qtdSugerida = scenarioOrderQty(row, scenario);
  return {
    ...row,
    media_mensal: scenarioMedia(row, scenario),
    estoque_minimo: Number(
      scenario === "media12m"
        ? row.estoque_minimo_12m
        : scenario === "media6m"
          ? row.estoque_minimo_6m
          : row.estoque_minimo,
    ) || 0,
    necessidade,
    qtd_sugerida_bruta: Math.max(0, necessidade - entradaTotal),
    qtd_sugerida: qtdSugerida,
    qtd_pedido: qtdSugerida,
  };
}

type CalculationMemory = {
  curva: string;
  multiplicador: number;
  media: number;
  estMin: number;
  saldo: number;
  nec: number;
  ent: number;
  faltaBruta: number;
  pendPedido: number;
  transito: number;
  jaProg: number;
  pedido: number;
  formula: string;
  detalhes: string;
};

function buildCalculationMemory(row: PedidoReposicaoRow): CalculationMemory {
  const curva = String(row.curva_completa || "");
  const multiplicador = isCurvaAAA(curva) ? 1.5 : 1.0;
  const targetDays = isCurvaAAA(curva) ? 45 : 30;
  const media = Number(row.media_mensal || 0);
  const estMin = Number(row.estoque_minimo || 0);
  const saldo = Number(row.saldo_inicial || 0);
  const nec = Number(row.necessidade || 0);
  const ent = Number(row.entrada_total || 0);
  const pendPedido = Number(row.qtd_pendente_pedido || 0);
  const transito = Number(row.qtd_transito || 0);
  const jaProg = Number(row.qtd_ja_programada || 0);
  const pedido = Number(row.qtd_pedido || 0);
  const faltaBruta = Math.max(0, nec - ent);

  const formula = `Nec ${formatNumber(nec)} - Ent ${formatNumber(ent)} - Prog ${formatNumber(jaProg)} = ${formatNumber(pedido)}`;
  const detalhes = [
    `Média: ${formatDecimal(media)}`,
    `Est.Mín: ${formatNumber(estMin)}`,
    `Saldo: ${formatNumber(saldo)}`,
    `Necessidade: ${formatNumber(nec)}`,
    `Entrada: ${formatNumber(ent)}`,
    `Falta Bruta: ${formatNumber(faltaBruta)}`,
    `Pend.Pedido: ${formatNumber(pendPedido)}`,
    `Trânsito: ${formatNumber(transito)}`,
    `Já Prog: ${formatNumber(jaProg)}`,
    `Pedido: ${formatNumber(pedido)}`,
  ].join(" | ");

  return { curva, multiplicador, media, estMin, saldo, nec, ent, faltaBruta, pendPedido, transito, jaProg, pedido, formula, detalhes: `${detalhes} | Meta: ${targetDays} dias` };
}

function CalculationTooltip({ memory }: { memory: CalculationMemory }) {
  return (
    <div className="calculationTooltip">
      <div className="calcGrid">
        <div className="calcSection">
          <span className="calcLabel">1. Base do Cálculo</span>
          <div className="calcRow"><span>Média mensal (3m)</span><strong>{formatDecimal(memory.media)}</strong></div>
          <div className="calcRow"><span>Curva</span><strong>{memory.curva || "-"}</strong></div>
          <div className="calcRow"><span>Multiplicador</span><strong>× {formatDecimal(memory.multiplicador)}</strong></div>
          <div className="calcRow"><span>Est. mínimo</span><strong className="highlight-amber">{formatNumber(memory.estMin)}</strong></div>
          <div className="calcRow"><span>Saldo inicial</span><strong>{formatNumber(memory.saldo)}</strong></div>
        </div>
        <div className="calcSection">
          <span className="calcLabel">2. Necessidade</span>
          <div className="calcRow small"><span>Est.Mín - Saldo</span><strong>{formatNumber(memory.estMin)} - {formatNumber(memory.saldo)}</strong></div>
          <div className="calcRow"><span>= max(0, resultado)</span><strong className="highlight-pink">{formatNumber(memory.nec)}</strong></div>
          <div className="calcFormulaMini">
            <code>max(0, {formatNumber(memory.estMin)} - {formatNumber(memory.saldo)}) = {formatNumber(memory.nec)}</code>
          </div>
        </div>
        <div className="calcSection">
          <span className="calcLabel">3. Falta Bruta</span>
          <div className="calcRow"><span>Necessidade</span><strong className="highlight-pink">{formatNumber(memory.nec)}</strong></div>
          <div className="calcRow"><span>Entrada total</span><strong className="highlight-blue">- {formatNumber(memory.ent)}</strong></div>
          <div className="calcRow"><span>= Falta bruta</span><strong className="highlight-amber">{formatNumber(memory.faltaBruta)}</strong></div>
        </div>
        <div className="calcSection">
          <span className="calcLabel">4. Deduções</span>
          <div className="calcRow"><span>Pend. pedido</span><strong>{formatNumber(memory.pendPedido)}</strong></div>
          <div className="calcRow"><span>Trânsito</span><strong>{formatNumber(memory.transito)}</strong></div>
          <div className="calcRow"><span>Já programado</span><strong>{formatNumber(memory.jaProg)}</strong></div>
        </div>
      </div>
      <div className="calcResultSection">
        <div className="calcResultRow">
          <span>Pedido Final</span>
          <strong className="highlight-green">{formatNumber(memory.pedido)}</strong>
        </div>
        <div className="calcFormula">
          <code>Falta({formatNumber(memory.faltaBruta)}) - JáProg({formatNumber(memory.jaProg)}) = {formatNumber(memory.pedido)}</code>
        </div>
      </div>
      <div className="calcFullFormula">
        <span className="calcLabel">Fórmula Completa</span>
        <code>
          Necessidade = max(0, EstMín - Saldo) = max(0, {formatNumber(memory.estMin)} - {formatNumber(memory.saldo)}) = {formatNumber(memory.nec)}<br/>
          Falta = max(0, Nec - Entrada) = max(0, {formatNumber(memory.nec)} - {formatNumber(memory.ent)}) = {formatNumber(memory.faltaBruta)}<br/>
          Pedido = max(0, Falta - JáProg) = max(0, {formatNumber(memory.faltaBruta)} - {formatNumber(memory.jaProg)}) = {formatNumber(memory.pedido)}
        </code>
      </div>
    </div>
  );
}

function PedidoMatrix({ pedido }: { pedido: PedidoReposicao }) {
  const [expandedEmpresas, setExpandedEmpresas] = useState<Set<string>>(new Set());
  const [expandedRefs, setExpandedRefs] = useState<Set<string>>(new Set());
  const [hoveredSku, setHoveredSku] = useState<string | null>(null);

  const totalPecas = pedido.rows.reduce((acc, row) => acc + Number(row.qtd_pedido || 0), 0);
  const totalSkus = pedido.rows.length;
  const empresas = useMemo(() => {
    const empresaMap = new Map<string, PedidoReposicaoRow[]>();
    for (const row of pedido.rows) {
      empresaMap.set(row.nome_loja, [...(empresaMap.get(row.nome_loja) ?? []), row]);
    }

    return Array.from(empresaMap.entries())
      .map(([empresa, empresaRows]) => {
        const refMap = new Map<string, PedidoReposicaoRow[]>();
        for (const row of empresaRows) {
          refMap.set(row.referencia, [...(refMap.get(row.referencia) ?? []), row]);
        }
        return {
          empresa,
          rows: empresaRows,
          total: empresaRows.reduce((acc, row) => acc + Number(row.qtd_pedido || 0), 0),
          refs: Array.from(refMap.entries())
            .map(([referencia, refRows]) => ({
              referencia,
              descricao: refRows[0]?.descricao_produto ?? "",
              rows: refRows.sort((a, b) => `${a.cor}-${a.tamanho}-${a.cd_produto}`.localeCompare(`${b.cor}-${b.tamanho}-${b.cd_produto}`)),
              total: refRows.reduce((acc, row) => acc + Number(row.qtd_pedido || 0), 0),
            }))
            .sort((a, b) => b.total - a.total || a.referencia.localeCompare(b.referencia)),
        };
      })
      .sort((a, b) => b.total - a.total || a.empresa.localeCompare(b.empresa));
  }, [pedido.rows]);

  function toggleEmpresa(empresa: string) {
    setExpandedEmpresas((current) => {
      const next = new Set(current);
      if (next.has(empresa)) next.delete(empresa);
      else next.add(empresa);
      return next;
    });
  }

  function toggleRef(refKey: string) {
    setExpandedRefs((current) => {
      const next = new Set(current);
      if (next.has(refKey)) next.delete(refKey);
      else next.add(refKey);
      return next;
    });
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <h2>{pedido.titulo}</h2>
          <p>{pedido.subtitulo}</p>
        </div>
        <span className="badge">{formatNumber(totalPecas)} peças</span>
      </div>

      <div className="matrixWrap">
        <table className="matrixTable pedidoMatrixTable fullMemory">
          <thead>
            <tr>
              <th className="colFixed">Empresa / Referência / SKU</th>
              <th className="colNum">SKUs</th>
              <th className="colNum highlight-result">Pedido</th>
              <th className="colNum">Média</th>
              <th className="colNum">Est.Mín</th>
              <th className="colNum">Saldo</th>
              <th className="colNum highlight-pink">Nec.</th>
              <th className="colNum highlight-blue">Entrada</th>
              <th className="colNum highlight-amber">Falta</th>
              <th className="colNum">Pend.</th>
              <th className="colNum">Trâns.</th>
              <th className="colNum">Já Prog</th>
              <th className="colNum">Cob.Atual</th>
              <th className="colNum">Cob.Pós</th>
              <th>Curva</th>
              <th>Status</th>
              <th>Prior.</th>
            </tr>
          </thead>
          <tbody>
            <tr className="matrixGroup totalGeral">
              <td>
                <strong>Total do pedido</strong>
              </td>
              <td>{formatNumber(totalSkus)}</td>
              <td className="highlight-result">{formatNumber(totalPecas)}</td>
              <td>-</td>
              <td>-</td>
              <td>{formatNumber(pedido.rows.reduce((acc, row) => acc + Number(row.saldo_inicial || 0), 0))}</td>
              <td className="highlight-pink">{formatNumber(pedido.rows.reduce((acc, row) => acc + Number(row.necessidade || 0), 0))}</td>
              <td className="highlight-blue">{formatNumber(pedido.rows.reduce((acc, row) => acc + Number(row.entrada_total || 0), 0))}</td>
              <td className="highlight-amber">{formatNumber(pedido.rows.reduce((acc, row) => acc + Math.max(0, Number(row.necessidade || 0) - Number(row.entrada_total || 0)), 0))}</td>
              <td>{formatNumber(pedido.rows.reduce((acc, row) => acc + Number(row.qtd_pendente_pedido || 0), 0))}</td>
              <td>{formatNumber(pedido.rows.reduce((acc, row) => acc + Number(row.qtd_transito || 0), 0))}</td>
              <td>{formatNumber(pedido.rows.reduce((acc, row) => acc + Number(row.qtd_ja_programada || 0), 0))}</td>
              <td>-</td>
              <td>-</td>
              <td>-</td>
              <td>-</td>
              <td>-</td>
            </tr>

            {empresas.map((empresa) => {
              const empresaOpen = expandedEmpresas.has(empresa.empresa);
              return (
                <Fragment key={empresa.empresa}>
                  <tr className="matrixGroup empresa">
                    <td>
                      <button type="button" onClick={() => toggleEmpresa(empresa.empresa)}>
                        {empresaOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        <strong>{empresa.empresa}</strong>
                      </button>
                    </td>
                    <td>{formatNumber(empresa.rows.length)}</td>
                    <td className="highlight-result">{formatNumber(empresa.total)}</td>
                    <td>-</td>
                    <td>-</td>
                    <td>{formatNumber(empresa.rows.reduce((acc, row) => acc + Number(row.saldo_inicial || 0), 0))}</td>
                    <td className="highlight-pink">{formatNumber(empresa.rows.reduce((acc, row) => acc + Number(row.necessidade || 0), 0))}</td>
                    <td className="highlight-blue">{formatNumber(empresa.rows.reduce((acc, row) => acc + Number(row.entrada_total || 0), 0))}</td>
                    <td className="highlight-amber">{formatNumber(empresa.rows.reduce((acc, row) => acc + Math.max(0, Number(row.necessidade || 0) - Number(row.entrada_total || 0)), 0))}</td>
                    <td>{formatNumber(empresa.rows.reduce((acc, row) => acc + Number(row.qtd_pendente_pedido || 0), 0))}</td>
                    <td>{formatNumber(empresa.rows.reduce((acc, row) => acc + Number(row.qtd_transito || 0), 0))}</td>
                    <td>{formatNumber(empresa.rows.reduce((acc, row) => acc + Number(row.qtd_ja_programada || 0), 0))}</td>
                    <td>-</td>
                    <td>-</td>
                    <td>-</td>
                    <td>-</td>
                    <td>-</td>
                  </tr>
                  {empresaOpen
                    ? empresa.refs.map((ref) => {
                        const refKey = `${empresa.empresa}-${ref.referencia}`;
                        const refOpen = expandedRefs.has(refKey);
                        return (
                          <Fragment key={refKey}>
                            <tr className="matrixGroup referencia">
                              <td>
                                <button type="button" onClick={() => toggleRef(refKey)}>
                                  {refOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                  <span>
                                    <strong>{ref.referencia}</strong>
                                    <em>{ref.descricao}</em>
                                  </span>
                                </button>
                              </td>
                              <td>{formatNumber(ref.rows.length)}</td>
                              <td className="highlight-result">{formatNumber(ref.total)}</td>
                              <td>-</td>
                              <td>-</td>
                              <td>{formatNumber(ref.rows.reduce((acc, row) => acc + Number(row.saldo_inicial || 0), 0))}</td>
                              <td className="highlight-pink">{formatNumber(ref.rows.reduce((acc, row) => acc + Number(row.necessidade || 0), 0))}</td>
                              <td className="highlight-blue">{formatNumber(ref.rows.reduce((acc, row) => acc + Number(row.entrada_total || 0), 0))}</td>
                              <td className="highlight-amber">{formatNumber(ref.rows.reduce((acc, row) => acc + Math.max(0, Number(row.necessidade || 0) - Number(row.entrada_total || 0)), 0))}</td>
                              <td>{formatNumber(ref.rows.reduce((acc, row) => acc + Number(row.qtd_pendente_pedido || 0), 0))}</td>
                              <td>{formatNumber(ref.rows.reduce((acc, row) => acc + Number(row.qtd_transito || 0), 0))}</td>
                              <td>{formatNumber(ref.rows.reduce((acc, row) => acc + Number(row.qtd_ja_programada || 0), 0))}</td>
                              <td>-</td>
                              <td>-</td>
                              <td>{ref.rows[0]?.curva_completa ?? "-"}</td>
                              <td>{ref.rows[0]?.status_produto ?? "-"}</td>
                              <td>{ref.rows[0]?.prioridade ?? "-"}</td>
                            </tr>
                            {refOpen
                              ? ref.rows.map((item) => {
                                  const memory = buildCalculationMemory(item);
                                  const currentCoverage = coverage(
                                    Number(item.saldo_inicial || 0) + Number(item.entrada_total || 0),
                                    Number(item.media_mensal || 0),
                                  );
                                  const projectedCoverage = coverage(
                                    Number(item.saldo_inicial || 0) +
                                      Number(item.entrada_total || 0) +
                                      Number(item.qtd_ja_programada || 0) +
                                      Number(item.qtd_pedido || 0),
                                    Number(item.media_mensal || 0),
                                  );
                                  const skuKey = `${item.mes}-${item.cd_loja}-${item.cd_produto}`;
                                  const isHovered = hoveredSku === skuKey;
                                  return (
                                  <tr
                                    className={`matrixSku ${isHovered ? "hovered" : ""}`}
                                    key={skuKey}
                                    onMouseEnter={() => setHoveredSku(skuKey)}
                                    onMouseLeave={() => setHoveredSku(null)}
                                  >
                                    <td className="skuCell">
                                      <span className="skuLabel">
                                        <strong>{item.cor || "SEM COR"} / {item.tamanho || "SEM TAM."}</strong>
                                        <em>SKU {item.cd_produto} · {item.linha ?? "-"}</em>
                                      </span>
                                      {isHovered && <CalculationTooltip memory={memory} />}
                                    </td>
                                    <td>1</td>
                                    <td className="highlight-result">{formatNumber(item.qtd_pedido)}</td>
                                    <td>{formatDecimal(memory.media)}</td>
                                    <td>{formatNumber(memory.estMin)}</td>
                                    <td>{formatNumber(memory.saldo)}</td>
                                    <td className="highlight-pink">{formatNumber(memory.nec)}</td>
                                    <td className="highlight-blue">{formatNumber(memory.ent)}</td>
                                    <td className="highlight-amber">{formatNumber(memory.faltaBruta)}</td>
                                    <td>{formatNumber(memory.pendPedido)}</td>
                                    <td>{formatNumber(memory.transito)}</td>
                                    <td>{formatNumber(memory.jaProg)}</td>
                                    <td>{formatDecimal(currentCoverage)}m</td>
                                    <td>{formatDecimal(projectedCoverage)}m</td>
                                    <td>{item.curva_completa}</td>
                                    <td>{item.status_produto ?? "-"}</td>
                                    <td>
                                      <StatusBadge value={item.prioridade} />
                                    </td>
                                  </tr>
                                  );
                                })
                              : null}
                          </Fragment>
                        );
                      })
                    : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function ProcessoReposicaoPage() {
  const [month, setMonth] = useState(CURRENT_MONTH);
  const [scenario, setScenario] = useState<MediaScenarioKey>("media3m");
  const [filtros, setFiltros] = useState<ReposicaoFiltros>({});
  const [classificacoes, setClassificacoes] = useState<ClassificacaoFiltros>(emptyClassificacoes);
  const [resumo, setResumo] = useState<ProcessoReposicaoResumo>(emptyResumo);
  const [rows, setRows] = useState<ProcessoReposicaoRow[]>([]);
  const [totvsPreviews, setTotvsPreviews] = useState<Record<string, TotvsPedidoPreview>>({});
  const [selectedTotvsOrder, setSelectedTotvsOrder] = useState<TotvsOrderPreview | null>(null);
  const [totvsLoading, setTotvsLoading] = useState<string | null>(null);
  const [totvsSendLoading, setTotvsSendLoading] = useState<string | null>(null);
  const [totvsSendResult, setTotvsSendResult] = useState<string | null>(null);
  const [totvsError, setTotvsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function activeFiltros(nextFiltros = filtros) {
    return Object.fromEntries(
      Object.entries(nextFiltros).filter(([, value]) => value && value !== "TODOS"),
    ) as ReposicaoFiltros;
  }

  async function loadData(selectedMonth = month, selectedFiltros = filtros) {
    setLoading(true);
    setError(null);
    try {
      const filtrosAtivos = activeFiltros(selectedFiltros);
      const [resumoData, rowsData] = await Promise.all([
        api.getProcessoReposicaoResumo(CURRENT_YEAR, selectedMonth, filtrosAtivos),
        api.getProcessoReposicaoSugestao(CURRENT_YEAR, selectedMonth, 10000, filtrosAtivos),
      ]);
      setResumo(resumoData);
      setRows(rowsData);
      setTotvsPreviews({});
      setTotvsError(null);
      setTotvsSendResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar processo de reposição");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    api.getClassificacaoFiltros().then(setClassificacoes).catch(() => setClassificacoes(emptyClassificacoes));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFiltroChange(key: keyof ReposicaoFiltros, value: string) {
    const next = { ...filtros, [key]: value || undefined };
    setFiltros(next);
    loadData(month, next);
  }

  async function handleTotvsPreview(pedidoTipo: "CURVA_A_AA" | "CURVA_BC_1" | "CURVA_BC_2") {
    setTotvsLoading(pedidoTipo);
    setTotvsError(null);
    try {
      const preview = await api.previewPedidoTotvs({
        year: CURRENT_YEAR,
        month,
        pedido_tipo: pedidoTipo,
        cenario: scenario,
        filtros: activeFiltros(),
      });
      setTotvsPreviews((current) => ({ ...current, [pedidoTipo]: preview }));
    } catch (err) {
      setTotvsError(err instanceof Error ? err.message : "Erro ao gerar previa TOTVS");
    } finally {
      setTotvsLoading(null);
    }
  }

  async function handleTotvsTestSend(pedidoTipo: "CURVA_A_AA" | "CURVA_BC_1" | "CURVA_BC_2") {
    const confirmado = window.confirm("Enviar um pedido de teste com apenas 1 SKU para a TOTVS?");
    if (!confirmado) return;

    setTotvsSendLoading(pedidoTipo);
    setTotvsError(null);
    setTotvsSendResult(null);
    try {
      const result = await api.enviarPedidoTotvs({
        year: CURRENT_YEAR,
        month,
        pedido_tipo: pedidoTipo,
        cenario: scenario,
        filtros: activeFiltros(),
        test_item: true,
        confirmar: true,
      });
      const pedidos = Array.isArray(result.pedidos) ? result.pedidos : [];
      console.log("TOTVS Response:", JSON.stringify(pedidos, null, 2));
      const firstOrder = pedidos[0] as {
        order_id?: string;
        nome_loja?: string;
        totvs?: Record<string, unknown>;
      } | undefined;
      const totvs = firstOrder?.totvs ?? {};
      const totvsOrderNumber = totvs.orderNumber ?? totvs.orderCode ?? totvs.code ?? totvs.id ?? totvs.nr_pedido ?? totvs.numero ?? null;
      const totvsMessage = totvs.message ?? totvs.mensagem ?? null;
      setTotvsSendResult(
        firstOrder
          ? `Teste enviado: ${firstOrder.order_id ?? "pedido"} (${firstOrder.nome_loja ?? "loja"})${totvsOrderNumber ? ` - Pedido TOTVS #${totvsOrderNumber}` : ""}${totvsMessage ? ` - ${totvsMessage}` : ""}`
          : "Teste enviado para a TOTVS.",
      );
      const preview = await api.previewPedidoTotvs({
        year: CURRENT_YEAR,
        month,
        pedido_tipo: pedidoTipo,
        cenario: scenario,
        filtros: activeFiltros(),
        test_item: true,
      });
      setTotvsPreviews((current) => ({ ...current, [`${pedidoTipo}_TEST`]: preview }));
    } catch (err) {
      setTotvsError(err instanceof Error ? err.message : "Erro ao enviar teste TOTVS");
    } finally {
      setTotvsSendLoading(null);
    }
  }

  async function handleTotvsFullSend(pedidoTipo: "CURVA_A_AA" | "CURVA_BC_1" | "CURVA_BC_2", cdLoja?: number) {
    const preview = totvsPreviews[pedidoTipo];
    const totalPedidos = cdLoja ? 1 : (preview?.pedidos ?? 0);
    const totalPecas = cdLoja
      ? preview?.orders?.find(o => o.cd_loja === cdLoja)?.pecas ?? 0
      : (preview?.pecas ?? 0);

    const confirmMsg = cdLoja
      ? `Enviar pedido da loja ${cdLoja} com ${formatNumber(totalPecas)} peças para a TOTVS?`
      : `Enviar TODOS os ${totalPedidos} pedidos (${formatNumber(totalPecas)} peças) para a TOTVS?\n\nEsta ação irá criar pedidos reais no sistema TOTVS.`;

    const confirmado = window.confirm(confirmMsg);
    if (!confirmado) return;

    const loadingKey = cdLoja ? `${pedidoTipo}_${cdLoja}` : `${pedidoTipo}_FULL`;
    setTotvsSendLoading(loadingKey);
    setTotvsError(null);
    setTotvsSendResult(null);

    try {
      const result = await api.enviarPedidoTotvs({
        year: CURRENT_YEAR,
        month,
        pedido_tipo: pedidoTipo,
        cenario: scenario,
        filtros: activeFiltros(),
        test_item: false,
        confirmar: true,
        cd_loja: cdLoja,
      });

      const pedidosEnviados = Array.isArray(result.pedidos) ? result.pedidos : [];
      console.log("TOTVS Full Response:", JSON.stringify(pedidosEnviados, null, 2));

      const successCount = pedidosEnviados.filter((p: { sucesso?: boolean }) => p.sucesso !== false).length;
      const errorCount = pedidosEnviados.filter((p: { sucesso?: boolean }) => p.sucesso === false).length;

      if (cdLoja) {
        const order = pedidosEnviados[0] as {
          order_id?: string;
          nome_loja?: string;
          totvs?: Record<string, unknown>;
          sucesso?: boolean;
          erro?: string;
        } | undefined;
        const totvs = order?.totvs ?? {};
        const totvsOrderNumber = totvs.orderNumber ?? totvs.orderCode ?? totvs.code ?? totvs.id ?? totvs.nr_pedido ?? totvs.numero ?? null;

        if (order?.sucesso === false) {
          setTotvsError(`Erro ao enviar pedido da loja ${cdLoja}: ${order?.erro ?? "Erro desconhecido"}`);
        } else {
          setTotvsSendResult(
            `Pedido enviado: ${order?.order_id ?? "pedido"} (${order?.nome_loja ?? "loja"})${totvsOrderNumber ? ` - Pedido TOTVS #${totvsOrderNumber}` : ""}`
          );
        }
      } else {
        if (errorCount > 0) {
          setTotvsError(`${errorCount} pedido(s) com erro. ${successCount} enviado(s) com sucesso.`);
        } else {
          setTotvsSendResult(`${successCount} pedido(s) enviado(s) com sucesso para a TOTVS!`);
        }
      }

      // Recarrega a prévia para mostrar os pedidos atualizados
      const updatedPreview = await api.previewPedidoTotvs({
        year: CURRENT_YEAR,
        month,
        pedido_tipo: pedidoTipo,
        cenario: scenario,
        filtros: activeFiltros(),
      });
      setTotvsPreviews((current) => ({ ...current, [pedidoTipo]: updatedPreview }));

    } catch (err) {
      setTotvsError(err instanceof Error ? err.message : "Erro ao enviar pedido(s) TOTVS");
    } finally {
      setTotvsSendLoading(null);
    }
  }

  const scenarioSummaries = useMemo(() => {
    const currentPieces = rows.reduce((sum, row) => sum + scenarioOrderQty(row, "media3m"), 0);
    return mediaScenarios.map((scenario) => {
      const activeRows = rows.filter((row) => scenarioOrderQty(row, scenario.key) > 0);
      const pieces = activeRows.reduce((sum, row) => sum + scenarioOrderQty(row, scenario.key), 0);
      const need = activeRows.reduce((sum, row) => sum + scenarioNeed(row, scenario.key), 0);
      const mediaTotal = activeRows.reduce((sum, row) => sum + scenarioMedia(row, scenario.key), 0);
      const lojas = new Set(activeRows.map((row) => row.cd_loja)).size;
      const curvaAAA = activeRows.filter((row) => isCurvaAAA(row.curva_completa)).reduce((sum, row) => sum + scenarioOrderQty(row, scenario.key), 0);
      const curvaBC = activeRows.filter((row) => isCurvaBC(row.curva_completa)).reduce((sum, row) => sum + scenarioOrderQty(row, scenario.key), 0);
      const addedVs3m = rows.reduce(
        (sum, row) => sum + Math.max(0, scenarioOrderQty(row, scenario.key) - scenarioOrderQty(row, "media3m")),
        0,
      );
      const recoveredRows = rows.filter((row) => scenarioOrderQty(row, scenario.key) > scenarioOrderQty(row, "media3m"));
      const reducedVs3m = rows.reduce(
        (sum, row) => sum + Math.max(0, scenarioOrderQty(row, "media3m") - scenarioOrderQty(row, scenario.key)),
        0,
      );
      return {
        ...scenario,
        skus: activeRows.length,
        lojas,
        pieces,
        need,
        mediaTotal,
        curvaAAA,
        curvaBC,
        addedVs3m,
        recoveredSkus: recoveredRows.length,
        recoveredStores: new Set(recoveredRows.map((row) => row.cd_loja)).size,
        reducedVs3m,
        deltaPieces: pieces - currentPieces,
        deltaPercent: currentPieces > 0 ? ((pieces - currentPieces) / currentPieces) * 100 : pieces > 0 ? null : 0,
      };
    });
  }, [rows]);

  const pedidos = useMemo<PedidoReposicao[]>(() => {
    const scenarioRows = rows
      .filter((row) => scenarioOrderQty(row, scenario) > 0)
      .map((row) => applyScenario(row, scenario));
    const curvaAAA = scenarioRows
      .filter((row) => isCurvaAAA(row.curva_completa))
      .map((row) => ({ ...row, qtd_pedido: Number(row.qtd_sugerida || 0) }));
    const curvaBC = scenarioRows.filter((row) => isCurvaBC(row.curva_completa));
    const primeiraBC = curvaBC
      .map((row) => ({ ...row, qtd_pedido: Math.ceil(Number(row.qtd_sugerida || 0) / 2) }))
      .filter((row) => row.qtd_pedido > 0);
    const segundaBC = curvaBC
      .map((row) => ({ ...row, qtd_pedido: Math.floor(Number(row.qtd_sugerida || 0) / 2) }))
      .filter((row) => row.qtd_pedido > 0);

    return [
      {
        titulo: "Pedido Curva A/AA",
        tipo: "CURVA_A_AA",
        subtitulo: `Pedido principal do período ${month}, priorizando ruptura e curvas de maior venda.`,
        rows: curvaAAA,
      },
      {
        titulo: "Pedido Curva B/C - 1ª quinzena",
        tipo: "CURVA_BC_1",
        subtitulo: `Primeira metade da necessidade B/C do período ${month}.`,
        rows: primeiraBC,
      },
      {
        titulo: "Pedido Curva B/C - 2ª quinzena",
        tipo: "CURVA_BC_2",
        subtitulo: `Segunda metade da necessidade B/C do período ${month}.`,
        rows: segundaBC,
      },
    ];
  }, [month, rows, scenario]);

  const selectedRows = useMemo(
    () => rows.filter((row) => scenarioOrderQty(row, scenario) > 0).map((row) => applyScenario(row, scenario)),
    [rows, scenario],
  );

  const selectedSummary = useMemo(() => ({
    skus_sugeridos: selectedRows.length,
    lojas: new Set(selectedRows.map((row) => row.cd_loja)).size,
    pecas_sugeridas: selectedRows.reduce((sum, row) => sum + Number(row.qtd_pedido || 0), 0),
    criticos: selectedRows.filter((row) => row.prioridade === "CRITICA").length,
    altos: selectedRows.filter((row) => row.prioridade === "ALTA").length,
  }), [selectedRows]);

  const selectedScenarioSummary = useMemo(
    () => scenarioSummaries.find((item) => item.key === scenario) ?? scenarioSummaries[0],
    [scenario, scenarioSummaries],
  );

  const selectedTotvsItems = (selectedTotvsOrder?.payload.items as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <PageContainer
      eyebrow="Operação"
      title="Processo de Reposição"
      description="Gere e revise a sugestão de reposição por loja, referência e SKU."
      actions={
        <>
          <span className="badge">Período atual: {month}</span>
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

      {loading ? <section className="loadingBand">Carregando processo de reposição...</section> : null}

      <section className="panel scenarioPanel">
        <div className="scenarioHeader">
          <div>
            <h2>Cenario de calculo</h2>
            <p>Escolha a media e todo o painel recalcula pedidos, totais e previa TOTVS pelo mesmo criterio.</p>
          </div>
          <span className="badge">Meta A/AA 45 dias | B/C 30 dias</span>
        </div>
        <div className="scenarioButtons" role="tablist" aria-label="Cenario de reposicao">
          {mediaScenarios.map((item) => {
            const summary = scenarioSummaries.find((summaryItem) => summaryItem.key === item.key);
            return (
              <button
                key={item.key}
                type="button"
                className={scenario === item.key ? "active" : ""}
                onClick={() => {
                  setScenario(item.key);
                  setTotvsPreviews({});
                  setSelectedTotvsOrder(null);
                  setTotvsError(null);
                }}
              >
                <strong>{item.title}</strong>
                <span>{item.subtitle}</span>
                <em>{formatNumber(summary?.pieces ?? 0)} pecas</em>
                <small>{formatNumber(summary?.skus ?? 0)} SKUs / {formatNumber(summary?.lojas ?? 0)} lojas</small>
                <small>Recupera {formatNumber(summary?.recoveredSkus ?? 0)} SKUs em {formatNumber(summary?.recoveredStores ?? 0)} lojas</small>
              </button>
            );
          })}
        </div>
        {selectedScenarioSummary ? (
          <div className="scenarioImpact">
            <span>
              <strong>{formatNumber(selectedScenarioSummary.pieces)}</strong>
              pecas no cenario
            </span>
            <span>
              <strong>{selectedScenarioSummary.deltaPieces >= 0 ? "+" : ""}{formatNumber(selectedScenarioSummary.deltaPieces)}</strong>
              vs media 3m
            </span>
            <span>
              <strong>+{formatNumber(selectedScenarioSummary.addedVs3m)}</strong>
              pecas recuperadas
            </span>
            <span>
              <strong>{formatNumber(selectedScenarioSummary.recoveredSkus)}</strong>
              SKUs recuperados
            </span>
            <span>
              <strong>{formatNumber(selectedScenarioSummary.recoveredStores)}</strong>
              lojas com gap recuperado
            </span>
            <span>
              <strong>-{formatNumber(selectedScenarioSummary.reducedVs3m)}</strong>
              reduz
            </span>
          </div>
        ) : null}
      </section>

      <section className="panel filterPanel">
        <div className="filterGrid">
          <label>
            Periodo
            <select
              value={month}
              onChange={(event) => {
                const nextMonth = event.target.value;
                setMonth(nextMonth);
                loadData(nextMonth, filtros);
              }}
            >
              {MONTH_OPTIONS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label>
            Status do produto
            <select
              value={filtros.status_produto ?? ""}
              onChange={(event) => handleFiltroChange("status_produto", event.target.value)}
            >
              <option value="">Todos</option>
              {classificacoes.status_produto.map((item) => (
                <option key={item.valor} value={item.valor}>
                  {item.valor}
                </option>
              ))}
            </select>
          </label>
          <label>
            Continuidade
            <select
              value={filtros.continuidade ?? ""}
              onChange={(event) => handleFiltroChange("continuidade", event.target.value)}
            >
              <option value="">Todas</option>
              {classificacoes.continuidade.map((item) => (
                <option key={item.valor} value={item.valor}>
                  {item.valor}
                </option>
              ))}
            </select>
          </label>
          <label>
            Linha
            <select value={filtros.linha ?? ""} onChange={(event) => handleFiltroChange("linha", event.target.value)}>
              <option value="">Todas</option>
              {classificacoes.linha.map((item) => (
                <option key={item.valor} value={item.valor}>
                  {item.valor}
                </option>
              ))}
            </select>
          </label>
          <label>
            Família
            <select value={filtros.familia ?? ""} onChange={(event) => handleFiltroChange("familia", event.target.value)}>
              <option value="">Todas</option>
              {classificacoes.familia.map((item) => (
                <option key={item.valor} value={item.valor}>
                  {item.valor}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => {
              setFiltros({});
              loadData(month, {});
            }}
            disabled={loading}
          >
            Limpar filtros
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Comparativo de cenarios de media</h2>
            <p>Simula a reposicao do periodo com media 3m, 6m sem abril/maio e 12m, usando meta de 45 dias para A/AA e 30 dias para B/C.</p>
          </div>
          <span className="badge">{month}</span>
        </div>
        {month === "2026-09" && rows.length === 0 ? (
          <section className="notice warning">
            <AlertTriangle size={20} />
            <span>Periodo 2026-09 selecionado, mas a base analitica ainda nao retornou SKUs para setembro. Quando a carga/cache de setembro estiver disponivel, este painel ja calcula os 3 cenarios.</span>
          </section>
        ) : null}
        <div className="metricGrid three">
          {scenarioSummaries.map((scenario) => (
            <MetricCard
              key={scenario.key}
              icon={<Target size={18} />}
              title={scenario.title}
              value={scenario.pieces}
              subtitle={`${formatNumber(scenario.skus)} SKUs / ${formatNumber(scenario.lojas)} lojas`}
              tone={scenario.key === "media3m" ? "blue" : scenario.key === "media6m" ? "pink" : "green"}
            />
          ))}
        </div>
        <div className="matrixWrap">
          <table className="matrixTable">
            <thead>
              <tr>
                <th>Cenario</th>
                <th>SKUs atingidos</th>
                <th>Lojas</th>
                <th>Media total</th>
                <th>Necessidade</th>
                <th>Pecas sugeridas</th>
                <th>A/AA</th>
                <th>B/C</th>
                <th>Pecas recuperadas</th>
                <th>SKUs recuperados</th>
                <th>Lojas recuperadas</th>
                <th>Reduz vs 3m</th>
                <th>Vs 3m</th>
              </tr>
            </thead>
            <tbody>
              {scenarioSummaries.map((scenario) => (
                <tr className="matrixSku" key={`${scenario.key}-row`}>
                  <td>
                    <strong>{scenario.title}</strong>
                    <span>{scenario.subtitle}</span>
                  </td>
                  <td>{formatNumber(scenario.skus)}</td>
                  <td>{formatNumber(scenario.lojas)}</td>
                  <td>{formatDecimal(scenario.mediaTotal)}</td>
                  <td>{formatNumber(scenario.need)}</td>
                  <td className="highlight-result">{formatNumber(scenario.pieces)}</td>
                  <td>{formatNumber(scenario.curvaAAA)}</td>
                  <td>{formatNumber(scenario.curvaBC)}</td>
                  <td className="highlight-green">+{formatNumber(scenario.addedVs3m)}</td>
                  <td>{formatNumber(scenario.recoveredSkus)}</td>
                  <td>{formatNumber(scenario.recoveredStores)}</td>
                  <td className="highlight-red">-{formatNumber(scenario.reducedVs3m)}</td>
                  <td>{scenario.deltaPercent === null ? "novo" : `${scenario.deltaPieces >= 0 ? "+" : ""}${formatNumber(scenario.deltaPieces)} (${formatDecimal(scenario.deltaPercent)}%)`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="metricGrid four">
        <MetricCard icon={<ClipboardList size={18} />} title="SKUs sugeridos" value={selectedSummary.skus_sugeridos} subtitle={`${formatNumber(selectedRows.length)} no cenário`} tone="pink" />
        <MetricCard icon={<PackageCheck size={18} />} title="Peças a repor" value={selectedSummary.pecas_sugeridas} subtitle="Cenário selecionado" tone="blue" />
        <MetricCard icon={<Store size={18} />} title="Lojas" value={selectedSummary.lojas} subtitle="Com sugestão no cenário" tone="gray" />
        <MetricCard icon={<Target size={18} />} title="Críticos" value={selectedSummary.criticos} subtitle={`${formatNumber(selectedSummary.altos)} alta prioridade`} tone="red" />
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Prévia TOTVS</h2>
            <p>Pedidos separados por loja, com cliente, operação, peças e valor.</p>
          </div>
          <span className="badge">{month}</span>
        </div>

        {totvsError ? (
          <section className="notice error">
            <AlertTriangle size={20} />
            <span>{totvsError}</span>
          </section>
        ) : null}

        {totvsSendResult ? (
          <section className="notice success">
            <PackageCheck size={20} />
            <span>{totvsSendResult}</span>
          </section>
        ) : null}

        <div className="filterGrid">
          {pedidos.map((pedido) => (
            <button
              key={pedido.tipo}
              type="button"
              onClick={() => handleTotvsPreview(pedido.tipo)}
              disabled={totvsLoading === pedido.tipo || loading}
            >
              <FileSearch size={17} />
              {totvsLoading === pedido.tipo ? "Gerando..." : pedido.titulo}
            </button>
          ))}
        </div>

        {Object.entries(totvsPreviews).map(([tipo, preview]) => (
          <div className="matrixWrap" key={tipo}>
            <table className="matrixTable">
              <thead>
                <tr>
                  <th>Pedido</th>
                  <th>Loja</th>
                  <th>Customer</th>
                  <th>Operação</th>
                  <th>SKUs</th>
                  <th>Peças</th>
                  <th>Valor</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr className="matrixGroup totalGeral">
                  <td>
                    <strong>{tipo}</strong>
                  </td>
                  <td>{formatNumber(preview.pedidos ?? 0)} pedidos</td>
                  <td>-</td>
                  <td>-</td>
                  <td>{formatNumber(preview.skus)}</td>
                  <td>{formatNumber(preview.pecas)}</td>
                  <td>-</td>
                  <td>
                    <div className="inlineActions">
                      <span>{preview.ready_to_send ? "Pronto" : preview.missing_config.join(", ")}</span>
                      <button
                        type="button"
                        onClick={() => handleTotvsTestSend(preview.pedido_tipo as "CURVA_A_AA" | "CURVA_BC_1" | "CURVA_BC_2")}
                        disabled={!preview.ready_to_send || Boolean(totvsSendLoading) || loading}
                      >
                        <Send size={15} />
                        {totvsSendLoading === preview.pedido_tipo ? "Enviando..." : "Teste 1 SKU"}
                      </button>
                      <button
                        type="button"
                        className="btnPrimary"
                        onClick={() => handleTotvsFullSend(preview.pedido_tipo as "CURVA_A_AA" | "CURVA_BC_1" | "CURVA_BC_2")}
                        disabled={!preview.ready_to_send || Boolean(totvsSendLoading) || loading}
                      >
                        <Send size={15} />
                        {totvsSendLoading === `${preview.pedido_tipo}_FULL` ? "Enviando..." : "Enviar Todos"}
                      </button>
                    </div>
                  </td>
                </tr>
                {(preview.orders ?? []).map((order) => {
                  const isReady = order.missing_config.length === 0;
                  const lojaLoadingKey = `${preview.pedido_tipo}_${order.cd_loja}`;
                  return (
                  <tr className="matrixSku" key={order.order_id}>
                    <td className="clickableCell" onClick={() => setSelectedTotvsOrder(order)}>{order.order_id}</td>
                    <td className="clickableCell" onClick={() => setSelectedTotvsOrder(order)}>{order.nome_loja}</td>
                    <td>{String(order.payload.customerCode ?? "-")}</td>
                    <td>{String(order.payload.operationCode ?? "-")}</td>
                    <td>{formatNumber(order.skus)}</td>
                    <td>{formatNumber(order.pecas)}</td>
                    <td>{formatNumber(order.total_amount)}</td>
                    <td>
                      <div className="inlineActions">
                        <span className={isReady ? "statusOk" : "statusPending"}>
                          {isReady ? "OK" : order.missing_config.join(", ")}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTotvsFullSend(preview.pedido_tipo as "CURVA_A_AA" | "CURVA_BC_1" | "CURVA_BC_2", order.cd_loja);
                          }}
                          disabled={!isReady || Boolean(totvsSendLoading) || loading}
                        >
                          <Send size={14} />
                          {totvsSendLoading === lojaLoadingKey ? "..." : "Enviar"}
                        </button>
                      </div>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}
      </section>

      {pedidos.map((pedido) => (
        <PedidoMatrix key={pedido.titulo} pedido={pedido} />
      ))}

      {selectedTotvsOrder ? (
        <div className="modalBackdrop" role="dialog" aria-modal="true">
          <section className="modalPanel">
            <div className="panelHeader">
              <div>
                <h2>{selectedTotvsOrder.order_id}</h2>
                <p>
                  {selectedTotvsOrder.nome_loja} · {formatNumber(selectedTotvsOrder.skus)} SKUs ·{" "}
                  {formatNumber(selectedTotvsOrder.pecas)} peças
                </p>
              </div>
              <button type="button" className="iconButton" onClick={() => setSelectedTotvsOrder(null)} aria-label="Fechar">
                <X size={18} />
              </button>
            </div>

            <div className="metricGrid four compact">
              <MetricCard icon={<Store size={18} />} title="Customer" value={String(selectedTotvsOrder.payload.customerCode ?? "-")} subtitle="Cliente TOTVS" tone="gray" />
              <MetricCard icon={<ClipboardList size={18} />} title="Operação" value={String(selectedTotvsOrder.payload.operationCode ?? "-")} subtitle="Código do pedido" tone="pink" />
              <MetricCard icon={<PackageCheck size={18} />} title="Peças" value={selectedTotvsOrder.pecas} subtitle="Quantidade total" tone="blue" />
              <MetricCard icon={<Target size={18} />} title="Valor" value={selectedTotvsOrder.total_amount} subtitle="Total do pedido" tone="red" />
            </div>

            <div className="matrixWrap modalMatrix">
              <table className="matrixTable totvsItemsTable">
                <thead>
                <tr>
                    <th>Ref</th>
                    <th>Cor</th>
                    <th>Tam</th>
                    <th>SKU</th>
                    <th>Qtd</th>
                    <th>Cob. atual</th>
                    <th>Cob. pós</th>
                    <th>Preço</th>
                    <th>Memória</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedTotvsItems.map((item, index) => {
                    const memory = (item.calculationMemory ?? {}) as Record<string, unknown>;
                    const memoryText = `Nec ${formatNumber(Number(memory.necessidade ?? 0))} - Ent ${formatNumber(Number(memory.entradaTotal ?? 0))} - Pend ${formatNumber(Number(memory.jaProgramado ?? 0))} = Ped ${formatNumber(Number(memory.pedidoFinal ?? item.quantity ?? 0))}`;
                    return (
                      <tr className="matrixSku" key={`${String(item.productCode)}-${index}`}>
                        <td>{String(item.reference ?? "-")}</td>
                        <td title={String(item.color ?? "-")}>{String(item.color ?? "-")}</td>
                        <td>{String(item.size ?? "-")}</td>
                        <td>{String(item.productCode ?? "-")}</td>
                        <td>{formatNumber(Number(item.quantity ?? 0))}</td>
                        <td>{formatDecimal(Number(item.currentCoverage ?? 0))}m</td>
                        <td>{formatDecimal(Number(item.projectedCoverage ?? 0))}m</td>
                        <td>{formatNumber(Number(item.price ?? 0))}</td>
                        <td title={memoryText}>{memoryText}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      ) : null}
    </PageContainer>
  );
}
