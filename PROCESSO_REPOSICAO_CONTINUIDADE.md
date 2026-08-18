# Processo de Reposicao - continuidade

Data do contexto: 2026-08-07.

## Objetivo atual

O pedido normal de reposicao deve responder:

> Quanto precisamos enviar hoje, no periodo atual, respeitando as regras de curva e abatendo o que ja esta programado para chegar.

Nao deve gerar pedido normal olhando mes antigo como `2026-06`.

Pedidos fora dessa regra, para recuperar SKU perdido/morto, devem virar outro fluxo: **pedido de recuperacao**.

## O que ja foi implementado

### Frontend

Pagina:

- `frontend/app/processo-reposicao/page.tsx`

Rota:

- `http://127.0.0.1:3000/processo-reposicao`

Comportamento atual:

- Usa sempre o periodo atual pelo navegador: `new Date().toISOString().slice(0, 7)`.
- Exibe matrizes de pedido:
  - `Pedido Curva A/AA`
  - `Pedido Curva B/C - 1a quinzena`
  - `Pedido Curva B/C - 2a quinzena`
- Hierarquia visual:
  - Empresa
  - Referencia
  - SKU / Cor / Tamanho
- A matriz agora mostra no nivel SKU:
  - Pendente
  - Cobertura atual
  - Cobertura pos-reposicao
  - Memoria de calculo
- A secao `Previa TOTVS` gera uma previa por loja.
- Cada linha da previa TOTVS e clicavel e abre modal com os itens do pedido.
- O modal mostra:
  - Ref
  - Cor
  - Tam
  - SKU
  - Qtd
  - Cob. atual
  - Cob. pos
  - Preco
  - Memoria

### Backend

Arquivos:

- `backend/main.py`
- `backend/totvs_moda.py`

Endpoints principais:

- `GET /api/processo-reposicao/resumo`
- `GET /api/processo-reposicao/sugestao`
- `POST /api/processo-reposicao/pedido-totvs/preview`
- `POST /api/processo-reposicao/pedido-totvs/enviar`
- `GET /api/totvs/config-status`

O envio real para TOTVS ainda exige `confirmar=true` e configuracao completa.

## Regra de pedido por curva

### Curva A / AA

Pedido normal:

```text
qtd_pedido = qtd_sugerida_final
```

### Curva B / C

Dividido em duas partes no mes:

```text
1a quinzena = ceil(qtd_sugerida_final / 2)
2a quinzena = floor(qtd_sugerida_final / 2)
```

## Calculo atual da sugestao

A base vem de `cache_reposicao_analitico_classificado` quando existe; se nao existir, usa `extrato_reposicao_loja_perm_analitico`.

No backend, a sugestao por SKU calcula:

```text
falta_bruta = max(0, necessidade - entrada_total)
pendente_pedido = pedidos abertos do periodo atual
ja_programado = pendente_pedido + transito
qtd_sugerida_final = max(0, falta_bruta - ja_programado)
```

Hoje, no codigo:

```text
qtd_transito = 0
ja_programado = pendente_pedido
```

Ou seja: **pedido pendente ja esta sendo abatido**, mas **em transito ainda nao esta aplicado**.

## Pendente: o que significa e como esta calculado

Pendente e o pedido ja criado para a loja, mas ainda nao atendido/faturado.

Tabelas:

- Cabecalho: `ped_pedidoc`
- Itens: `ped_pedidoi`
- Loja destino: `dEMPRESA.cd_pessoa = ped_pedidoc.cd_cliente`

Regra atual no backend:

```sql
ped_pedidoc.cd_empresa = 1
ped_pedidoc.dt_pedido dentro do mes atual
ped_pedidoc.tp_situacao IN (1, 3)
ped_pedidoc.cd_operacao IN (30, 598, 310)
```

Quantidade pendente por loja/SKU:

```sql
max(0, qt_solicitada - qt_atendida - qt_cancelada)
```

Consulta-base usada no backend:

```sql
SELECT
    de.idempresa AS cd_loja,
    i.cd_produto,
    SUM(
        GREATEST(
            0,
            COALESCE(i.qt_solicitada, 0)
            - COALESCE(i.qt_atendida, 0)
            - COALESCE(i.qt_cancelada, 0)
        )
    ) AS qtd_pendente_pedido
FROM ped_pedidoc c
JOIN ped_pedidoi i
    ON i.cd_empresa = c.cd_empresa
   AND i.cd_pedido = c.cd_pedido
JOIN public."dEMPRESA" de
    ON de.cd_pessoa = c.cd_cliente
WHERE c.cd_empresa = 1
  AND c.dt_pedido >= (:month || '-01')::date
  AND c.dt_pedido < ((:month || '-01')::date + INTERVAL '1 month')
  AND c.tp_situacao IN (1, 3)
  AND c.cd_operacao IN (30, 598, 310)
GROUP BY de.idempresa, i.cd_produto;
```

Validacao feita em 2026-08:

- `tp_situacao = 1`, operacoes `30/598`: pedidos abertos com saldo pendente.
- `tp_situacao = 4`: pedidos atendidos/faturados, saldo pendente zero.
- `tp_situacao = 6`: cancelado, saldo pendente zero.

## Em transito: entendimento atual

Em transito e o produto que ja saiu/faturou da fabrica, mas ainda nao entrou confirmado na loja.

Pelo mapeamento encontrado:

### Saida da fabrica

Tabela:

- `tra_transacao`
- `tra_transitem`

Padrao:

```text
tra_transacao.cd_empresa = 1
tra_transacao.cd_pessoa = dEMPRESA.cd_pessoa da loja destino
tra_transacao.cd_operacao IN (30, 598, 310)
tra_transacao.tp_situacao = 4
```

