# Reposicao de Lojas LIEBE

Sistema local de inteligencia PCP para acompanhar reposicao permanente das lojas LIEBE em 2026. O projeto cruza vendas, estoque inicial, curva ABC, classificacoes de produto, entradas por lote/periodo e pedidos/transitos para responder, por loja e SKU, o que precisava chegar, o que chegou, o que faltou e o que foi enviado sem necessidade.

Este README e o ponto de continuidade do projeto. Quando abrir novamente com Codex, comece por aqui, depois leia `PROCESSO_REPOSICAO_CONTINUIDADE.md`, `TOTVS_PEDIDOS.md`, `backend/main.py`, `frontend/app/page.tsx`, `frontend/components/tables/MatrizReposicao.tsx` e `frontend/services/api.ts`.

## Estado atual em 2026-08-18

- Backend FastAPI em `backend/main.py`.
- Frontend Next.js em `frontend/`.
- Banco esperado: PostgreSQL com tabelas/views TOTVS/Power BI ja existentes no schema `public`.
- Frontend principal: `http://localhost:3001/`.
- API normal recomendada: `http://127.0.0.1:8001`.
- Nesta sessao local, a porta `8001` ficou presa em uma instancia antiga; foi validado backend atualizado em `8002` e `frontend/.env.local` foi apontado localmente para `http://127.0.0.1:8002`. Esse arquivo esta ignorado no Git.
- Nao publicar `.env`, logs, CSVs, `node_modules`, caches Python ou build local.

## Problema de negocio

A reposicao nao e somente enviar produto para loja. O objetivo e garantir o produto certo, na loja certa, no momento certo.

Dois cenarios precisam aparecer claramente:

- Ruptura: existe necessidade, mas a loja nao recebeu o suficiente.
- Envio sem necessidade: nao existia necessidade calculada, mas houve entrada para a loja/SKU.

Tambem existe a "morte silenciosa": SKU sem estoque para vender deixa de vender, perde sinal de demanda e para de aparecer como necessidade. Esse fluxo deve ser tratado separado do pedido normal, como recuperacao.

## Regra central da necessidade

A base analitica trabalha em nivel:

```text
mes > loja > referencia > produto/SKU > cor > tamanho
```

Conceito:

```text
media_mensal = vendas_3m / 3
estoque_minimo = regra por curva
necessidade = max(0, estoque_minimo - saldo_inicial)
faltou = max(0, necessidade - entrada_total)
```

Regra correta por curva:

- Curva A/AA: `estoque_minimo = media_mensal x 1.5`.
- Curva B/C: `estoque_minimo = media_mensal`.
- Nao descrever B/C como `media x 1.5`; isso foi corrigido no front.

Atendimento:

```text
SKU atendido = necessidade > 0 e entrada_total >= necessidade
SKU faltante = necessidade > 0 e entrada_total < necessidade
Entrada sem necessidade = necessidade <= 0 e entrada_total > 0
```

Importante: linhas completamente zeradas nao devem aparecer na matriz. Ou seja, se todas as colunas numericas relevantes forem zero, o front deve ocultar a linha.

## Entradas

O projeto separa entradas em:

- `entrada_periodo`: entrada ligada ao lote/periodo correto.
- `entrada_atrasada`: entrada de lote antigo.
- `entrada_sem_lote`: entrada sem lote mapeado.
- `entrada_total`: soma das entradas consideradas.
- `entrada_sem_necessidade`: parte da `entrada_total` onde `necessidade <= 0`.

Na visao de resumo, quando o filtro "Entrou sem necessidade" esta ligado, a necessidade deve zerar porque a base considerada e apenas `necessidade <= 0 AND entrada_total > 0`.

## Dashboard atual

Arquivo principal:

```text
frontend/app/page.tsx
```

Componentes principais:

```text
frontend/components/cards/MetricCard.tsx
frontend/components/charts/EvolucaoMensal.tsx
frontend/components/charts/ComparacaoLojas.tsx
frontend/components/tables/MatrizReposicao.tsx
frontend/components/tables/MatrizSkusSemReposicao.tsx
frontend/components/layout/PageContainer.tsx
frontend/components/layout/Sidebar.tsx
```

Cards do topo:

- Necessidade Total.
- Entrada Periodo.
- Entrada Atrasada.
- Sem Lote.
- Entrou sem necessidade.
- Taxa Atendimento.

Os cards foram ajustados para caberem na mesma linha em desktop usando a classe `dashboardMetrics`.

Filtros atuais do painel:

- Mes.
- Loja (`cd_loja`).
- Referencia (`referencia`, busca parcial com `ILIKE`).
- Entrou sem necessidade (`somente_entrada_sem_necessidade=true`).
- Status do produto.
- Continuidade.
- Linha.
- Familia.

