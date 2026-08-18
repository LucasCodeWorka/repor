"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import type { MatrizReposicaoRow, ResumoGeral } from "../../types/reposicao";
import { formatNumber, formatPercent } from "../cards/MetricCard";
import { StatusBadge } from "../cards/StatusBadge";

type Totais = {
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
};

type RefGroup = {
  referencia: string;
  descricao_produto: string;
  itens: MatrizReposicaoRow[];
  totais: Totais;
};

type EmpresaGroup = {
  cd_loja: number;
  nome_loja: string;
  referencias: RefGroup[];
  totais: Totais;
};

const emptyTotals: Totais = {
  necessidade: 0,
  entrada_periodo: 0,
  entrada_atrasada: 0,
  entrada_sem_lote: 0,
  entrada_total: 0,
  entrada_sem_necessidade: 0,
  faltou: 0,
  skus_demanda: 0,
  skus_atendidos: 0,
  skus_faltantes: 0,
};

function addTotals(rows: MatrizReposicaoRow[]): Totais {
  return rows.reduce(
    (acc, row) => ({
      necessidade: acc.necessidade + Number(row.necessidade || 0),
      entrada_periodo: acc.entrada_periodo + Number(row.entrada_periodo || 0),
      entrada_atrasada: acc.entrada_atrasada + Number(row.entrada_atrasada || 0),
      entrada_sem_lote: acc.entrada_sem_lote + Number(row.entrada_sem_lote || 0),
      entrada_total: acc.entrada_total + Number(row.entrada_total || 0),
      entrada_sem_necessidade: acc.entrada_sem_necessidade + Number(row.entrada_sem_necessidade || 0),
      faltou: acc.faltou + Number(row.faltou || 0),
      skus_demanda: acc.skus_demanda + Number(row.skus_demanda || 0),
      skus_atendidos: acc.skus_atendidos + Number(row.skus_atendidos || 0),
      skus_faltantes: acc.skus_faltantes + Number(row.skus_faltantes || 0),
    }),
    emptyTotals,
  );
}

function taxa(totais: Totais) {
  if (!totais.skus_demanda) return 100;
  return (totais.skus_atendidos / totais.skus_demanda) * 100;
}

function statusFromTotals(totais: Totais) {
  const value = taxa(totais);
  if (value >= 100) return "OK";
  if (value >= 50) return "PARCIAL";
  return "CRITICO";
}

function RowMetric({ totals }: { totals: Totais }) {
  return (
    <>
      <td>{formatNumber(totals.necessidade)}</td>
      <td>{formatNumber(totals.entrada_periodo)}</td>
      <td>{formatNumber(totals.entrada_atrasada)}</td>
      <td>{formatNumber(totals.entrada_sem_lote)}</td>
      <td>{formatNumber(totals.entrada_sem_necessidade)}</td>
      <td>{formatNumber(totals.skus_demanda)}</td>
      <td>{formatNumber(totals.skus_atendidos)}</td>
      <td className="bad">{formatNumber(totals.skus_faltantes)}</td>
      <td className="bad">{formatNumber(totals.faltou)}</td>
      <td>{formatPercent(taxa(totals))}</td>
      <td>
        <StatusBadge value={statusFromTotals(totals)} />
      </td>
    </>
  );
}

