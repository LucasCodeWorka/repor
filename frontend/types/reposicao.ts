export type ResumoGeral = {
  necessidade: number;
  entrada_periodo: number;
  entrada_atrasada: number;
  entrada_sem_lote: number;
  entrada_total: number;
  entrada_sem_necessidade: number;
  faltou: number;
  skus_demanda: number;
  skus_atendidos: number;
  skus_faltantes: number;
  skus_entrada_periodo: number;
  skus_entrada_atrasada: number;
  skus_entrada_sem_lote: number;
  skus_entrada_sem_necessidade: number;
  skus_ok: number;
  skus_parcial: number;
  skus_zerados: number;
  taxa_atendimento: number | null;
  pct_periodo: number;
  pct_atrasada: number;
  pct_sem_lote: number;
  primeiro_mes?: string | null;
  ultimo_mes?: string | null;
};

export type EvolucaoMensalRow = {
  mes: string;
  necessidade: number;
  entrada_periodo: number;
  entrada_atrasada: number;
  entrada_sem_lote: number;
  entrada_total: number;
  faltou: number;
  skus_demanda: number;
  skus_atendidos: number;
  skus_faltantes: number;
  taxa_atendimento: number | null;
};

export type LojaRankingRow = {
  cd_loja: number;
  nome_loja: string;
  necessidade: number;
  entrada_total: number;
  faltou: number;
  taxa_atendimento: number | null;
  skus_demanda: number;
  skus_atendidos: number;
  skus_faltantes: number;
  skus_entrada_periodo: number;
  skus_entrada_atrasada: number;
  skus_entrada_sem_lote: number;
  skus_zerados: number;
};

export type AnaliseLojaMesRow = {
  id?: number;
  mes: string;
  cd_loja: number;
  nome_loja: string;
  qtd_skus_demanda: number;
  necessidade_total: number;
  entrada_periodo: number;
  entrada_atrasada: number;
  entrada_sem_lote: number;
  entrada_total: number;
  faltou: number;
  taxa_atendimento: number | null;
  skus_atendidos?: number;
  skus_faltantes?: number;
  skus_entrada_periodo?: number;
  skus_entrada_atrasada?: number;
  skus_entrada_sem_lote?: number;
  skus_ok: number;
  skus_parcial: number;
  skus_zerados: number;
};

export type Alerta = {
  tipo: string;
  severidade: "critico" | "alto" | "medio" | "baixo";
  mensagem: string;
  dados: Record<string, unknown>;
  criado_em: string;
};

export type CacheStatus = {
  status: string;
  iniciado_em: string | null;
  finalizado_em: string | null;
  erro: string | null;
  cache?: {
    atualizado_em: string | null;
    registros_resumo: number;
    primeiro_mes: string | null;
    ultimo_mes: string | null;
  };
};

export type ConfigReposicao = {
  meses_media: number;
  multiplicador_estoque_minimo: number;
  // Multiplicadores por curva
  multiplicador_curva_aa?: number;
  multiplicador_curva_a?: number;
  multiplicador_curva_b?: number;
  multiplicador_curva_c?: number;
  // Meses selecionados para calculo
  meses_selecionados?: string[];
  modo_meses?: "ultimos_3" | "ultimos_6" | "customizado";
};

export type MatrizReposicaoRow = {
  mes: string;
  cd_loja: number;
  nome_loja: string;
  referencia: string;
  descricao_produto: string;
  cd_produto: number;
  status_produto?: string | null;
  continuidade?: string | null;
  linha?: string | null;
  familia?: string | null;
  cor: string;
  tamanho: string;
  curva_completa: string;
  vendas_3m: number;
  media_mensal: number;
  estoque_minimo: number;
  saldo_inicial: number;
  necessidade: number;
  entrada_periodo: number;
  entrada_atrasada: number;
  entrada_sem_lote: number;
  entrada_total: number;
  entrada_sem_necessidade: number;
  faltou: number;
  skus_demanda: number;
  skus_atendidos: number;
  skus_faltantes: number;
  skus_entrada_sem_necessidade: number;
  status_reposicao: string;
};