O filtro `somente_entrada_sem_necessidade=true` precisa afetar todos estes endpoints ao mesmo tempo:

- `/api/dashboard/resumo-geral`
- `/api/dashboard/evolucao-mensal`
- `/api/dashboard/lojas-ranking`
- `/api/analise/matriz-reposicao`

## Diagnostico por Produto

Tela criada para responder perguntas minuciosas como:

```text
A loja Dom Luis pediu 4 pecas de cada cor Branco, Preto e Nude no tamanho M.
Havia necessidade mesmo?
Entrou sem necessidade?
Em algum mes anterior teve necessidade e isso se perdeu?
```

Rota frontend:

```text
/diagnostico-produto
```

Endpoint backend:

```text
GET /api/analise/diagnostico-produto
```

Filtros:

- `year`
- `mes_inicio`
- `mes_fim`
- `cd_loja`
- `referencia`
- `cor`
- `tamanho`
- `limit`

O endpoint filtra a exibicao por periodo, mas preserva o historico anterior do ano no calculo para conseguir mostrar:

- `maior_venda_3m_anterior`
- `ultimo_mes_com_estoque_anterior`
- `ultimo_mes_com_necessidade_anterior`
- `ultimo_mes_com_entrada_anterior`

Diagnosticos gerados:

- `ATENDIDO`: havia necessidade e a entrada total cobriu.
- `ATENDIDO PARCIAL`: havia necessidade, mas a entrada nao cobriu tudo.
- `TINHA NECESSIDADE E FALTOU`: havia necessidade e faltou peca.
- `ENTROU SEM NECESSIDADE`: nao havia necessidade calculada, mas entrou produto.
- `POSSIVEL DEMANDA PERDIDA`: sem necessidade/estoque atual, mas com venda historica anterior.
- `SEM NECESSIDADE COM ESTOQUE`: saldo inicial cobria a regra.
- `SEM MOVIMENTO`: sem sinal relevante no recorte.

Essa tela e o caminho correto para diagnosticar referencia/cor/tamanho por loja antes de discutir se um pedido manual fazia sentido.

## Matriz de Reposicao

Arquivo:

```text
frontend/components/tables/MatrizReposicao.tsx
```

Hierarquia visual atual:

```text
Empresa
  Referencia
    Cor/Tamanho/SKU
```

O usuario pediu para abrir para o lado, foi tentado, mas ficou ruim e foi revertido. Mantenha a expansao para baixo, compacta, como estava.

Colunas atuais:

- Necessidade.
- Periodo.
- Atrasada.
- Sem lote.
- Ent. sem nec.
- SKUs demanda.
- Atendidos.
- Faltantes.
- Pecas faltantes.
- Atend SKU.

Regras visuais ja aplicadas:

- Fundo do cabecalho/tabela foi clareado e separado em blocos de cor por familia de metrica.
- Hover em linhas de matriz deve "piscar" levemente. CSS atual usa `.matrixGroup:hover` e `.matrixSku:hover` com `@keyframes matrixRowBlink`.
- Nao deixar linha totalmente zero aparecer.
- Nao limitar a matriz por padrao; o backend aceita `limit`, mas o dashboard chama sem `limit` para os totais baterem.

Texto explicativo acima da matriz deve dizer claramente:

```text
Matriz de Reposicao
Empresa > Referencia > Cor/Tamanho. Consolida necessidade, entradas e atendimento por SKU.
Regra de necessidade: Curva A/AA usa media mensal dos ultimos 3 meses x 1,5 menos saldo inicial. Curva B/C usa somente a media mensal menos saldo inicial. Exemplo: se uma referencia Curva A vendeu 30 pecas em 3 meses, a media mensal e 10; a meta fica 15. Com saldo inicial 6, a necessidade e 9 pecas. Para Curva B/C, com a mesma media 10 e saldo 6, a necessidade seria 4 pecas.
```

## Backend

Arquivo principal:

```text
backend/main.py
```

Dependencias:

```text
backend/requirements.txt
```

Principais helpers:

- `get_connection()`: abre conexao PostgreSQL usando `.env`.
- `fetch_all()` / `fetch_one()`: executam SQL e retornam JSON seguro.
- `source_analytic_table()`: prioriza `cache_reposicao_analitico_classificado`; fallback `extrato_reposicao_loja_perm_analitico`.
- `source_summary_table()`: cria resumo agregado a partir da analitica quando existe; fallback para `cache_reposicao_resumo`.
- `product_classification_filter_sql()`: filtra classificacoes via tabelas TOTVS quando a analitica nao tem colunas classificadas.
- `product_classification_column_filter_sql()`: filtra classificacoes direto nas colunas do cache classificado.
- `scope_filter_sql()`: filtro comum por loja, referencia e entrada sem necessidade.

