"use client";

import { Fragment, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { SkuSemReposicaoResumo, SkuSemReposicaoRow } from "../../types/reposicao";
import { formatNumber } from "../cards/MetricCard";
import { StatusBadge } from "../cards/StatusBadge";

type TotaisSkuSemReposicao = {
  qtd_skus: number;
  perdidos: number;
  risco: number;
  recuperando: number;
  necessidade_identificada: number;
  quantidade_reposta_depois: number;
  venda_apos_ruptura: number;
  dias_sem_reposicao: number;
  data_ultima_entrada: string | null;
  data_inicio_falta: string | null;
};

type RefGroup = {
  referencia: string;
  itens: SkuSemReposicaoRow[];
  totais: TotaisSkuSemReposicao;
};

type EmpresaGroup = {
  empresa: string;
  referencias: RefGroup[];
  totais: TotaisSkuSemReposicao;
};

const emptyTotals: TotaisSkuSemReposicao = {
  qtd_skus: 0,
  perdidos: 0,
  risco: 0,
  recuperando: 0,
  necessidade_identificada: 0,
  quantidade_reposta_depois: 0,
  venda_apos_ruptura: 0,
  dias_sem_reposicao: 0,
  data_ultima_entrada: null,
  data_inicio_falta: null,
};

function latestDate(current: string | null, next: string | null) {
  if (!next) return current;
  if (!current) return next;
  return next > current ? next : current;
}

function earliestDate(current: string | null, next: string | null) {
  if (!next) return current;
  if (!current) return next;
  return next < current ? next : current;
}

function addTotals(rows: SkuSemReposicaoRow[]): TotaisSkuSemReposicao {
  return rows.reduce(
    (acc, row) => ({
      qtd_skus: acc.qtd_skus + 1,
      perdidos: acc.perdidos + (row.status === "PERDIDO" ? 1 : 0),
      risco: acc.risco + (row.status === "EM RISCO" ? 1 : 0),
      recuperando: acc.recuperando + (row.status === "RECUPERANDO" ? 1 : 0),
      necessidade_identificada: acc.necessidade_identificada + Number(row.necessidade_identificada || 0),
      quantidade_reposta_depois: acc.quantidade_reposta_depois + Number(row.quantidade_reposta_depois || 0),
      venda_apos_ruptura: acc.venda_apos_ruptura + Number(row.venda_apos_ruptura || 0),
      dias_sem_reposicao: Math.max(acc.dias_sem_reposicao, Number(row.dias_sem_reposicao || 0)),
      data_ultima_entrada: latestDate(acc.data_ultima_entrada, row.data_ultima_entrada),
      data_inicio_falta: earliestDate(acc.data_inicio_falta, row.data_inicio_falta),
    }),
    emptyTotals,
  );
}

function statusFromTotals(totais: TotaisSkuSemReposicao) {
  if (totais.perdidos > 0) return "PERDIDO";
  if (totais.risco > 0) return "EM RISCO";
  return "RECUPERANDO";
}

function RowMetric({ totals }: { totals: TotaisSkuSemReposicao }) {
  return (
    <>
      <td>{formatNumber(totals.qtd_skus)}</td>
      <td className="bad">{formatNumber(totals.perdidos)}</td>
      <td>{formatNumber(totals.risco)}</td>
      <td>{formatNumber(totals.recuperando)}</td>
      <td>{totals.data_ultima_entrada ?? "-"}</td>
      <td>{totals.data_inicio_falta ?? "-"}</td>
      <td>{formatNumber(totals.necessidade_identificada)}</td>
      <td>{formatNumber(totals.quantidade_reposta_depois)}</td>
      <td className="bad">{formatNumber(totals.dias_sem_reposicao)}</td>
      <td>{formatNumber(totals.venda_apos_ruptura)}</td>
      <td>
        <StatusBadge value={statusFromTotals(totals)} />
      </td>
    </>
  );
}

function totalsFromResumo(resumo: SkuSemReposicaoResumo): TotaisSkuSemReposicao {
  return {
    qtd_skus: Number(resumo.total || 0),
    perdidos: Number(resumo.perdidos || 0),
    risco: Number(resumo.risco || 0),
    recuperando: Number(resumo.recuperando || 0),
    necessidade_identificada: Number(resumo.necessidade_identificada || 0),
    quantidade_reposta_depois: Number(resumo.quantidade_reposta_depois || 0),
    venda_apos_ruptura: Number(resumo.venda_apos_ruptura || 0),
    dias_sem_reposicao: Number(resumo.dias_sem_reposicao || 0),
    data_ultima_entrada: resumo.data_ultima_entrada ?? null,
    data_inicio_falta: resumo.data_inicio_falta ?? null,
  };
}

export function MatrizSkusSemReposicao({
  data,
  resumo,
}: {
  data: SkuSemReposicaoRow[];
  resumo?: SkuSemReposicaoResumo;
}) {
  const [expandedEmpresas, setExpandedEmpresas] = useState<Set<string>>(new Set());
  const [expandedRefs, setExpandedRefs] = useState<Set<string>>(new Set());

  const grupos = useMemo<EmpresaGroup[]>(() => {
    const empresaMap = new Map<string, SkuSemReposicaoRow[]>();
    for (const row of data) {
      const key = String(row.empresa || "SEM EMPRESA");
      empresaMap.set(key, [...(empresaMap.get(key) ?? []), row]);
    }

    return Array.from(empresaMap.entries())
      .map(([empresa, rows]) => {
        const refMap = new Map<string, SkuSemReposicaoRow[]>();
        for (const row of rows) {
          const ref = String(row.referencia || "SEM REFERENCIA");
          refMap.set(ref, [...(refMap.get(ref) ?? []), row]);
        }

        const referencias = Array.from(refMap.entries())
          .map(([referencia, refRows]) => ({
            referencia,
            itens: [...refRows].sort((a, b) =>
              `${a.cor}-${a.tamanho}-${a.sku}`.localeCompare(`${b.cor}-${b.tamanho}-${b.sku}`),
            ),
            totais: addTotals(refRows),
          }))
          .sort((a, b) => b.totais.perdidos - a.totais.perdidos || b.totais.risco - a.totais.risco || a.referencia.localeCompare(b.referencia));

        return {
          empresa,
          referencias,
          totais: addTotals(rows),
        };
      })
      .sort((a, b) => b.totais.perdidos - a.totais.perdidos || b.totais.risco - a.totais.risco || a.empresa.localeCompare(b.empresa));
  }, [data]);

  const totalGeral = useMemo(() => (resumo ? totalsFromResumo(resumo) : addTotals(data)), [data, resumo]);

  function toggleEmpresa(empresa: string) {
    setExpandedEmpresas((current) => {
      const next = new Set(current);
      if (next.has(empresa)) next.delete(empresa);
      else next.add(empresa);
      return next;
    });
  }

  function toggleRef(key: string) {
    setExpandedRefs((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  if (!data.length) {
    return <div className="emptyState">Nenhum SKU sem reposição encontrado no recorte atual.</div>;
  }

  return (
    <div className="matrixWrap">
      <table className="matrixTable skuLostMatrix">
        <thead>
          <tr>
            <th>Empresa / Referência / SKU</th>
            <th>SKUs</th>
            <th>Perdidos</th>
            <th>Em risco</th>
            <th>Recuperando</th>
            <th>Última entrada</th>
            <th>Início falta</th>
            <th>Necessidade</th>
            <th>Reposto depois</th>
            <th>Dias sem reposição</th>
            <th>Venda após ruptura</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr className="matrixGroup totalGeral">
            <td>
              <strong>Total geral</strong>
            </td>
            <RowMetric totals={totalGeral} />
          </tr>
          {grupos.map((empresa) => {
            const empresaOpen = expandedEmpresas.has(empresa.empresa);
            return (
              <Fragment key={`empresa-sem-reposicao-${empresa.empresa}`}>
                <tr className="matrixGroup empresa">
                  <td>
                    <button type="button" onClick={() => toggleEmpresa(empresa.empresa)}>
                      {empresaOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      <strong>{empresa.empresa}</strong>
                    </button>
                  </td>
                  <RowMetric totals={empresa.totais} />
                </tr>
                {empresaOpen
                  ? empresa.referencias.map((ref) => {
                      const refKey = `${empresa.empresa}-${ref.referencia}`;
                      const refOpen = expandedRefs.has(refKey);
                      return (
                        <Fragment key={`referencia-sem-reposicao-${refKey}`}>
                          <tr className="matrixGroup referencia">
                            <td>
                              <button type="button" onClick={() => toggleRef(refKey)}>
                                {refOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                <strong>{ref.referencia}</strong>
                              </button>
                            </td>
                            <RowMetric totals={ref.totais} />
                          </tr>
                          {refOpen
                            ? ref.itens.map((item) => (
                                <tr className="matrixSku" key={`${item.empresa}-${item.sku}-${item.data_inicio_falta}`}>
                                  <td>
                                    <span className="skuLabel">
                                      <strong>{item.cor || "SEM COR"} / {item.tamanho || "SEM TAM."}</strong>
                                      <em>SKU {item.sku} · média antes {formatNumber(item.media_venda_antes_ruptura)}</em>
                                    </span>
                                  </td>
                                  <td>1</td>
                                  <td className="bad">{item.status === "PERDIDO" ? 1 : 0}</td>
                                  <td>{item.status === "EM RISCO" ? 1 : 0}</td>
                                  <td>{item.status === "RECUPERANDO" ? 1 : 0}</td>
                                  <td>{item.data_ultima_entrada ?? "-"}</td>
                                  <td>{item.data_inicio_falta}</td>
                                  <td>{formatNumber(item.necessidade_identificada)}</td>
                                  <td>{formatNumber(item.quantidade_reposta_depois)}</td>
                                  <td className="bad">{formatNumber(item.dias_sem_reposicao)}</td>
                                  <td>{formatNumber(item.venda_apos_ruptura)}</td>
                                  <td>
                                    <StatusBadge value={item.status} />
                                  </td>
                                </tr>
                              ))
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
  );
}