export type DiagnosticoProdutoRow = {
  mes: string;
  cd_loja: number;
  nome_loja: string;
  referencia: string;
  descricao_produto: string;
  cd_produto: number;
  cor: string;
  tamanho: string;
  curva_completa: string;
  vendas_3m: number;
  media_mensal: number;
  estoque_minimo: number;
  saldo_inicial: number;
  necessidade: number;
  entrada_periodo: number;
  entrada_atrasada: number;
  entrada_sem_lote: number;
  entrada_total: number;
  entrada_sem_necessidade: number;
  faltou: number;
  status_reposicao: string;
  maior_venda_3m_anterior: number | null;
  ultimo_mes_com_estoque_anterior: string | null;
  ultimo_mes_com_necessidade_anterior: string | null;
  ultimo_mes_com_entrada_anterior: string | null;
  diagnostico: string;
  leitura: string;
};

export type DiagnosticoProdutoFiltros = {
  year?: number;
  mes_inicio?: string;
  mes_fim?: string;
  cd_loja?: string;
  referencia?: string | string[];
  cor?: string | string[];
  tamanho?: string | string[];
  limit?: number;
};

export type DiagnosticoProdutoOpcoes = {
  lojas: Array<{
    cd_loja: number;
    nome_loja: string;
    qtd_registros: number;
  }>;
  referencias: Array<{
    referencia: string;
    descricao_produto: string;
    qtd_skus: number;
  }>;
  cores: Array<{
    valor: string;
    qtd_registros: number;
  }>;
  tamanhos: Array<{
    valor: string;
    qtd_registros: number;
  }>;
};

export type SkuSemReposicaoRow = {
  empresa: string;
  referencia: string;
  status_produto?: string | null;
  continuidade?: string | null;
  linha?: string | null;
  familia?: string | null;
  cor: string;
  tamanho: string;
  sku: number;
  ultima_venda_antes_ruptura: string | null;
  media_venda_antes_ruptura: number;
  data_ultima_entrada: string | null;
  quantidade_ultima_entrada: number;
  data_inicio_falta: string;
  necessidade_identificada: number;
  quantidade_reposta_depois: number;
  dias_sem_reposicao: number;
  venda_apos_ruptura: number;
  status: "PERDIDO" | "EM RISCO" | "RECUPERANDO" | string;
};

export type SkuSemReposicaoResumo = {
  total: number;
  perdidos: number;
  risco: number;
  recuperando: number;
  empresas: number;
  data_ultima_entrada?: string | null;
  data_inicio_falta?: string | null;
  necessidade_identificada?: number;
  quantidade_reposta_depois?: number;
  dias_sem_reposicao?: number;
  venda_apos_ruptura?: number;
};

export type ClassificacaoFiltroOption = {
  valor: string;
  qtd_produtos: number;
};

export type ClassificacaoFiltros = {
  status_produto: ClassificacaoFiltroOption[];
  continuidade: ClassificacaoFiltroOption[];
  linha: ClassificacaoFiltroOption[];
  familia: ClassificacaoFiltroOption[];
};

export type ReposicaoFiltros = {
  cd_loja?: string;
  referencia?: string;
  somente_entrada_sem_necessidade?: string;
  status_produto?: string;
  continuidade?: string;
  linha?: string;
  familia?: string;
};

export type ProcessoReposicaoResumo = {
  skus_sugeridos: number;
  lojas: number;
  pecas_sugeridas: number;
  necessidade: number;
  entrada_total: number;
  criticos: number;
  altos: number;
  normais: number;
};