export function MatrizReposicao({ data, resumo }: { data: MatrizReposicaoRow[]; resumo?: ResumoGeral | null }) {
  const [expandedEmpresas, setExpandedEmpresas] = useState<Set<number>>(new Set());
  const [expandedRefs, setExpandedRefs] = useState<Set<string>>(new Set());

  const grupos = useMemo<EmpresaGroup[]>(() => {
    const empresaMap = new Map<number, MatrizReposicaoRow[]>();
    for (const row of data) {
      const key = Number(row.cd_loja);
      empresaMap.set(key, [...(empresaMap.get(key) ?? []), row]);
    }

    return Array.from(empresaMap.entries())
      .map(([cd_loja, rows]) => {
        const refMap = new Map<string, MatrizReposicaoRow[]>();
        for (const row of rows) {
          const ref = String(row.referencia || "SEM REFERENCIA");
          refMap.set(ref, [...(refMap.get(ref) ?? []), row]);
        }

        const referencias = Array.from(refMap.entries())
          .map(([referencia, refRows]) => ({
            referencia,
            descricao_produto: refRows[0]?.descricao_produto ?? "",
            itens: [...refRows].sort((a, b) =>
              `${a.cor}-${a.tamanho}-${a.cd_produto}`.localeCompare(`${b.cor}-${b.tamanho}-${b.cd_produto}`),
            ),
            totais: addTotals(refRows),
          }))
          .sort((a, b) => b.totais.skus_faltantes - a.totais.skus_faltantes || a.referencia.localeCompare(b.referencia));

        return {
          cd_loja,
          nome_loja: rows[0]?.nome_loja ?? `Loja ${cd_loja}`,
          referencias,
          totais: addTotals(rows),
        };
      })
      .sort((a, b) => taxa(a.totais) - taxa(b.totais) || b.totais.skus_faltantes - a.totais.skus_faltantes);
  }, [data]);

  const totalGeral = useMemo<Totais>(() => {
    if (resumo) {
      return {
        necessidade: Number(resumo.necessidade || 0),
        entrada_periodo: Number(resumo.entrada_periodo || 0),
        entrada_atrasada: Number(resumo.entrada_atrasada || 0),
        entrada_sem_lote: Number(resumo.entrada_sem_lote || 0),
        entrada_total: Number(resumo.entrada_total || 0),
        entrada_sem_necessidade: Number(resumo.entrada_sem_necessidade || 0),
        faltou: Number(resumo.faltou || 0),
        skus_demanda: Number(resumo.skus_demanda || 0),
        skus_atendidos: Number(resumo.skus_atendidos || 0),
        skus_faltantes: Number(resumo.skus_faltantes || 0),
      };
    }
    return addTotals(data);
  }, [data, resumo]);

  function toggleEmpresa(cdLoja: number) {
    setExpandedEmpresas((current) => {
      const next = new Set(current);
      if (next.has(cdLoja)) next.delete(cdLoja);
      else next.add(cdLoja);
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
    return <div className="emptyState">Nenhum SKU encontrado para a matriz.</div>;
  }

  return (
    <div className="matrixWrap">
      <table className="matrixTable">
        <thead>
          <tr>
            <th>Empresa / Referencia / SKU</th>
            <th>Necessidade</th>
            <th>Periodo</th>
            <th>Atrasada</th>
            <th>Sem lote</th>
            <th>Ent. sem nec.</th>
            <th>SKUs demanda</th>
            <th>Atendidos</th>
            <th>Faltantes</th>
            <th>Pecas faltantes</th>
            <th>Atend SKU</th>
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
            const empresaOpen = expandedEmpresas.has(empresa.cd_loja);
            return (
              <Fragment key={`empresa-group-${empresa.cd_loja}`}>
                <tr className="matrixGroup empresa">
                  <td>
                    <button type="button" onClick={() => toggleEmpresa(empresa.cd_loja)}>
                      {empresaOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      <strong>{empresa.nome_loja}</strong>
                    </button>
                  </td>
                  <RowMetric totals={empresa.totais} />
                </tr>
                {empresaOpen
                  ? empresa.referencias.map((ref) => {
                      const refKey = `${empresa.cd_loja}-${ref.referencia}`;
                      const refOpen = expandedRefs.has(refKey);
                      return (
                        <Fragment key={`ref-group-${refKey}`}>
                          <tr className="matrixGroup referencia">
                            <td>
                              <button type="button" onClick={() => toggleRef(refKey)}>
                                {refOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                <span>
                                  <strong>{ref.referencia}</strong>
                                  <em>{ref.descricao_produto}</em>
                                </span>
                              </button>
                            </td>
                            <RowMetric totals={ref.totais} />
                          </tr>
                          {refOpen
                            ? ref.itens.map((item) => (
                                <tr className="matrixSku" key={`${item.cd_loja}-${item.cd_produto}`}>
                                  <td>
                                    <span className="skuLabel">
                                      <strong>{item.cor || "SEM COR"} / {item.tamanho || "SEM TAM."}</strong>
                                      <em>SKU {item.cd_produto} - {item.curva_completa}</em>
                                    </span>
                                  </td>
                                  <td>{formatNumber(item.necessidade)}</td>
                                  <td>{formatNumber(item.entrada_periodo)}</td>
                                  <td>{formatNumber(item.entrada_atrasada)}</td>
                                  <td>{formatNumber(item.entrada_sem_lote)}</td>
                                  <td>{formatNumber(item.entrada_sem_necessidade)}</td>
                                  <td>{formatNumber(item.skus_demanda)}</td>
                                  <td>{formatNumber(item.skus_atendidos)}</td>
                                  <td className="bad">{formatNumber(item.skus_faltantes)}</td>
                                  <td className="bad">{formatNumber(item.faltou)}</td>
                                  <td>{item.skus_demanda ? formatPercent((item.skus_atendidos / item.skus_demanda) * 100) : formatPercent(100)}</td>
                                  <td>
                                    <StatusBadge value={item.status_reposicao} />
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
