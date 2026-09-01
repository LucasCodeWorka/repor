"use client";

import { AlertTriangle, Microscope, RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { MetricCard, formatNumber } from "../../components/cards/MetricCard";
import { MultiSelect } from "../../components/inputs/MultiSelect";
import { PageContainer } from "../../components/layout/PageContainer";
import { api } from "../../services/api";
import type {
  DiagnosticoProdutoFiltros,
  DiagnosticoProdutoOpcoes,
  DiagnosticoProdutoRow,
} from "../../types/reposicao";

const YEAR = 2026;
const monthOptions = Array.from({ length: 12 }, (_, index) => `2026-${String(index + 1).padStart(2, "0")}`);
const emptyOpcoes: DiagnosticoProdutoOpcoes = {
  lojas: [],
  referencias: [],
  cores: [],
  tamanhos: [],
};

function statusClass(status: string) {
  if (status === "ATENDIDO") return "statusOk";
  if (status === "ATENDIDO PARCIAL" || status === "ENTROU SEM NECESSIDADE") return "statusWarn";
  if (status === "TINHA NECESSIDADE E FALTOU" || status === "POSSIVEL DEMANDA PERDIDA") return "statusPending";
  return "statusNeutral";
}

function normalizeSearch(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export default function DiagnosticoProdutoPage() {
  const [filtros, setFiltros] = useState<DiagnosticoProdutoFiltros>({
    year: YEAR,
    mes_inicio: "2026-01",
    mes_fim: "2026-12",
    limit: 1000,
  });
  const [lojaInput, setLojaInput] = useState("");
  const [referencias, setReferencias] = useState<string[]>([]);
  const [cores, setCores] = useState<string[]>([]);
  const [tamanhos, setTamanhos] = useState<string[]>([]);
  const [opcoes, setOpcoes] = useState<DiagnosticoProdutoOpcoes>(emptyOpcoes);
  const [rows, setRows] = useState<DiagnosticoProdutoRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingOpcoes, setLoadingOpcoes] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const resumo = useMemo(() => {
    return rows.reduce(
      (acc, row) => {
        acc.necessidade += row.necessidade || 0;
        acc.entrada += row.entrada_total || 0;
        acc.faltou += row.faltou || 0;
        acc.semNecessidade += row.entrada_sem_necessidade || 0;
        if (row.diagnostico === "POSSIVEL DEMANDA PERDIDA") acc.perdida += 1;
        if (row.diagnostico === "TINHA NECESSIDADE E FALTOU") acc.ruptura += 1;
        acc.skus.add(`${row.cd_loja}-${row.cd_produto}`);
        acc.lojas.add(row.cd_loja);
        return acc;
      },
      {
        necessidade: 0,
        entrada: 0,
        faltou: 0,
        semNecessidade: 0,
        perdida: 0,
        ruptura: 0,
        skus: new Set<string>(),
        lojas: new Set<number>(),
      },
    );
  }, [rows]);

  function handleChange(key: keyof DiagnosticoProdutoFiltros, value: string) {
    setFiltros((current) => ({ ...current, [key]: value || undefined }));
  }

  function lojaCodigoSelecionado() {
    if (!lojaInput.trim()) return undefined;
    const codeMatch = lojaInput.match(/^(\d+)/);
    if (codeMatch) return codeMatch[1];
    const normalizedInput = normalizeSearch(lojaInput);
    const loja = opcoes.lojas.find((item) => normalizeSearch(item.nome_loja).includes(normalizedInput));
    return loja ? String(loja.cd_loja) : undefined;
  }

  useEffect(() => {
    setLoadingOpcoes(true);
    const timeout = window.setTimeout(() => {
      api
        .getDiagnosticoProdutoOpcoes({
          ...filtros,
          year: filtros.year ?? YEAR,
          cd_loja: lojaCodigoSelecionado(),
          referencia: referencias.length > 0 ? referencias : undefined,
          cor: cores.length > 0 ? cores : undefined,
          tamanho: tamanhos.length > 0 ? tamanhos : undefined,
        })
        .then(setOpcoes)
        .catch(() => setOpcoes(emptyOpcoes))
        .finally(() => setLoadingOpcoes(false));
    }, 250);

    return () => window.clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.mes_inicio, filtros.mes_fim, referencias, cores, tamanhos, lojaInput]);

  async function loadData() {
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const data = await api.getDiagnosticoProduto({
        ...filtros,
        year: filtros.year ?? YEAR,
        cd_loja: lojaCodigoSelecionado(),
        referencia: referencias.length > 0 ? referencias : undefined,
        cor: cores.length > 0 ? cores : undefined,
        tamanho: tamanhos.length > 0 ? tamanhos : undefined,
        limit: filtros.limit ?? 1000,
      });
      setRows(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar diagnostico do produto");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageContainer
      eyebrow="Analise minuciosa"
      title="Diagnostico por Produto"
      description="Filtre loja, referencia, cor e tamanho para entender se havia necessidade, se faltou, se entrou sem necessidade ou se a demanda pode ter sido perdida."
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

      <section className="panel filterPanel">
        <div className="panelHeader">
          <div>
            <h2>Filtro do diagnostico</h2>
            <p>Exemplo: loja Dom Luis, referencia do produto, cor Branco/Preto/Nude e tamanho M.</p>
          </div>
          <span className="badge">{rows.length} linhas</span>
        </div>
        <div className="diagnosticFilters">
          <div className="filterRow">
            <label className="small">
              Mes inicial
              <select
                value={filtros.mes_inicio ?? ""}
                onChange={(event) => handleChange("mes_inicio", event.target.value)}
              >
                {monthOptions.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </label>
            <label className="small">
              Mes final
              <select
                value={filtros.mes_fim ?? ""}
                onChange={(event) => handleChange("mes_fim", event.target.value)}
              >
                {monthOptions.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </label>
            <label className="large">
              Loja
              <select
                value={lojaInput}
                onChange={(event) => setLojaInput(event.target.value)}
              >
                <option value="">Todas as lojas</option>
                {opcoes.lojas.map((item) => (
                  <option key={item.cd_loja} value={`${item.cd_loja} - ${item.nome_loja}`}>
                    {item.cd_loja} - {item.nome_loja}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="filterRow">
            <label className="large">
              Referencia
              <MultiSelect
                options={opcoes.referencias.map((r) => ({ value: r.referencia, label: `${r.referencia} - ${r.descricao_produto}`, shortLabel: r.referencia }))}
                value={referencias}
                onChange={setReferencias}
                placeholder="Selecione..."
                loading={loadingOpcoes}
              />
            </label>
            <label className="large">
              Cor
              <MultiSelect
                options={opcoes.cores.map((c) => ({ value: c.valor, label: c.valor }))}
                value={cores}
                onChange={setCores}
                placeholder="Selecione..."
                loading={loadingOpcoes}
              />
            </label>
            <label className="medium">
              Tamanho
              <MultiSelect
                options={opcoes.tamanhos.map((t) => ({ value: t.valor, label: t.valor }))}
                value={tamanhos}
                onChange={setTamanhos}
                placeholder="Selecione..."
                loading={loadingOpcoes}
              />
            </label>
            <div className="filterActions">
              <button type="button" className="btnPrimary" onClick={loadData} disabled={loading}>
                <Search size={16} />
                Gerar diagnostico
              </button>
              <button
                type="button"
                onClick={() => {
                  setLojaInput("");
                  setReferencias([]);
                  setCores([]);
                  setTamanhos([]);
                  setFiltros({
                    year: YEAR,
                    mes_inicio: "2026-01",
                    mes_fim: "2026-12",
                    limit: 1000,
                  });
                }}
                disabled={loading}
              >
                Limpar
              </button>
            </div>
          </div>
        </div>
      </section>

      {loading ? <section className="loadingBand">Gerando diagnostico...</section> : null}

      {rows.length > 0 ? (
        <>
          <section className="metricGrid dashboardMetrics">
            <MetricCard icon={<Microscope size={18} />} title="SKUs analisados" value={resumo.skus.size} subtitle={`${resumo.lojas.size} lojas`} tone="pink" />
            <MetricCard title="Necessidade" value={resumo.necessidade} subtitle="Pecas que deveria repor" tone="blue" />
            <MetricCard title="Entrada total" value={resumo.entrada} subtitle="Periodo + atrasada + sem lote" tone="green" />
            <MetricCard title="Faltou" value={resumo.faltou} subtitle={`${resumo.ruptura} linhas com ruptura`} tone="red" />
            <MetricCard title="Sem necessidade" value={resumo.semNecessidade} subtitle="Entrada sem necessidade calculada" tone="amber" />
            <MetricCard title="Demanda perdida" value={resumo.perdida} subtitle="Sinal historico sem necessidade atual" tone="gray" />
          </section>

          <section className="panel">
            <div className="panelHeader">
              <div>
                <h2>Tabela de diagnostico</h2>
                <p>Mostra mes a mes como estava o SKU na loja e a leitura gerada pela regra.</p>
              </div>
              <span className="badge">{rows.length} registros</span>
            </div>
            <div className="tableWrap diagnosticTableWrap">
              <table className="diagnosticTable">
                <thead>
                  <tr>
                    <th>Mes</th>
                    <th>Loja</th>
                    <th>Referencia</th>
                    <th>Cor</th>
                    <th>Tam</th>
                    <th>SKU</th>
                    <th>Curva</th>
                    <th>Venda 3m</th>
                    <th>Media</th>
                    <th>Minimo</th>
                    <th>Saldo</th>
                    <th>Nec.</th>
                    <th>Entrada</th>
                    <th>Sem nec.</th>
                    <th>Faltou</th>
                    <th>Ult. nec.</th>
                    <th>Ult. ent.</th>
                    <th>Diagnostico</th>
                    <th>Leitura</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={`${row.mes}-${row.cd_loja}-${row.cd_produto}`} className="diagnosticRow">
                      <td>{row.mes}</td>
                      <td className="textCell">{row.nome_loja}</td>
                      <td className="textCell">
                        <strong>{row.referencia}</strong>
                        <em>{row.descricao_produto}</em>
                      </td>
                      <td>{row.cor || "-"}</td>
                      <td>{row.tamanho || "-"}</td>
                      <td>{row.cd_produto}</td>
                      <td>{row.curva_completa || "-"}</td>
                      <td>{formatNumber(row.vendas_3m)}</td>
                      <td>{formatNumber(row.media_mensal)}</td>
                      <td>{formatNumber(row.estoque_minimo)}</td>
                      <td>{formatNumber(row.saldo_inicial)}</td>
                      <td>{formatNumber(row.necessidade)}</td>
                      <td>{formatNumber(row.entrada_total)}</td>
                      <td>{formatNumber(row.entrada_sem_necessidade)}</td>
                      <td>{formatNumber(row.faltou)}</td>
                      <td>{row.ultimo_mes_com_necessidade_anterior ?? "-"}</td>
                      <td>{row.ultimo_mes_com_entrada_anterior ?? "-"}</td>
                      <td className={statusClass(row.diagnostico)}>{row.diagnostico}</td>
                      <td className="textCell">{row.leitura}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}

      {!searched && !loading ? (
        <section className="notice">
          <AlertTriangle size={20} />
          <span>Selecione pelo menos uma <strong>loja</strong> ou <strong>referencia</strong> e clique em "Gerar diagnostico".</span>
        </section>
      ) : null}

      {searched && !loading && rows.length === 0 ? (
        <section className="notice">
          <AlertTriangle size={20} />
          <span>Nenhum SKU encontrado para esse filtro. Confira loja, referencia, cor e tamanho.</span>
        </section>
      ) : null}
    </PageContainer>
  );
}