Filtro comum atual:

```python
def scope_filter_sql(alias, cd_loja=None, referencia=None, somente_entrada_sem_necessidade=None):
    # cd_loja: AND alias.cd_loja = %(cd_loja)s
    # referencia: AND alias.referencia ILIKE %(referencia)s
    # somente_entrada_sem_necessidade:
    #   AND alias.necessidade <= 0 AND alias.entrada_total > 0
```

Rotas principais:

```text
GET  /api/health
GET  /api/filtros/classificacoes
GET  /api/dashboard/resumo-geral
GET  /api/dashboard/evolucao-mensal
GET  /api/dashboard/lojas-ranking
GET  /api/dashboard/alertas
GET  /api/analise/matriz-reposicao
GET  /api/analise/diagnostico-produto
GET  /api/analise/skus-sem-reposicao
GET  /api/analise/skus-sem-reposicao/resumo
GET  /api/analise/por-mes/{mes}
GET  /api/analise/por-loja/{cd_loja}
GET  /api/analise/entradas/{mes}
GET  /api/analise/necessidade-zerada
GET  /api/micro/sku/{cd_produto}
GET  /api/micro/loja/{cd_loja}/criticos
GET  /api/micro/referencias-morrendo
GET  /api/cache/status
POST /api/cache/atualizar
POST /api/cache/atualizar-mes/{mes}
GET  /api/config/meses-relevantes
POST /api/config/meses-relevantes
GET  /api/config/ultima-atualizacao
GET  /api/processo-reposicao/resumo
GET  /api/processo-reposicao/sugestao
GET  /api/totvs/config-status
POST /api/processo-reposicao/pedido-totvs/preview
POST /api/processo-reposicao/pedido-totvs/enviar
GET  /api/reposicao/dashboard
GET  /api/reposicao/pedidos
GET  /api/reposicao/pedidos/{pedido_id}
PUT  /api/reposicao/pedidos/{pedido_id}/status
PUT  /api/reposicao/itens/{item_id}/status
```

## Processo de Reposicao

Arquivo:

```text
frontend/app/processo-reposicao/page.tsx
```

Rotas backend:

```text
GET  /api/processo-reposicao/resumo
GET  /api/processo-reposicao/sugestao
POST /api/processo-reposicao/pedido-totvs/preview
POST /api/processo-reposicao/pedido-totvs/enviar
```

Pedido normal deve olhar o periodo atual, nao mes antigo como `2026-06`.

Regra:

```text
falta_bruta = max(0, necessidade - entrada_total)
pendente_pedido = pedidos abertos do periodo atual
qtd_transito = 0 hoje
ja_programado = pendente_pedido + qtd_transito
qtd_sugerida_final = max(0, falta_bruta - ja_programado)
```

Hoje `qtd_transito = 0`. A pendencia tecnica importante e criar cache de transito e passar a abater:

```text
ja_programado = pendente_pedido + qtd_transito
```

Pedido por curva:

- Curva A/AA: pedido integral.
- Curva B/C primeira quinzena: `ceil(qtd_sugerida_final / 2)`.
- Curva B/C segunda quinzena: `floor(qtd_sugerida_final / 2)`.

Pedido de recuperacao de SKU morto/perdido deve ser fluxo separado, nao misturado com pedido normal.

## TOTVS Moda

Arquivos:

```text
backend/totvs_moda.py
TOTVS_PEDIDOS.md
```

Rotas:

```text
GET  /api/totvs/config-status
POST /api/processo-reposicao/pedido-totvs/preview
POST /api/processo-reposicao/pedido-totvs/enviar
```

O envio real exige:

```text
confirmar=true
```

E exige variaveis TOTVS completas no `.env`. Sem isso, a previa deve funcionar, mas envio real deve ficar bloqueado.

Operacao por loja:

```text
598: empresas 2,3,4,5,6,7,8,19,21,22
30:  empresas 10,14,15,20,120
310: empresa 17
```

Campos principais do pedido:

- `customerCode`: `dEMPRESA.cd_pessoa`.
- `productCode`: `dPRODUTO.idproduto`.
- `originalPrice`: `dPRODUTO.prcpfabrica`.
- `price`: `dPRODUTO.prcpfabrica`.
- `discountPercentage`: `0`.
- `discountValue`: `0`.
- `paymentConditionCode`: `1`.
- `representativeCode`: `32098` por padrao.

Variaveis relevantes estao em `.env.example`.

## Tabelas e fontes esperadas

O projeto depende de tabelas/views do banco da empresa. As mais importantes:

