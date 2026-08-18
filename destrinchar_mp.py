"""
Destrincha o valor de uma MP na consulta de necessidade:

1) Consumo direto ja apontado nas OPs (vr_pcp_opmp)
2) Consumo indireto para produzir ALCAS usadas por PAs em producao

Uso:
    python destrinchar_mp.py
    python destrinchar_mp.py 1002422
"""
import argparse
from decimal import Decimal

from tabulate import tabulate

from db_bridge import get_connection


def fmt_num(valor):
    if valor is None:
        return "0"
    if isinstance(valor, Decimal):
        valor = float(valor)
    return f"{valor:,.4f}".rstrip("0").rstrip(".")


def as_decimal(valor):
    if valor is None:
        return Decimal("0")
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


def print_table(titulo, colunas, linhas):
    print("\n" + "=" * 100)
    print(titulo)
    print("=" * 100)

    if not linhas:
        print("Sem registros.")
        return

    print(tabulate(linhas, headers=colunas, tablefmt="psql"))
    print(f"\nTotal de linhas: {len(linhas)}")


def print_conta_aberta(linhas):
    print("\n" + "=" * 100)
    print("CONTA ABERTA - DE ONDE VEM CADA SUBTOTAL")
    print("=" * 100)

    if not linhas:
        print("Sem registros.")
        return

    alca_atual = None
    subtotal_alca = Decimal("0")
    total_geral = Decimal("0")

    for row in linhas:
        (
            cd_alca,
            descricao_alca,
            nr_op,
            cd_pa,
            descricao_pa,
            qt_op,
            consumo_alca_por_pa,
            qt_alca_necessaria,
            consumo_mp_por_alca,
            qt_mp_calculada,
        ) = row

        if alca_atual is not None and cd_alca != alca_atual:
            print(f"  Subtotal da alca {alca_atual}: {fmt_num(subtotal_alca)}\n")
            subtotal_alca = Decimal("0")

        if cd_alca != alca_atual:
            print(f"ALCA {cd_alca} - {descricao_alca}")
            alca_atual = cd_alca

        subtotal_alca += as_decimal(qt_mp_calculada)
        total_geral += as_decimal(qt_mp_calculada)

        descricao_pa = (descricao_pa[:45] + "...") if len(descricao_pa) > 48 else descricao_pa
        print(
            "  "
            f"OP {nr_op} | PA {cd_pa} | {descricao_pa} | "
            f"qt_op {fmt_num(qt_op)} x alca/PA {fmt_num(consumo_alca_por_pa)} "
            f"= {fmt_num(qt_alca_necessaria)} alcas | "
            f"x MP/alca {fmt_num(consumo_mp_por_alca)} "
            f"= {fmt_num(qt_mp_calculada)}"
        )

    print(f"  Subtotal da alca {alca_atual}: {fmt_num(subtotal_alca)}")
    print("-" * 100)
    print(f"TOTAL GERAL: {fmt_num(total_geral)}")


