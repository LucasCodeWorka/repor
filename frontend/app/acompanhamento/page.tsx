"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Package,
  RefreshCw,
  Send,
  Truck,
  X,
} from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { MetricCard, formatNumber } from "../../components/cards/MetricCard";
import { PageContainer } from "../../components/layout/PageContainer";
import { api } from "../../services/api";
import type {
  ReposicaoDashboard,
  ReposicaoHistorico,
  ReposicaoItem,
  ReposicaoPedido,
  ReposicaoPedidoDetalhes,
  ReposicaoStatus,
} from "../../types/reposicao";

const STATUS_CONFIG: Record<ReposicaoStatus, { label: string; color: string; icon: typeof Clock }> = {
  GERADO: { label: "Gerado", color: "#94a3b8", icon: Clock },
  ENVIADO_TOTVS: { label: "Enviado TOTVS", color: "#3b82f6", icon: Send },
  ERRO_TOTVS: { label: "Erro TOTVS", color: "#ef4444", icon: AlertTriangle },
  FATURADO: { label: "Faturado", color: "#f97316", icon: Package },
  EXPEDIDO: { label: "Expedido", color: "#eab308", icon: Package },
  EM_TRANSITO: { label: "Em Trânsito", color: "#8b5cf6", icon: Truck },
  RECEBIDO: { label: "Recebido", color: "#22c55e", icon: CheckCircle2 },
  CONFERIDO: { label: "Conferido", color: "#16a34a", icon: CheckCircle2 },
  FINALIZADO: { label: "Finalizado", color: "#15803d", icon: CheckCircle2 },
  CANCELADO: { label: "Cancelado", color: "#991b1b", icon: X },
};

const STATUS_ORDER: ReposicaoStatus[] = [
  "GERADO",
  "ENVIADO_TOTVS",
  "ERRO_TOTVS",
  "FATURADO",
  "EXPEDIDO",
  "EM_TRANSITO",
  "RECEBIDO",
  "CONFERIDO",
  "FINALIZADO",
  "CANCELADO",
];

function StatusBadgeReposicao({ status }: { status: ReposicaoStatus }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.GERADO;
  return (
    <span
      className="statusBadge"
      style={{ background: `${config.color}20`, color: config.color, borderColor: config.color }}
    >
      {config.label}
    </span>
  );
}

function StatusSelect({
  value,
  onChange,
  disabled,
}: {
  value: ReposicaoStatus;
  onChange: (status: ReposicaoStatus) => void;
  disabled?: boolean;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as ReposicaoStatus)}
      disabled={disabled}
      style={{ minWidth: 140 }}
    >
      {STATUS_ORDER.map((status) => (
        <option key={status} value={status}>
          {STATUS_CONFIG[status]?.label || status}
        </option>
      ))}
    </select>
  );
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function TimelineItem({ item }: { item: ReposicaoHistorico }) {
  return (
    <div className="timelineItem">
      <div className="timelineDot" />
      <div className="timelineContent">
        <div className="timelineHeader">
          <span className="timelineStatus">
            {item.status_anterior ? `${item.status_anterior} → ` : ""}
            <strong>{item.status_novo}</strong>
          </span>
          <span className="timelineDate">{formatDate(item.criado_em)}</span>
        </div>
        {item.usuario && <span className="timelineUser">por {item.usuario}</span>}
        {item.observacao && <p className="timelineObs">{item.observacao}</p>}
      </div>
    </div>
  );
}

