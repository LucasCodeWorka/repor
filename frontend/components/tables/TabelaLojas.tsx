import Link from "next/link";
import type { LojaRankingRow } from "../../types/reposicao";
import { formatNumber, formatPercent } from "../cards/MetricCard";
import { StatusBadge } from "../cards/StatusBadge";

function statusForTaxa(taxa: number | null) {
  if ((taxa ?? 0) >= 100) return "OK";
  if ((taxa ?? 0) >= 50) return "PARCIAL";
  return "CRITICO";
}

export function TabelaLojas({ data }: { data: LojaRankingRow[] }) {
  if (!data.length) {
    return <div className="emptyState">Nenhuma loja encontrada para o filtro.</div>;
  }

  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>
            <th>Loja</th>
            <th>SKUs demanda</th>
            <th>SKUs atendidos</th>
            <th>SKUs faltantes</th>
            <th>Peças faltantes</th>
            <th>Atend SKU</th>
            <th>Periodo</th>
            <th>Atrasada</th>
            <th>Sem lote</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {data.map((loja) => (
            <tr key={loja.cd_loja}>
              <td>
                <Link className="tableLink" href={`/lojas/${loja.cd_loja}`}>
                  {loja.nome_loja}
                </Link>
              </td>
              <td>{formatNumber(loja.skus_demanda)}</td>
              <td>{formatNumber(loja.skus_atendidos)}</td>
              <td className="bad">{formatNumber(loja.skus_faltantes)}</td>
              <td className="bad">{formatNumber(loja.faltou)}</td>
              <td>{formatPercent(loja.taxa_atendimento)}</td>
              <td>{formatNumber(loja.skus_entrada_periodo)}</td>
              <td>{formatNumber(loja.skus_entrada_atrasada)}</td>
              <td>{formatNumber(loja.skus_entrada_sem_lote)}</td>
              <td>
                <StatusBadge value={statusForTaxa(loja.taxa_atendimento)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