export type ProcessoReposicaoRow = {
  mes: string;
  cd_loja: number;
  nome_loja: string;
  referencia: string;
  descricao_produto: string;
  cd_produto: number;
  status_produto?: string | null;
  continuidade?: string | null;
  linha?: string | null;
  familia?: string | null;
  cor: string;
  tamanho: string;
  curva_completa: string;
  media_mensal: number;
  media_6m_sem_abr_mai?: number;
  media_12m_consideravel?: number;
  media_12m_sem_ruptura?: number;
  estoque_minimo: number;
  estoque_minimo_6m?: number;
  estoque_minimo_12m?: number;
  estoque_minimo_sem_ruptura?: number;
  saldo_inicial: number;
  necessidade: number;
  necessidade_6m?: number;
  necessidade_12m?: number;
  necessidade_sem_ruptura?: number;
  entrada_total: number;
  qtd_sugerida_bruta?: number;
  qtd_pendente_pedido?: number;
  qtd_transito?: number;
  qtd_ja_programada?: number;
  qtd_sugerida_6m?: number;
  qtd_sugerida_12m?: number;
  qtd_sugerida_sem_ruptura?: number;
  qtd_sugerida: number;
  original_price?: number;
  price?: number;
  discount_percentage?: number;
  discount_value?: number;
  customer_code?: number | null;
  operation_code?: number | null;
  payment_condition_code?: number | null;
  shipping_company_code?: number | null;
  freight_type?: string | null;
  status_reposicao: string;
  prioridade: string;
};

export type Media12mImpactoResumo = {
  skus_analisados: number;
  lojas: number;
  referencias: number;
  skus_com_gap: number;
  ruptura_silenciosa: number;
  subestimados: number;
  gap_pecas: number;
  media_antiga_total: number;
  media_12m_total: number;
  media_sem_ruptura_total: number;
  estoque_minimo_3m_total: number;
  estoque_minimo_12m_total: number;
  gap_estoque_minimo_total: number;
  estoque_cd_skus_gap: number;
  qtd_recuperavel: number;
  deficit_pos_estoque: number;
};

export type Media12mImpactoLoja = {
  cd_loja: number;
  nome_loja: string;
  skus_com_gap: number;
  ruptura_silenciosa: number;
  gap_pecas: number;
  qtd_recuperavel: number;
  media_antiga_total: number;
  media_12m_total: number;
  media_sem_ruptura_total: number;
};

export type Media12mImpactoReferencia = {
  referencia: string;
  descricao_produto: string;
  lojas: number;
  skus_com_gap: number;
  ruptura_silenciosa: number;
  gap_pecas: number;
  qtd_recuperavel: number;
  media_antiga_total: number;
  media_12m_total: number;
  media_sem_ruptura_total: number;
};

export type Media12mImpactoCurva = {
  curva_completa: string;
  skus_3m: number;
  skus_12m: number;
  skus_com_gap: number;
  ruptura_silenciosa: number;
  gap_pecas: number;
  qtd_recuperavel: number;
  media_antiga_total: number;
  media_12m_total: number;
  necessidade_3m_total: number;
  necessidade_12m_total: number;
  gap_necessidade_total: number;
  estoque_minimo_3m_total: number;
  estoque_minimo_12m_total: number;
  gap_estoque_minimo_total: number;
};

export type Media12mImpactoCurvaLoja = Media12mImpactoCurva & {
  cd_loja: number;
  nome_loja: string;
};

export type Media12mImpactoRow = {
  mes: string;
  cd_loja: number;
  nome_loja: string;
  referencia: string;
  descricao_produto: string;
  cd_produto: number;
  status_produto?: string | null;
  continuidade?: string | null;
  linha?: string | null;
  familia?: string | null;
  cor: string;
  tamanho: string;
  curva_completa: string;
  vendas_3m: number;
  media_antiga_3m: number;
  media_nova_12m: number;
  media_bruta_12m: number;
  media_sem_ruptura_12m: number;
  venda_12m_considerada: number;
  entrada_12m_considerada: number;
  venda_12m_sem_ruptura: number;
  entrada_12m_sem_ruptura: number;
  meses_considerados: number;
  meses_considerados_sem_ruptura: number;
  meses_utilizados_media_3m?: string | null;
  valores_utilizados_media_3m?: string | null;
  formula_media_antiga_3m?: string | null;
  meses_utilizados_media?: string | null;
  valores_utilizados_media?: string | null;
  formula_media_nova?: string | null;
  meses_utilizados_media_sem_ruptura?: string | null;
  valores_utilizados_media_sem_ruptura?: string | null;
  formula_media_sem_ruptura?: string | null;
  meses_excluidos_media_sem_ruptura?: string | null;
  explicacao_media_12m?: string | null;
  explicacao_media_sem_ruptura?: string | null;
  estoque_minimo_antigo: number;
  saldo_inicial: number;
  necessidade_antiga: number;
  entrada_total: number;
  estoque_disponivel_cd: number;
  multiplicador_curva: number;
  estoque_minimo_12m: number;
  gap_media: number;
  necessidade_12m: number;
  gap_necessidade: number;
  diagnostico: string;
  qtd_recuperavel_sku: number;
  deficit_pos_estoque_sku: number;
  qtd_recuperavel_rateada: number;
  cobertura_potencial_meses: number;
};