```text
cache_reposicao_analitico_classificado
extrato_reposicao_loja_perm_analitico
cache_reposicao_resumo
cache_reposicao_meta
reposicao_config
prd_produtoclas
prd_classificacao
vr_prd_prdgrade
vr_ger_empresa
ped_pedidoc
ped_pedidoi
tra_transacao
tra_transitem
dEMPRESA
dPRODUTO
```

Scripts SQL e Python na raiz documentam/recriam partes da analise historica, exemplos:

```text
criar_extrato_reposicao_loja_perm_analitico.sql
criar_extrato_reposicao_2026_completo.sql
carregar_2026_completo.py
carregar_agosto.py
recriar_extrato_reposicao_loja_perm.sql
auditoria_reposicao_junho_origem_base.sql
analise_reposicao.py
analise_reposicao_lojas.py
```

## Como rodar local

Backend:

```powershell
cd C:\Users\ce_lu\OneDrive\Documentos\geo2
python -m venv .venv
.\.venv\Scripts\pip.exe install -r backend\requirements.txt
copy .env.example .env
# preencher DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

Frontend:

```powershell
cd C:\Users\ce_lu\OneDrive\Documentos\geo2\frontend
npm install
copy .env.example .env.local
npm run dev -- -p 3001
```

URLs:

```text
Frontend: http://localhost:3001/
Backend health: http://127.0.0.1:8001/api/health
```

Se a porta `8001` ficar presa em uma instancia antiga no Windows, subir backend temporario em `8002` e alterar apenas `frontend/.env.local`:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8002
```

## Validacoes usadas

Backend:

```powershell
python -m py_compile backend\main.py
curl.exe -s "http://127.0.0.1:8001/api/health"
```

Frontend:

```powershell
cd frontend
npx tsc --noEmit
curl.exe -I "http://localhost:3001/"
```

Filtro de envio sem necessidade:

```powershell
curl.exe -s "http://127.0.0.1:8001/api/dashboard/resumo-geral?year=2026&month=2026-06&somente_entrada_sem_necessidade=true"
curl.exe -s "http://127.0.0.1:8001/api/analise/matriz-reposicao?year=2026&month=2026-06&somente_entrada_sem_necessidade=true&limit=5"
```

Resposta esperada na matriz: todas as linhas com `necessidade = 0`, `entrada_total > 0` e `entrada_sem_necessidade > 0`.

## Alteracoes recentes importantes

- Corrigida URL do front para apontar para API correta.
- Backend agora aceita filtros por loja e referencia no painel.
- Backend agora aceita `somente_entrada_sem_necessidade=true`.
- Dashboard adicionou filtro "Entrou sem necessidade".
- Dashboard adicionou card "Entrou sem necessidade".
- Matriz adicionou colunas `Necessidade` e `Ent. sem nec.`.
- Matriz deixou de aplicar `limit` por padrao para evitar total divergente dos cards.
- Texto explicativo da matriz foi corrigido para curva A/AA x1.5 e B/C media simples.
- Tentativa de abrir a matriz para o lado foi revertida por piorar visualizacao.
- Linhas totalmente zeradas devem ser ocultadas.
- Hover/piscada em linhas da matriz foi adicionado.
- Fundo escuro do cabecalho/tabela foi suavizado e separado por blocos de cor.

## Pontos de atencao para proximas sessoes

1. Confirmar se o front esta apontando para a porta correta no `.env.local`.
2. Se dados nao aparecem, testar primeiro `GET /api/health` e depois o endpoint do painel direto no backend.
3. Se `{"message":"Rota nao encontrada"}` aparecer em `3000`, provavelmente o usuario esta abrindo outro projeto/porta. Este front usa `3001`.
4. Nao voltar a limitar a matriz por padrao, porque isso faz os totais nao baterem com os cards.
5. Nao misturar pedido normal com recuperacao de SKU morto.
6. Antes de enviar pedido real TOTVS, checar `/api/totvs/config-status` e exigir `confirmar=true`.
7. Criar cache de transito antes de abater mercadoria em transito na sugestao.
8. Confirmar se operacao `140` deve contar como entrada de transferencia.
9. Padronizar encoding dos textos do frontend; alguns arquivos mostram caracteres quebrados em portugues.
10. Este repositorio deve continuar sem `.env`, CSVs grandes, logs e dependencias instaladas.

## Publicacao GitHub

Repositorio remoto solicitado:

```text
https://github.com/LucasCodeWorka/reporlojas.git
```

Como este workspace tinha uma pasta `.git` incompleta, o correto foi reinicializar o Git localmente, criar `.gitignore`, commitar o codigo util e configurar `origin` para o repositorio acima.