def print_explicacao_unica(resumo, linhas_alca, linhas_direto):
    print("\n" + "=" * 100)
    print("EXPLICACAO UNICA DO CALCULO")
    print("=" * 100)

    if not resumo:
        print("MP nao encontrada no resumo.")
        return

    cd_produto, descricao, qt_alcas, qt_ops, total = resumo[0]
    qt_alcas = as_decimal(qt_alcas)
    qt_ops = as_decimal(qt_ops)
    total = as_decimal(total)

    print(f"MP {cd_produto} - {descricao}")
    print()
    print("Formula da sua consulta:")
    print("  total = quantidade vinda das ALCAS + quantidade direta das OPs")
    print(f"  total = {fmt_num(qt_alcas)} + {fmt_num(qt_ops)} = {fmt_num(total)}")
    print()

    print("1) Parte vinda das ALCAS")
    if linhas_alca:
        alca_atual = None
        subtotal_alca = Decimal("0")

        for row in linhas_alca:
            (
                cd_alca,
                descricao_alca,
                nr_op,
                cd_pa,
                descricao_pa,
                qt_op,
                consumo_alca_por_pa,
                qt_alca_necessaria,
                consumo_mp_por_alca,
                qt_mp_calculada,
            ) = row

            if alca_atual is not None and cd_alca != alca_atual:
                print(f"     subtotal alca {alca_atual} = {fmt_num(subtotal_alca)}")
                print()
                subtotal_alca = Decimal("0")

            if cd_alca != alca_atual:
                print(f"   ALCA {cd_alca} - {descricao_alca}")
                alca_atual = cd_alca

            subtotal_alca += as_decimal(qt_mp_calculada)

            print(
                f"     OP {nr_op}, PA {cd_pa}: "
                f"{fmt_num(qt_op)} OP x {fmt_num(consumo_alca_por_pa)} alca/PA "
                f"= {fmt_num(qt_alca_necessaria)} alcas; "
                f"{fmt_num(qt_alca_necessaria)} x {fmt_num(consumo_mp_por_alca)} MP/alca "
                f"= {fmt_num(qt_mp_calculada)}"
            )

        print(f"     subtotal alca {alca_atual} = {fmt_num(subtotal_alca)}")
    else:
        print("   Sem valor vindo de ALCAS.")

    print()
    print("2) Parte direta das OPs")
    if linhas_direto:
        total_direto = Decimal("0")
        for row in linhas_direto:
            cd_empresa, nr_ciclo, nr_op, tp_situacao, cd_categoria, cd_mp, _, qt_estimada, *_ = row
            total_direto += as_decimal(qt_estimada)
            print(
                f"   Empresa {cd_empresa}, ciclo {nr_ciclo}, OP {nr_op}, "
                f"situacao {tp_situacao}, categoria {cd_categoria}: "
                f"qt_estimada {fmt_num(qt_estimada)}"
            )
        print(f"   subtotal direto nas OPs = {fmt_num(total_direto)}")
    else:
        print("   Sem registros diretos em vr_pcp_opmp para esta MP.")

    print()
    print("Conclusao:")
    print(f"  {fmt_num(qt_alcas)} das alcas + {fmt_num(qt_ops)} direto nas OPs = {fmt_num(total)}")


def fetch_all(cur, query, params):
    cur.execute(query, params)
    colunas = [desc[0] for desc in cur.description]
    linhas = cur.fetchall()
    return colunas, linhas


