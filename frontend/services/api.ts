import type {
  Alerta,
  AnaliseLojaMesRow,
  CacheStatus,
  ClassificacaoFiltros,
  ConfigReposicao,
  DiagnosticoProdutoFiltros,
  DiagnosticoProdutoRow,
  EvolucaoMensalRow,
  LojaRankingRow,
  MatrizReposicaoRow,
  ProcessoReposicaoResumo,
  ProcessoReposicaoRow,
  ReposicaoDashboard,
  ReposicaoFiltros,
  ReposicaoPedido,
  ReposicaoPedidoDetalhes,
  ReposicaoPedidoFiltros,
  ReposicaoStatus,
  ResumoGeral,
  SkuSemReposicaoRow,
  SkuSemReposicaoResumo,
  TotvsConfigStatus,
  TotvsPedidoPreview,
} from "../types/reposicao";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Erro ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function withParams(path: string, params: Record<string, string | number | undefined>) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) searchParams.set(key, String(value));
  });
  return `${path}?${searchParams.toString()}`;
}

export const api = {
  getClassificacaoFiltros() {
    return request<ClassificacaoFiltros>("/api/filtros/classificacoes");
  },

  getResumoGeral(year: number, month?: string, filtros?: ReposicaoFiltros) {
    return request<ResumoGeral>(withParams("/api/dashboard/resumo-geral", { year, month, ...filtros }));
  },

  getEvolucaoMensal(year: number, filtros?: ReposicaoFiltros) {
    return request<EvolucaoMensalRow[]>(
      withParams("/api/dashboard/evolucao-mensal", { year, ...filtros }),
    );
  },

  getLojasRanking(year: number, month?: string, limit = 50, filtros?: ReposicaoFiltros) {
    return request<LojaRankingRow[]>(
      withParams("/api/dashboard/lojas-ranking", { year, month, limit, ...filtros }),
    );
  },

  getMatrizReposicao(year: number, month?: string, limit?: number, filtros?: ReposicaoFiltros) {
    return request<MatrizReposicaoRow[]>(
      withParams("/api/analise/matriz-reposicao", { year, month, limit, ...filtros }),
    );
  },

  getDiagnosticoProduto(filtros: DiagnosticoProdutoFiltros) {
    return request<DiagnosticoProdutoRow[]>(
      withParams("/api/analise/diagnostico-produto", {
        year: filtros.year ?? 2026,
        mes_inicio: filtros.mes_inicio,
        mes_fim: filtros.mes_fim,
        cd_loja: filtros.cd_loja,
        referencia: filtros.referencia,
        cor: filtros.cor,
        tamanho: filtros.tamanho,
        limit: filtros.limit,
      }),
    );
  },

  getSkusSemReposicao(year: number, cdLoja?: number, limit = 500, filtros?: ReposicaoFiltros) {
    return request<SkuSemReposicaoRow[]>(
      withParams("/api/analise/skus-sem-reposicao", { year, cd_loja: cdLoja, limit, ...filtros }),
    );
  },

  getSkusSemReposicaoResumo(year: number, cdLoja?: number, filtros?: ReposicaoFiltros) {
    return request<SkuSemReposicaoResumo>(
      withParams("/api/analise/skus-sem-reposicao/resumo", { year, cd_loja: cdLoja, ...filtros }),
    );
  },

  getProcessoReposicaoResumo(year: number, month?: string, filtros?: ReposicaoFiltros) {
    return request<ProcessoReposicaoResumo>(
      withParams("/api/processo-reposicao/resumo", { year, month, ...filtros }),
    );
  },

  getProcessoReposicaoSugestao(year: number, month?: string, limit = 1000, filtros?: ReposicaoFiltros) {
    return request<ProcessoReposicaoRow[]>(
      withParams("/api/processo-reposicao/sugestao", { year, month, limit, ...filtros }),
    );
  },

  getTotvsConfigStatus() {
    return request<TotvsConfigStatus>("/api/totvs/config-status");
  },

  previewPedidoTotvs(payload: {
    year: number;
    month: string;
    pedido_tipo: "CURVA_A_AA" | "CURVA_BC_1" | "CURVA_BC_2";
    filtros?: ReposicaoFiltros;
    test_item?: boolean;
  }) {
    return request<TotvsPedidoPreview>("/api/processo-reposicao/pedido-totvs/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  enviarPedidoTotvs(payload: {
    year: number;
    month: string;
    pedido_tipo: "CURVA_A_AA" | "CURVA_BC_1" | "CURVA_BC_2";
    filtros?: ReposicaoFiltros;
    test_item?: boolean;
    cd_loja?: number;
    confirmar: true;
  }) {
    return request<Record<string, unknown>>("/api/processo-reposicao/pedido-totvs/enviar", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getAlertas(month?: string) {
    return request<Alerta[]>(withParams("/api/dashboard/alertas", { month }));
  },

  getAnalisePorMes(mes: string) {
    return request<AnaliseLojaMesRow[]>(`/api/analise/por-mes/${mes}`);
  },

  getAnalisePorLoja(cdLoja: number, year: number) {
    return request<AnaliseLojaMesRow[]>(
      withParams(`/api/analise/por-loja/${cdLoja}`, { year }),
    );
  },

  getCacheStatus() {
    return request<CacheStatus>("/api/cache/status");
  },

  atualizarCache() {
    return request<Record<string, unknown>>("/api/cache/atualizar", { method: "POST" });
  },

  getConfig() {
    return request<ConfigReposicao>("/api/config/meses-relevantes");
  },

  salvarConfig(config: ConfigReposicao) {
    return request<ConfigReposicao>("/api/config/meses-relevantes", {
      method: "POST",
      body: JSON.stringify(config),
    });
  },

  getNecessidadeZerada(limit = 200) {
    return request<unknown[]>(withParams("/api/analise/necessidade-zerada", { limit }));
  },

  getReferenciasMorrendo(limit = 100) {
    return request<unknown[]>(withParams("/api/micro/referencias-morrendo", { limit }));
  },

  // ============================================================
  // Acompanhamento de Reposição
  // ============================================================

  getReposicaoDashboard(filtros?: ReposicaoPedidoFiltros) {
    return request<ReposicaoDashboard>(
      withParams("/api/reposicao/dashboard", { mes: filtros?.mes, cd_loja: filtros?.cd_loja }),
    );
  },

  getReposicaoPedidos(filtros?: ReposicaoPedidoFiltros & { limit?: number }) {
    return request<ReposicaoPedido[]>(
      withParams("/api/reposicao/pedidos", {
        mes: filtros?.mes,
        cd_loja: filtros?.cd_loja,
        status: filtros?.status,
        pedido_tipo: filtros?.pedido_tipo,
        limit: filtros?.limit,
      }),
    );
  },

  getReposicaoPedidoDetalhes(pedidoId: number) {
    return request<ReposicaoPedidoDetalhes>(`/api/reposicao/pedidos/${pedidoId}`);
  },

  atualizarStatusPedido(pedidoId: number, status: ReposicaoStatus, options?: { observacao?: string; usuario?: string; atualizar_itens?: boolean }) {
    return request<{ success: boolean; status_anterior: string; status_novo: string }>(
      `/api/reposicao/pedidos/${pedidoId}/status`,
      {
        method: "PUT",
        body: JSON.stringify({ status, ...options }),
      },
    );
  },

  atualizarStatusItem(itemId: number, status: ReposicaoStatus, options?: { observacao?: string; usuario?: string }) {
    return request<{ success: boolean; status_anterior: string; status_novo: string }>(
      `/api/reposicao/itens/${itemId}/status`,
      {
        method: "PUT",
        body: JSON.stringify({ status, ...options }),
      },
    );
  },
};