Operacoes de saida:

- `30`  = saida transf.
- `598` = saida transf. Fortaleza
- `310` = saida transf. Recife

### Entrada na loja

Tabela:

- `tra_transacao`
- `tra_transitem`

Padrao encontrado:

```text
entrada.cd_empresa = loja
entrada.cd_empresaori = 1
entrada.nr_transacaoori = nr_transacao da saida da fabrica
entrada.tp_situacao = 4
```

Operacoes de entrada vistas:

- `31`
- `599`
- `311`
- `140` apareceu em algumas entradas e precisa ser confirmado se deve entrar na regra final.

Exemplo validado:

```text
Saida fabrica:
cd_empresa = 1
nr_transacao = 1926427
operacao = 598
qtd = 110

Entrada loja:
cd_empresa = 2
nr_transacao = 1927008
operacao = 599
cd_empresaori = 1
nr_transacaoori = 1926427
qtd = 110
```

Esse exemplo mostra que, quando existe entrada confirmada, a saida nao deve mais ser considerada em transito.

## Regra candidata para em transito

Ainda nao aplicada no calculo.

Regra proposta:

```text
transito por SKU/loja =
  quantidade de saidas da fabrica confirmadas
  - quantidade de entradas da loja confirmadas vinculadas a essas saidas
```

Em SQL conceitual:

```sql
saidas:
  s.cd_empresa = 1
  s.cd_operacao IN (30, 598, 310)
  s.tp_situacao = 4
  s.cd_pessoa = dEMPRESA.cd_pessoa

entradas:
  e.cd_empresa = dEMPRESA.idempresa
  e.cd_empresaori = 1
  e.nr_transacaoori = s.nr_transacao
  e.tp_situacao = 4
  e.cd_operacao IN (31, 599, 311)

transito = max(0, saida_item - entrada_item)
```

Ponto de atencao:

- A medicao completa por SKU ainda ficou pesada usando as tabelas transacionais.
- Recomendo criar uma tabela/cache materializado para isso antes de aplicar no pedido.

## Cache recomendado para transito

Criar uma tabela materializada ou cache:

```text
cache_reposicao_transito
```

Campos sugeridos:

```text
mes
cd_loja
nome_loja
cd_produto
referencia
cor
tamanho
qtd_saida_fabrica
qtd_entrada_loja
qtd_transito
ultima_saida_fabrica
ultima_entrada_loja
transacoes_saida
transacoes_entrada
atualizado_em
```

Depois o calculo da reposicao deve virar:

```text
ja_programado = qtd_pendente_pedido + qtd_transito
qtd_sugerida_final = max(0, falta_bruta - ja_programado)
```

## Previa TOTVS

O backend monta um pedido por loja.

Campos por pedido:

- `orderId`: `TRANSF-YYYY-MM-TIPO-cd_loja`
- `customerCode`: `dEMPRESA.cd_pessoa`
- `operationCode`: regra por empresa
- `paymentConditionCode`: `1`
- `representativeCode`: default `32098`

Campos por item:

- `productCode`: `dPRODUTO.idproduto`
- `reference`: referencia
- `color`: cor
- `size`: tamanho
- `quantity`: qtd pedido
- `originalPrice`: `dPRODUTO.prcpfabrica`
- `price`: `dPRODUTO.prcpfabrica`
- `discountPercentage`: `0`
- `discountValue`: `0`
- `currentCoverage`
- `projectedCoverage`
- `calculationMemory`

## Operacao por empresa

```text
598: empresas 2,3,4,5,6,7,8,19,21,22
30:  empresas 10,14,15,20,120
310: empresa 17
```

## Precos

Foi alinhado com o modelo Power BI mais recente:

```text
originalPrice = dPRODUTO.prcpfabrica
price = dPRODUTO.prcpfabrica
discountPercentage = 0
discountValue = 0
```

## Cobertura

Cobertura atual:

```text
(saldo_inicial + entrada_total) / media_mensal
```

Cobertura pos-reposicao:

```text
(saldo_inicial + entrada_total + ja_programado + qtd_pedido) / media_mensal
```

Se `media_mensal <= 0`, cobertura fica `0`.

## Memoria de calculo exibida

Versao compacta na matriz:

```text
Nec X - Ent Y - Pend Z = Ped W
```

No payload da previa, a memoria completa inclui:

```text
mediaMensal
saldoInicial
entradaTotal
necessidade
faltaBruta
pendentePedido
transito
jaProgramado
pedidoFinal
```

## Configuracao TOTVS pendente

Sem gravar credenciais no codigo.

Ainda precisam ser configurados no ambiente:

```text
TOTVS_TOKEN_URL
TOTVS_ORDER_URL
TOTVS_CLIENT_ID
TOTVS_CLIENT_SECRET
TOTVS_USERNAME
TOTVS_PASSWORD
TOTVS_BRANCH_CODE
```

Enquanto esses campos faltarem:

- A previa funciona.
- O envio real nao deve ser liberado.

## Proximos passos recomendados

1. Criar cache/materializada de transito por loja/SKU.
2. Validar se operacao `140` deve contar como entrada de transferencia ou se deve ficar fora.
3. Alterar `backend/main.py` para juntar `cache_reposicao_transito`.
4. Trocar:

```text
qtd_transito = 0
```

por:

```text
qtd_transito = cache_reposicao_transito.qtd_transito
```

5. Ajustar memoria:

```text
Nec X - Ent Y - Pend P - Trans T = Ped W
```

6. Criar fluxo separado para `Pedidos de Recuperacao`, sem misturar com o pedido normal do periodo atual.
