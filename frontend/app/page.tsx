"use client";

import { AlertTriangle, Boxes, CheckCircle2, Clock3, Filter, Package, PackageSearch, RefreshCw, Store, Tag } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { MetricCard, formatNumber, formatPercent } from "../components/cards/MetricCard";
import { EvolucaoMensal } from "../components/charts/EvolucaoMensal";
import { PageContainer } from "../components/layout/PageContainer";
import { MatrizReposicao } from "../components/tables/MatrizReposicao";
import { MatrizSkusSemReposicao } from "../components/tables/MatrizSkusSemReposicao";
import { api } from "../services/api";
import type {
  ClassificacaoFiltros,
  EvolucaoMensalRow,
  MatrizReposicaoRow,
  ReposicaoFiltros,
  ResumoGeral,
  SkuSemReposicaoRow,
  SkuSemReposicaoResumo,
} from "../types/reposicao";

const YEAR = 2026;
const emptyClassificacoes: ClassificacaoFiltros = {
  status_produto: [],
  continuidade: [],
  linha: [],
  familia: [],
};

export default function DashboardPage() {
  const [month, setMonth] = useState("2026-06");
  const [filtros, setFiltros] = useState<ReposicaoFiltros>({});
  const [classificacoes, setClassificacoes] = useState<ClassificacaoFiltros>(emptyClassificacoes);
  const [resumo, setResumo] = useState<ResumoGeral | null>(null);
  const [evolucao, setEvolucao] = useState<EvolucaoMensalRow[]>([]);
  const [matriz, setMatriz] = useState<MatrizReposicaoRow[]>([]);
  const [skusSemReposicao, setSkusSemReposicao] = useState<SkuSemReposicaoRow[]>([]);
  const [resumoSkusSemReposicao, setResumoSkusSemReposicao] = useState<SkuSemReposicaoResumo>({
    total: 0,
    perdidos: 0,
    risco: 0,
    recuperando: 0,
    empresas: 0,
  });
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
      const [resumoData, evolucaoData, matrizData, skusSemReposicaoResumoData, skusSemReposicaoData] = await Promise.all([
        api.getResumoGeral(YEAR, selectedMonth, filtrosAtivos),
        api.getEvolucaoMensal(YEAR, filtrosAtivos),
        api.getMatrizReposicao(YEAR, selectedMonth, undefined, filtrosAtivos),
        api.getSkusSemReposicaoResumo(YEAR, undefined, filtrosAtivos),
        api.getSkusSemReposicao(YEAR, undefined, 1000, filtrosAtivos),
      ]);
      setResumo(resumoData);
      setEvolucao(evolucaoData);
      setMatriz(matrizData);
      setResumoSkusSemReposicao(skusSemReposicaoResumoData);
      setSkusSemReposicao(skusSemReposicaoData);
      if (!evolucaoData.some((item) => item.mes === selectedMonth) && evolucaoData[0]) {
        setMonth(evolucaoData[evolucaoData.length - 1].mes);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    api
      .getClassificacaoFiltros()
      .then(setClassificacoes)
      .catch(() => setClassificacoes(emptyClassificacoes));
  }, []);

  const monthOptions = useMemo(
    () =>
      evolucao.length
        ? evolucao.map((item) => item.mes)
        : Array.from({ length: 12 }, (_, index) => `2026-${String(index + 1).padStart(2, "0")}`),
    [evolucao],
  );

  function handleMonthChange(value: string) {
    setMonth(value);
    loadData(value, filtros);
  }

  function handleFiltroChange(key: keyof ReposicaoFiltros, value: string) {
    const next = { ...filtros, [key]: value || undefined };
    setFiltros(next);
    loadData(month, next);
  }

  return (
    <PageContainer
      eyebrow="Inteligencia PCP"
      title="Dashboard de Reposicao"
      description="Necessidade, entradas, ruptura e morte silenciosa por loja."
      actions={
        <>
          <select value={month} onChange={(event) => handleMonthChange(event.target.value)}>
            {monthOptions.map((item) => (
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

      {loading ? <section className="loadingBand">Carregando indicadores...</section> : null}

      <section className="panel filterPanel">
        <div className="filterGroups">
          {/* Grupo: Localização */}
          <div className="filterGroup">
            <div className="filterGroupTitle">
              <Store size={14} />
              Localização
            </div>
            <div className="filterGrid">
              <label>
                Loja
                <input
                  inputMode="numeric"
                  placeholder="Código da loja"
                  value={filtros.cd_loja ?? ""}
                  onChange={(event) => handleFiltroChange("cd_loja", event.target.value)}
                />
              </label>
              <label>
                Referência
                <input
                  placeholder="Ex: 103605"
                  value={filtros.referencia ?? ""}
                  onChange={(event) => handleFiltroChange("referencia", event.target.value)}
                />
              </label>
            </div>
          </div>

          {/* Grupo: Classificação do Produto */}
          <div className="filterGroup">
            <div className="filterGroupTitle">
              <Tag size={14} />
              Classificação
            </div>
            <div className="filterGrid">
              <label>
                Status
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
            </div>
          </div>

          {/* Grupo: Filtros Especiais */}
          <div className="filterGroup">
            <div className="filterGroupTitle">
              <Filter size={14} />
              Especial
            </div>
            <div className="filterGrid">
              <label>
                Entrada sem necessidade
                <select
                  value={filtros.somente_entrada_sem_necessidade ?? ""}
                  onChange={(event) => handleFiltroChange("somente_entrada_sem_necessidade", event.target.value)}
                >
                  <option value="">Todos</option>
                  <option value="true">Somente sim</option>
                </select>
              </label>
            </div>
          </div>
        </div>

        <div className="filterActions">
          <button
            type="button"
            onClick={() => {
              setFiltros({});
              loadData(month, {});
            }}
            disabled={loading}
          >
            Limpar filtros
            {Object.keys(activeFiltros()).length > 0 && (
              <span className="activeFiltersCount">{Object.keys(activeFiltros()).length}</span>
            )}
          </button>
        </div>
      </section>

      <section className="metricGrid dashboardMetrics">
        <MetricCard
          icon={<PackageSearch size={18} />}
          title="Necessidade Total"
          value={resumo?.necessidade ?? 0}
          subtitle={`${formatNumber(resumo?.skus_demanda)} SKUs com demanda`}
          tone="pink"
        />
        <MetricCard
          icon={<CheckCircle2 size={18} />}
          title="Entrada Periodo"
          value={resumo?.entrada_periodo ?? 0}
          subtitle={`${formatNumber(resumo?.skus_entrada_periodo)} SKUs com demanda receberam`}
          percentage={resumo?.pct_periodo ?? 0}
          tone="blue"
        />
        <MetricCard
          icon={<Clock3 size={18} />}
          title="Entrada Atrasada"
          value={resumo?.entrada_atrasada ?? 0}
          subtitle={`${formatNumber(resumo?.skus_entrada_atrasada)} SKUs com demanda receberam`}
          percentage={resumo?.pct_atrasada ?? 0}
          tone="amber"
        />
        <MetricCard
          icon={<Boxes size={18} />}
          title="Sem Lote"
          value={resumo?.entrada_sem_lote ?? 0}
          subtitle={`${formatNumber(resumo?.skus_entrada_sem_lote)} SKUs com demanda receberam`}
          percentage={resumo?.pct_sem_lote ?? 0}
          tone="gray"
        />
        <MetricCard
          icon={<Boxes size={18} />}
          title="Entrou sem necessidade"
          value={resumo?.entrada_sem_necessidade ?? 0}
          subtitle={`${formatNumber(resumo?.skus_entrada_sem_necessidade)} SKUs sem necessidade receberam`}
          tone="amber"
        />
        <MetricCard
          icon={<AlertTriangle size={18} />}
          title="Faltou"
          value={resumo?.faltou ?? 0}
          subtitle={`${formatNumber(resumo?.skus_faltantes)} SKUs faltantes | Atend SKU: ${formatPercent(resumo?.taxa_atendimento)}`}
          tone={(resumo?.taxa_atendimento ?? 0) >= 100 ? "green" : "red"}
        />
      </section>

      <section className="panel">
          <div className="panelHeader">
            <div>
              <h2>Evolucao Mensal</h2>
              <p>Necessidade, entrada total e falta ao longo de {YEAR}.</p>
            </div>
            <span className="badge">{evolucao.length} meses</span>
          </div>
          <EvolucaoMensal data={evolucao} />
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Matriz de Reposicao</h2>
            <p>
              Empresa &gt; Referencia &gt; Cor/Tamanho. Necessidade = max(0, estoque minimo - saldo inicial).
              Estoque minimo: Curva A/AA usa media mensal x 1,5; Curva B/C usa a propria media mensal.
              Exemplo Curva A: media 14, estoque minimo 21 e saldo 10 geram necessidade de 11 pecas.
            </p>
          </div>
        </div>
        <MatrizReposicao data={matriz} resumo={resumo} />
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>SKUs sem Reposição</h2>
            <p>Produtos que tiveram necessidade, ficaram abaixo do mínimo e não foram recompostos por empresa.</p>
          </div>
          <span className="badge">{formatNumber(resumoSkusSemReposicao.total)} SKUs</span>
        </div>

        <section className="metricGrid four">
          <MetricCard title="SKUs analisados" value={resumoSkusSemReposicao.total} subtitle="Com falta identificada" tone="pink" />
          <MetricCard title="Perdidos" value={resumoSkusSemReposicao.perdidos} subtitle="Venda caiu após ruptura" tone="red" />
          <MetricCard title="Em risco" value={resumoSkusSemReposicao.risco} subtitle="Sem reposição suficiente" tone="amber" />
          <MetricCard title="Empresas afetadas" value={resumoSkusSemReposicao.empresas} subtitle="Contextos loja/SKU" tone="gray" />
        </section>

        <MatrizSkusSemReposicao data={skusSemReposicao} resumo={resumoSkusSemReposicao} />
      </section>
    </PageContainer>
  );
}