function PedidoDetalhesModal({
  pedidoId,
  onClose,
  onStatusChange,
}: {
  pedidoId: number;
  onClose: () => void;
  onStatusChange: () => void;
}) {
  const [detalhes, setDetalhes] = useState<ReposicaoPedidoDetalhes | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<number | null>(null);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadDetalhes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pedidoId]);

  async function loadDetalhes() {
    setLoading(true);
    try {
      const data = await api.getReposicaoPedidoDetalhes(pedidoId);
      setDetalhes(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusPedido(status: ReposicaoStatus) {
    setUpdating(-1);
    try {
      await api.atualizarStatusPedido(pedidoId, status, { atualizar_itens: true });
      await loadDetalhes();
      onStatusChange();
    } finally {
      setUpdating(null);
    }
  }

  async function handleStatusItem(itemId: number, status: ReposicaoStatus) {
    setUpdating(itemId);
    try {
      await api.atualizarStatusItem(itemId, status);
      await loadDetalhes();
      onStatusChange();
    } finally {
      setUpdating(null);
    }
  }

  function toggleItem(itemId: number) {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  }

  if (loading) {
    return (
      <div className="modalBackdrop" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <div className="modalHeader">
            <h3>Carregando...</h3>
            <button type="button" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!detalhes) return null;

  const { pedido, itens, historico } = detalhes;

  return (
    <div className="modalBackdrop" onClick={onClose}>
      <div className="modal modalLarge" onClick={(e) => e.stopPropagation()}>
        <div className="modalHeader">
          <div>
            <h3>{pedido.order_id}</h3>
            <p>
              {pedido.nome_loja} | {pedido.pedido_tipo} | {pedido.mes}
            </p>
          </div>
          <button type="button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modalBody">
          <div className="detalhesGrid">
            <div className="detalhesSection">
              <h4>Status do Pedido</h4>
              <div className="statusControl">
                <StatusBadgeReposicao status={pedido.status as ReposicaoStatus} />
                <StatusSelect
                  value={pedido.status as ReposicaoStatus}
                  onChange={handleStatusPedido}
                  disabled={updating !== null}
                />
                {pedido.totvs_order_number && (
                  <span className="totvsNumber">TOTVS #{pedido.totvs_order_number}</span>
                )}
              </div>
              <div className="detalhesMeta">
                <span>
                  <strong>{formatNumber(pedido.total_skus)}</strong> SKUs
                </span>
                <span>
                  <strong>{formatNumber(pedido.total_pecas)}</strong> peças
                </span>
                <span>
                  <strong>R$ {formatNumber(pedido.total_valor)}</strong>
                </span>
              </div>
            </div>

            <div className="detalhesSection">
              <h4>Histórico</h4>
              <div className="timeline">
                {historico.slice(0, 10).map((h) => (
                  <TimelineItem key={h.id} item={h} />
                ))}
              </div>
            </div>
          </div>

          <div className="detalhesSection">
            <h4>Itens ({itens.length})</h4>
            <div className="matrixWrap" style={{ maxHeight: 400 }}>
              <table className="matrixTable">
                <thead>
                  <tr>
                    <th>Produto</th>
                    <th>Cor / Tam</th>
                    <th>Curva</th>
                    <th>Qtd</th>
                    <th>Status</th>
                    <th>Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {itens.map((item) => (
                    <Fragment key={item.id}>
                      <tr
                        className="matrixSku clickableRow"
                        onClick={() => toggleItem(item.id)}
                      >
                        <td>
                          <span className="skuLabel">
                            <strong>{item.referencia}</strong>
                            <em>{item.descricao}</em>
                          </span>
                        </td>
                        <td>
                          {item.cor} / {item.tamanho}
                        </td>
                        <td>{item.curva_completa}</td>
                        <td>{formatNumber(item.quantidade)}</td>
                        <td>
                          <StatusBadgeReposicao status={item.status} />
                        </td>
                        <td>
                          <StatusSelect
                            value={item.status}
                            onChange={(s) => handleStatusItem(item.id, s)}
                            disabled={updating !== null}
                          />
                        </td>
                      </tr>
                      {expandedItems.has(item.id) && (
                        <tr className="itemDetails">
                          <td colSpan={6}>
                            <div className="itemDetailsGrid">
                              <span>
                                <strong>SKU:</strong> {item.cd_produto}
                              </span>
                              <span>
                                <strong>Média:</strong> {formatNumber(item.media_mensal || 0)}
                              </span>
                              <span>
                                <strong>Est.Mín:</strong> {formatNumber(item.estoque_minimo || 0)}
                              </span>
                              <span>
                                <strong>Saldo:</strong> {formatNumber(item.saldo_inicial || 0)}
                              </span>
                              <span>
                                <strong>Necessidade:</strong> {formatNumber(item.necessidade || 0)}
                              </span>
                              <span>
                                <strong>Entrada:</strong> {formatNumber(item.entrada_total || 0)}
                              </span>
                              {item.observacao && (
                                <span className="observacao">
                                  <strong>Obs:</strong> {item.observacao}
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AcompanhamentoPage() {
  const [dashboard, setDashboard] = useState<ReposicaoDashboard | null>(null);
  const [pedidos, setPedidos] = useState<ReposicaoPedido[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPedido, setSelectedPedido] = useState<number | null>(null);
  const [filtroStatus, setFiltroStatus] = useState<ReposicaoStatus | "">("");
  const [filtroMes, setFiltroMes] = useState<string>("");

  async function loadData() {
    setLoading(true);
    try {
      const [dashData, pedidosData] = await Promise.all([
        api.getReposicaoDashboard({ mes: filtroMes || undefined }),
        api.getReposicaoPedidos({
          mes: filtroMes || undefined,
          status: filtroStatus || undefined,
          limit: 500,
        }),
      ]);
      setDashboard(dashData);
      setPedidos(pedidosData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroStatus, filtroMes]);

  const statusCounts = dashboard?.por_status || {};

  return (
    <PageContainer
      title="Acompanhamento de Reposições"
      description="Acompanhe o status de cada pedido e SKU desde a geração até a finalização na loja."
      actions={
        <button type="button" onClick={loadData} disabled={loading}>
          <RefreshCw size={16} className={loading ? "spin" : ""} />
          Atualizar
        </button>
      }
    >
      {/* Dashboard Cards */}
      <div className="metricGrid four">
        <MetricCard
          title="Total Pedidos"
          value={dashboard?.total_pedidos || 0}
          icon={<Package size={20} />}
          tone="gray"
        />
        <MetricCard
          title="Total SKUs"
          value={dashboard?.total_skus || 0}
          icon={<Package size={20} />}
          tone="blue"
        />
        <MetricCard
          title="Total Peças"
          value={dashboard?.total_pecas || 0}
          icon={<Package size={20} />}
          tone="pink"
        />
        <MetricCard
          title="Valor Total"
          value={`R$ ${formatNumber(dashboard?.total_valor || 0)}`}
          icon={<Package size={20} />}
          tone="green"
        />
      </div>

      {/* Status Summary */}
      <section className="card">
        <div className="cardHeader">
          <h3>Resumo por Status</h3>
        </div>
        <div className="statusGrid">
          {STATUS_ORDER.filter((s) => s !== "CANCELADO").map((status) => {
            const data = statusCounts[status] || { total: 0, pecas: 0 };
            const config = STATUS_CONFIG[status];
            const isActive = filtroStatus === status;
            return (
              <button
                key={status}
                type="button"
                className={`statusCard ${isActive ? "active" : ""}`}
                style={{
                  borderColor: isActive ? config.color : undefined,
                  background: isActive ? `${config.color}10` : undefined,
                }}
                onClick={() => setFiltroStatus(isActive ? "" : status)}
              >
                <span className="statusIcon" style={{ color: config.color }}>
                  <config.icon size={20} />
                </span>
                <span className="statusLabel">{config.label}</span>
                <span className="statusCount">{data.total}</span>
                <span className="statusPecas">{formatNumber(data.pecas)} pç</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Filtros */}
      <div className="filterGrid" style={{ gridTemplateColumns: "repeat(3, minmax(150px, 1fr)) auto" }}>
        <label>
          Mês
          <input
            type="month"
            value={filtroMes}
            onChange={(e) => setFiltroMes(e.target.value)}
            placeholder="Todos os meses"
          />
        </label>
        <label>
          Status
          <select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value as ReposicaoStatus | "")}>
            <option value="">Todos</option>
            {STATUS_ORDER.map((s) => (
              <option key={s} value={s}>
                {STATUS_CONFIG[s].label}
              </option>
            ))}
          </select>
        </label>
        <label>
          &nbsp;
          <button
            type="button"
            onClick={() => {
              setFiltroStatus("");
              setFiltroMes("");
            }}
          >
            Limpar filtros
          </button>
        </label>
      </div>

      {/* Tabela de Pedidos */}
      <section className="card">
        <div className="cardHeader">
          <h3>Pedidos ({pedidos.length})</h3>
        </div>
        <div className="matrixWrap">
          <table className="matrixTable">
            <thead>
              <tr>
                <th>Pedido</th>
                <th>Loja</th>
                <th>Tipo</th>
                <th>Mês</th>
                <th>SKUs</th>
                <th>Peças</th>
                <th>Valor</th>
                <th>Status</th>
                <th>TOTVS</th>
                <th>Criado</th>
              </tr>
            </thead>
            <tbody>
              {pedidos.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ textAlign: "center", padding: 40 }}>
                    {loading ? "Carregando..." : "Nenhum pedido encontrado"}
                  </td>
                </tr>
              ) : (
                pedidos.map((pedido) => (
                  <tr
                    key={pedido.id}
                    className="matrixSku clickableRow"
                    onClick={() => setSelectedPedido(pedido.id)}
                  >
                    <td>
                      <strong>{pedido.order_id}</strong>
                    </td>
                    <td>{pedido.nome_loja}</td>
                    <td>{pedido.pedido_tipo}</td>
                    <td>{pedido.mes}</td>
                    <td>{formatNumber(pedido.total_skus)}</td>
                    <td>{formatNumber(pedido.total_pecas)}</td>
                    <td>R$ {formatNumber(pedido.total_valor)}</td>
                    <td>
                      <StatusBadgeReposicao status={pedido.status} />
                    </td>
                    <td>{pedido.totvs_order_number || "-"}</td>
                    <td>{formatDate(pedido.criado_em)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Modal de Detalhes */}
      {selectedPedido && (
        <PedidoDetalhesModal
          pedidoId={selectedPedido}
          onClose={() => setSelectedPedido(null)}
          onStatusChange={loadData}
        />
      )}
    </PageContainer>
  );
}