export type Media12mImpacto = {
  resumo: Media12mImpactoResumo;
  por_loja: Media12mImpactoLoja[];
  por_referencia: Media12mImpactoReferencia[];
  por_curva: Media12mImpactoCurva[];
  por_curva_loja: Media12mImpactoCurvaLoja[];
  rows: Media12mImpactoRow[];
};

export type TotvsConfigStatus = {
  configured: boolean;
  missing: string[];
  order_url_configured: boolean;
  token_url_configured: boolean;
};

export type TotvsPedidoPreview = {
  ready_to_send: boolean;
  missing_config: string[];
  pedido_tipo: "CURVA_A_AA" | "CURVA_BC_1" | "CURVA_BC_2" | string;
  month: string;
  skus: number;
  pecas: number;
  pedidos?: number;
  orders?: Array<{
    cd_loja: number;
    nome_loja: string;
    order_id: string;
    skus: number;
    pecas: number;
    total_amount: number;
    missing_config: string[];
    payload: Record<string, unknown>;
  }>;
  payload: Record<string, unknown>;
};

// ============================================================
// Types para Acompanhamento de Reposição
// ============================================================

export type ReposicaoStatus =
  | "GERADO"
  | "ENVIADO_TOTVS"
  | "ERRO_TOTVS"
  | "FATURADO"
  | "EXPEDIDO"
  | "EM_TRANSITO"
  | "RECEBIDO"
  | "CONFERIDO"
  | "FINALIZADO"
  | "CANCELADO";

export type ReposicaoPedido = {
  id: number;
  order_id: string;
  pedido_tipo: string;
  mes: string;
  cd_loja: number;
  nome_loja: string;
  total_skus: number;
  total_pecas: number;
  total_valor: number;
  status: ReposicaoStatus;
  totvs_order_number?: string | null;
  criado_em: string;
  atualizado_em: string;
};

export type ReposicaoItem = {
  id: number;
  cd_produto: number;
  referencia: string;
  descricao: string;
  cor: string;
  tamanho: string;
  curva_completa: string;
  quantidade: number;
  preco: number;
  status: ReposicaoStatus;
  observacao?: string | null;
  media_mensal?: number;
  estoque_minimo?: number;
  saldo_inicial?: number;
  necessidade?: number;
  entrada_total?: number;
  qtd_ja_programada?: number;
  atualizado_em: string;
};

export type ReposicaoHistorico = {
  id: number;
  item_id?: number | null;
  status_anterior?: string | null;
  status_novo: string;
  usuario?: string | null;
  observacao?: string | null;
  criado_em: string;
};

export type ReposicaoPedidoDetalhes = {
  pedido: ReposicaoPedido & { totvs_response?: Record<string, unknown> | null };
  itens: ReposicaoItem[];
  historico: ReposicaoHistorico[];
};

export type ReposicaoDashboard = {
  total_pedidos: number;
  total_skus: number;
  total_pecas: number;
  total_valor: number;
  por_status: Record<string, { total: number; pecas: number }>;
  status_disponiveis: ReposicaoStatus[];
};

export type ReposicaoPedidoFiltros = {
  mes?: string;
  cd_loja?: number;
  status?: ReposicaoStatus;
  pedido_tipo?: string;
};