def destrinchar_mp(cd_mp):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Resumo final igual ao raciocinio da sua consulta principal.
            resumo_query = """
                WITH
                ops_producao AS (
                    SELECT
                        aa.cd_produto,
                        SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_op
                    FROM vr_pcp_opi aa
                    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa
                                       AND aa.nr_ciclo = bb.nr_ciclo
                                       AND aa.nr_op = bb.nr_op
                    WHERE aa.cd_empresa = 1
                      AND COALESCE(bb.cd_categoria, 0) <> 15
                      AND aa.tp_situacao IN (5, 10, 15, 20)
                    GROUP BY aa.cd_produto
                ),
                necessidade_alca AS (
                    SELECT
                        cc.cd_produtomp AS cd_alca,
                        SUM(op.qt_op * cc.qt_consumo) AS qt_alca_necessaria
                    FROM ops_producao op
                    JOIN vr_pcp_fcconsumo cc ON cc.cd_produtopa = op.cd_produto
                    JOIN prd_produtoclas pp ON pp.cd_produto = cc.cd_produtomp
                                            AND pp.cd_tipoclas = 111
                    JOIN prd_classificacao pc ON pc.cd_tipoclas = pp.cd_tipoclas
                                              AND pc.cd_classificacao = pp.cd_classificacao
                    WHERE pc.ds_classificacao = 'ALCA'
                      AND (op.qt_op * cc.qt_consumo) > 0
                    GROUP BY cc.cd_produtomp
                ),
                consumo_mp_alca AS (
                    SELECT
                        cc.cd_produtomp AS cd_mp,
                        SUM(na.qt_alca_necessaria * cc.qt_consumo) AS qt_mp
                    FROM necessidade_alca na
                    JOIN vr_pcp_fcconsumo cc ON cc.cd_produtopa = na.cd_alca
                    GROUP BY cc.cd_produtomp
                ),
                consumo_mp_op AS (
                    SELECT
                        aa.cd_produto AS cd_mp,
                        SUM(aa.qt_estimada) AS qt_mp
                    FROM vr_pcp_opmp aa
                    LEFT JOIN vr_pcp_opc bb ON aa.nr_op = bb.nr_op
                                            AND aa.nr_ciclo = bb.nr_ciclo
                                            AND aa.cd_empresa = bb.cd_empresa
                    WHERE aa.qt_baixada = 0
                      AND bb.tp_situacao NOT IN (30, 40)
                      AND aa.in_fechamentobaixa = 'F'
                    GROUP BY aa.cd_produto
                )
                SELECT
                    %s AS cd_produto,
                    COALESCE(p.ds_produto, '-') AS descricao,
                    COALESCE(a.qt_mp, 0) AS qt_vinda_de_alcas,
                    COALESCE(b.qt_mp, 0) AS qt_vinda_das_ops,
                    COALESCE(a.qt_mp, 0) + COALESCE(b.qt_mp, 0) AS total
                FROM (SELECT %s::numeric AS cd_mp) filtro
                LEFT JOIN consumo_mp_alca a ON a.cd_mp = filtro.cd_mp
                LEFT JOIN consumo_mp_op b ON b.cd_mp = filtro.cd_mp
                LEFT JOIN prd_produto p ON p.cd_produto = filtro.cd_mp
            """
            colunas, linhas_resumo = fetch_all(cur, resumo_query, (cd_mp, cd_mp))
            linhas_fmt = [
                (r[0], r[1], fmt_num(r[2]), fmt_num(r[3]), fmt_num(r[4]))
                for r in linhas_resumo
            ]
            print_table("RESUMO DA MP", colunas, linhas_fmt)

            # Detalha a parte que vem diretamente da tabela de MP das OPs.
            direto_query = """
                SELECT
                    aa.cd_empresa,
                    aa.nr_ciclo,
                    aa.nr_op,
                    bb.tp_situacao,
                    bb.cd_categoria,
                    aa.cd_produto AS cd_mp,
                    COALESCE(p.ds_produto, '-') AS descricao_mp,
                    aa.qt_estimada,
                    aa.qt_baixada,
                    aa.in_fechamentobaixa
                FROM vr_pcp_opmp aa
                LEFT JOIN vr_pcp_opc bb ON aa.nr_op = bb.nr_op
                                        AND aa.nr_ciclo = bb.nr_ciclo
                                        AND aa.cd_empresa = bb.cd_empresa
                LEFT JOIN prd_produto p ON p.cd_produto = aa.cd_produto
                WHERE aa.cd_produto = %s
                  AND aa.qt_baixada = 0
                  AND bb.tp_situacao NOT IN (30, 40)
                  AND aa.in_fechamentobaixa = 'F'
                ORDER BY aa.qt_estimada DESC, aa.nr_op
            """
            colunas, linhas_direto = fetch_all(cur, direto_query, (cd_mp,))
            linhas_fmt = [
                tuple(fmt_num(v) if isinstance(v, Decimal) else v for v in row)
                for row in linhas_direto
            ]
            print_table("FONTE 4 - MP DIRETO NAS OPS", colunas, linhas_fmt)

            # Detalha a parte calculada: PA em OP -> ALCA necessaria -> MP da ficha da ALCA.
            alca_query = """
                WITH
                ops_producao AS (
                    SELECT
                        aa.cd_empresa,
                        aa.nr_ciclo,
                        aa.nr_op,
                        aa.cd_produto AS cd_pa,
                        SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_op
                    FROM vr_pcp_opi aa
                    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa
                                       AND aa.nr_ciclo = bb.nr_ciclo
                                       AND aa.nr_op = bb.nr_op
                    WHERE aa.cd_empresa = 1
                      AND COALESCE(bb.cd_categoria, 0) <> 15
                      AND aa.tp_situacao IN (5, 10, 15, 20)
                    GROUP BY aa.cd_empresa, aa.nr_ciclo, aa.nr_op, aa.cd_produto
                ),
                alcas_por_pa AS (
                    SELECT
                        op.cd_empresa,
                        op.nr_ciclo,
                        op.nr_op,
                        op.cd_pa,
                        op.qt_op,
                        fc_alca.cd_produtomp AS cd_alca,
                        fc_alca.qt_consumo AS consumo_alca_por_pa,
                        op.qt_op * fc_alca.qt_consumo AS qt_alca_necessaria
                    FROM ops_producao op
                    JOIN vr_pcp_fcconsumo fc_alca ON fc_alca.cd_produtopa = op.cd_pa
                    JOIN prd_produtoclas pp ON pp.cd_produto = fc_alca.cd_produtomp
                                            AND pp.cd_tipoclas = 111
                    JOIN prd_classificacao pc ON pc.cd_tipoclas = pp.cd_tipoclas
                                              AND pc.cd_classificacao = pp.cd_classificacao
                    WHERE pc.ds_classificacao = 'ALCA'
                      AND (op.qt_op * fc_alca.qt_consumo) > 0
                )
                SELECT
                    a.cd_empresa,
                    a.nr_ciclo,
                    a.nr_op,
                    a.cd_pa,
                    COALESCE(pa.ds_produto, '-') AS descricao_pa,
                    a.qt_op,
                    a.cd_alca,
                    COALESCE(alca.ds_produto, '-') AS descricao_alca,
                    a.consumo_alca_por_pa,
                    a.qt_alca_necessaria,
                    fc_mp.cd_produtomp AS cd_mp,
                    COALESCE(mp.ds_produto, '-') AS descricao_mp,
                    fc_mp.qt_consumo AS consumo_mp_por_alca,
                    a.qt_alca_necessaria * fc_mp.qt_consumo AS qt_mp_calculada
                FROM alcas_por_pa a
                JOIN vr_pcp_fcconsumo fc_mp ON fc_mp.cd_produtopa = a.cd_alca
                LEFT JOIN prd_produto pa ON pa.cd_produto = a.cd_pa
                LEFT JOIN prd_produto alca ON alca.cd_produto = a.cd_alca
                LEFT JOIN prd_produto mp ON mp.cd_produto = fc_mp.cd_produtomp
                WHERE fc_mp.cd_produtomp = %s
                ORDER BY qt_mp_calculada DESC, a.cd_alca, a.cd_pa, a.nr_op
            """
            colunas, linhas = fetch_all(cur, alca_query, (cd_mp,))
            linhas_fmt = [
                tuple(fmt_num(v) if isinstance(v, Decimal) else v for v in row)
                for row in linhas
            ]
            print_table("FONTE 2/3 - PA -> ALCA -> MP", colunas, linhas_fmt)

            conta_aberta_query = """
                WITH
                ops_producao AS (
                    SELECT
                        aa.cd_empresa,
                        aa.nr_ciclo,
                        aa.nr_op,
                        aa.cd_produto AS cd_pa,
                        SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_op
                    FROM vr_pcp_opi aa
                    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa
                                       AND aa.nr_ciclo = bb.nr_ciclo
                                       AND aa.nr_op = bb.nr_op
                    WHERE aa.cd_empresa = 1
                      AND COALESCE(bb.cd_categoria, 0) <> 15
                      AND aa.tp_situacao IN (5, 10, 15, 20)
                    GROUP BY aa.cd_empresa, aa.nr_ciclo, aa.nr_op, aa.cd_produto
                ),
                alcas_por_pa AS (
                    SELECT
                        op.nr_op,
                        op.cd_pa,
                        op.qt_op,
                        fc_alca.cd_produtomp AS cd_alca,
                        fc_alca.qt_consumo AS consumo_alca_por_pa,
                        op.qt_op * fc_alca.qt_consumo AS qt_alca_necessaria
                    FROM ops_producao op
                    JOIN vr_pcp_fcconsumo fc_alca ON fc_alca.cd_produtopa = op.cd_pa
                    JOIN prd_produtoclas pp ON pp.cd_produto = fc_alca.cd_produtomp
                                            AND pp.cd_tipoclas = 111
                    JOIN prd_classificacao pc ON pc.cd_tipoclas = pp.cd_tipoclas
                                              AND pc.cd_classificacao = pp.cd_classificacao
                    WHERE pc.ds_classificacao = 'ALCA'
                      AND (op.qt_op * fc_alca.qt_consumo) > 0
                )
                SELECT
                    a.cd_alca,
                    COALESCE(alca.ds_produto, '-') AS descricao_alca,
                    a.nr_op,
                    a.cd_pa,
                    COALESCE(pa.ds_produto, '-') AS descricao_pa,
                    a.qt_op,
                    a.consumo_alca_por_pa,
                    a.qt_alca_necessaria,
                    fc_mp.qt_consumo AS consumo_mp_por_alca,
                    a.qt_alca_necessaria * fc_mp.qt_consumo AS qt_mp_calculada
                FROM alcas_por_pa a
                JOIN vr_pcp_fcconsumo fc_mp ON fc_mp.cd_produtopa = a.cd_alca
                LEFT JOIN prd_produto alca ON alca.cd_produto = a.cd_alca
                LEFT JOIN prd_produto pa ON pa.cd_produto = a.cd_pa
                WHERE fc_mp.cd_produtomp = %s
                ORDER BY a.cd_alca, qt_mp_calculada DESC, a.nr_op, a.cd_pa
            """
            _, linhas_conta = fetch_all(cur, conta_aberta_query, (cd_mp,))
            print_conta_aberta(linhas_conta)

            print_explicacao_unica(linhas_resumo, linhas_conta, linhas_direto)

            produtos_envolvidos_query = """
                WITH
                ops_producao AS (
                    SELECT
                        aa.cd_empresa,
                        aa.nr_ciclo,
                        aa.nr_op,
                        aa.cd_produto AS cd_pa,
                        SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_op
                    FROM vr_pcp_opi aa
                    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa
                                       AND aa.nr_ciclo = bb.nr_ciclo
                                       AND aa.nr_op = bb.nr_op
                    WHERE aa.cd_empresa = 1
                      AND COALESCE(bb.cd_categoria, 0) <> 15
                      AND aa.tp_situacao IN (5, 10, 15, 20)
                    GROUP BY aa.cd_empresa, aa.nr_ciclo, aa.nr_op, aa.cd_produto
                ),
                alcas_por_pa AS (
                    SELECT
                        op.cd_pa,
                        fc_alca.cd_produtomp AS cd_alca
                    FROM ops_producao op
                    JOIN vr_pcp_fcconsumo fc_alca ON fc_alca.cd_produtopa = op.cd_pa
                    JOIN prd_produtoclas pp ON pp.cd_produto = fc_alca.cd_produtomp
                                            AND pp.cd_tipoclas = 111
                    JOIN prd_classificacao pc ON pc.cd_tipoclas = pp.cd_tipoclas
                                              AND pc.cd_classificacao = pp.cd_classificacao
                    JOIN vr_pcp_fcconsumo fc_mp ON fc_mp.cd_produtopa = fc_alca.cd_produtomp
                    WHERE pc.ds_classificacao = 'ALCA'
                      AND fc_mp.cd_produtomp = %s
                      AND (op.qt_op * fc_alca.qt_consumo) > 0
                ),
                produtos AS (
                    SELECT 'MP ANALISADA' AS tipo, %s::numeric AS cd_produto
                    UNION
                    SELECT 'ALCA QUE CONSOME A MP' AS tipo, cd_alca AS cd_produto
                    FROM alcas_por_pa
                    UNION
                    SELECT 'PA EM PRODUCAO' AS tipo, cd_pa AS cd_produto
                    FROM alcas_por_pa
                ),
                classificacoes AS (
                    SELECT
                        pp.cd_produto,
                        STRING_AGG(pc.ds_classificacao, ', ' ORDER BY pc.ds_classificacao) AS classificacoes
                    FROM prd_produtoclas pp
                    JOIN prd_classificacao pc ON pc.cd_tipoclas = pp.cd_tipoclas
                                              AND pc.cd_classificacao = pp.cd_classificacao
                    GROUP BY pp.cd_produto
                )
                SELECT
                    p.tipo,
                    p.cd_produto,
                    COALESCE(pr.ds_produto, '-') AS descricao,
                    COALESCE(c.classificacoes, '-') AS classificacoes
                FROM produtos p
                LEFT JOIN prd_produto pr ON pr.cd_produto = p.cd_produto
                LEFT JOIN classificacoes c ON c.cd_produto = p.cd_produto
                ORDER BY
                    CASE p.tipo
                        WHEN 'MP ANALISADA' THEN 1
                        WHEN 'ALCA QUE CONSOME A MP' THEN 2
                        ELSE 3
                    END,
                    p.cd_produto
            """
            colunas, linhas = fetch_all(cur, produtos_envolvidos_query, (cd_mp, cd_mp))
            linhas_fmt = [
                tuple(fmt_num(v) if isinstance(v, Decimal) else v for v in row)
                for row in linhas
            ]
            print_table("PRODUTOS ENVOLVIDOS NO CALCULO", colunas, linhas_fmt)

            ficha_mp_query = """
                WITH
                classificacoes AS (
                    SELECT
                        pp.cd_produto,
                        STRING_AGG(pc.ds_classificacao, ', ' ORDER BY pc.ds_classificacao) AS classificacoes
                    FROM prd_produtoclas pp
                    JOIN prd_classificacao pc ON pc.cd_tipoclas = pp.cd_tipoclas
                                              AND pc.cd_classificacao = pp.cd_classificacao
                    GROUP BY pp.cd_produto
                )
                SELECT
                    fc.cd_produtopa AS produto_pai,
                    COALESCE(pa.ds_produto, '-') AS descricao_pai,
                    COALESCE(c.classificacoes, '-') AS classificacoes_pai,
                    fc.cd_produtomp AS mp,
                    COALESCE(mp.ds_produto, '-') AS descricao_mp,
                    fc.qt_consumo AS consumo_mp_por_pai
                FROM vr_pcp_fcconsumo fc
                LEFT JOIN prd_produto pa ON pa.cd_produto = fc.cd_produtopa
                LEFT JOIN prd_produto mp ON mp.cd_produto = fc.cd_produtomp
                LEFT JOIN classificacoes c ON c.cd_produto = fc.cd_produtopa
                WHERE fc.cd_produtomp = %s
                ORDER BY
                    CASE WHEN COALESCE(c.classificacoes, '') LIKE '%%ALCA%%' THEN 1 ELSE 2 END,
                    fc.cd_produtopa
            """
            colunas, linhas = fetch_all(cur, ficha_mp_query, (cd_mp,))
            linhas_fmt = [
                tuple(fmt_num(v) if isinstance(v, Decimal) else v for v in row)
                for row in linhas
            ]
            print_table("FICHA TECNICA - PRODUTOS QUE CONSOMEM ESTA MP", colunas, linhas_fmt)

            # Agrupamento por ALCA para bater com o total da fonte calculada.
            alca_resumo_query = """
                WITH
                ops_producao AS (
                    SELECT
                        aa.cd_produto AS cd_pa,
                        SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_op
                    FROM vr_pcp_opi aa
                    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa
                                       AND aa.nr_ciclo = bb.nr_ciclo
                                       AND aa.nr_op = bb.nr_op
                    WHERE aa.cd_empresa = 1
                      AND COALESCE(bb.cd_categoria, 0) <> 15
                      AND aa.tp_situacao IN (5, 10, 15, 20)
                    GROUP BY aa.cd_produto
                ),
                necessidade_alca AS (
                    SELECT
                        cc.cd_produtomp AS cd_alca,
                        SUM(op.qt_op * cc.qt_consumo) AS qt_alca_necessaria
                    FROM ops_producao op
                    JOIN vr_pcp_fcconsumo cc ON cc.cd_produtopa = op.cd_pa
                    JOIN prd_produtoclas pp ON pp.cd_produto = cc.cd_produtomp
                                            AND pp.cd_tipoclas = 111
                    JOIN prd_classificacao pc ON pc.cd_tipoclas = pp.cd_tipoclas
                                              AND pc.cd_classificacao = pp.cd_classificacao
                    WHERE pc.ds_classificacao = 'ALCA'
                      AND (op.qt_op * cc.qt_consumo) > 0
                    GROUP BY cc.cd_produtomp
                )
                SELECT
                    na.cd_alca,
                    COALESCE(alca.ds_produto, '-') AS descricao_alca,
                    na.qt_alca_necessaria,
                    fc.qt_consumo AS consumo_mp_por_alca,
                    na.qt_alca_necessaria * fc.qt_consumo AS qt_mp_calculada
                FROM necessidade_alca na
                JOIN vr_pcp_fcconsumo fc ON fc.cd_produtopa = na.cd_alca
                LEFT JOIN prd_produto alca ON alca.cd_produto = na.cd_alca
                WHERE fc.cd_produtomp = %s
                ORDER BY qt_mp_calculada DESC, na.cd_alca
            """
            colunas, linhas = fetch_all(cur, alca_resumo_query, (cd_mp,))
            linhas_fmt = [
                tuple(fmt_num(v) if isinstance(v, Decimal) else v for v in row)
                for row in linhas
            ]
            print_table("RESUMO AGRUPADO POR ALCA", colunas, linhas_fmt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Destrincha o valor calculado de uma materia-prima."
    )
    parser.add_argument(
        "cd_mp",
        nargs="?",
        type=int,
        default=1002422,
        help="Codigo da materia-prima. Padrao: 1002422",
    )
    args = parser.parse_args()

    destrinchar_mp(args.cd_mp)
