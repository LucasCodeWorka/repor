# Contexto de Continuidade - 2026-09-02

Este arquivo guarda o contexto da sessao em que foram ajustadas as telas:

- `http://localhost:3000/processo-reposicao`
- `http://localhost:3000/media-12m-impacto`

Leia este arquivo antes de continuar o projeto.

## Estado geral

Projeto local em:

```text
C:\Users\ce_lu\OneDrive\Documentos\geo2
```

Frontend:

```text
http://localhost:3000
```

Backend usado pelo frontend:

```text
http://127.0.0.1:8001
```

Importante: o backend `8001` estava rodando sem `--reload`. Sempre que alterar `backend/main.py` ou `backend/totvs_moda.py`, reinicie o processo `uvicorn` na porta `8001`.

Comando que funcionou para subir o backend:

```powershell
Start-Process -FilePath "C:\Python312\python.exe" -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001") -WorkingDirectory "C:\Users\ce_lu\OneDrive\Documentos\geo2\backend" -WindowStyle Hidden
```

Nao subir a partir da raiz com `backend.main:app`, porque `backend/main.py` importa `totvs_moda` como modulo local.

## Arquivos alterados nesta sequencia

- `backend/main.py`
- `backend/totvs_moda.py`
- `frontend/app/processo-reposicao/page.tsx`
- `frontend/app/media-12m-impacto/page.tsx`
- `frontend/app/globals.css`
- `frontend/types/reposicao.ts`

Validacoes rodadas:

```text
python -m py_compile backend\main.py backend\totvs_moda.py
node node_modules\typescript\bin\tsc -p tsconfig.json --noEmit
```

Ambas passaram.

## Processo de Reposicao

Problema encontrado:

- A API `/api/processo-reposicao/resumo` retornava `5.242` pecas.
- A API `/api/processo-reposicao/sugestao` ainda retornava linhas antigas que somavam `4.286` pecas.
- A tela somava as linhas de `sugestao`, por isso nao atualizava.
- Causa: cache antigo de painel e backend `8001` sem reload.

Correcao:

- Em `backend/main.py`, versoes de cache alteradas para invalidar dados antigos:
  - `processo_resumo_v6_sem_abater_entrada`
  - `processo_sugestao_v6_sem_abater_entrada`
- A regra atual do pedido normal deixou de abater `entrada_total`.
- O calculo ficou:

```text
estoque_minimo = media * multiplicador_curva
necessidade = max(0, estoque_minimo - saldo_inicial)
qtd_sugerida = max(0, necessidade - qtd_pendente_pedido)
qtd_transito = 0 por enquanto
qtd_ja_programada = qtd_pendente_pedido
```

Numeros validados depois do ajuste:

```text
Resumo API: 5.242 pecas / 2.692 SKUs
Soma das linhas da sugestao: 5.242 pecas / 2.692 SKUs
```

Previa TOTVS validada:

```text
CURVA_A_AA: 3.476 pecas
CURVA_BC_1: 1.400 pecas
CURVA_BC_2: 366 pecas
Total: 5.242 pecas
```

Tambem foi alinhada a memoria visual do frontend para parar de mostrar `Nec - Entrada - Prog`.

Agora a memoria correta e:

```text
Necessidade - Ja Programado = Pedido
```

Cobertura alinhada em `backend/totvs_moda.py`:

```text
cobertura_atual = saldo_inicial / media_mensal
cobertura_pos = (saldo_inicial + qtd_ja_programada + qtd_pedido) / media_mensal
```

## Media 12m Impacto

Tela:

```text
frontend/app/media-12m-impacto/page.tsx
```

Endpoint:

```text
GET /api/analise/media-12m-impacto
```

Objetivo da melhoria pedida pelo chefe:

> Melhorar a secao "Diagnostico por Curva" para mostrar se o problema esta concentrado nos produtos que deveriam ter maior protecao e permitir validar de forma granular por loja.

### Correcao conceitual importante

Primeira tentativa comparou estoque minimo 3m contra estoque minimo 12m puro. Isso mostrou queda, o que nao fazia sentido para a regra de protecao.

Regra correta validada com o usuario:

```text
estoque_minimo_3m = media_3m * multiplicador_curva
estoque_minimo_12m_protegido = max(media_3m, media_12m) * multiplicador_curva
```

Assim a regra 12m protegida nunca reduz a base frente ao 3m.

Em `backend/main.py`, no CTE `calculado`, `estoque_minimo_12m` passou a usar:

```sql
ROUND(
    GREATEST(COALESCE(media_antiga_3m, 0), COALESCE(media_nova_12m, 0))
    * CASE WHEN curva_completa IN ('CURVA A', 'CURVA AA') THEN 1.5 ELSE 1.0 END,
    0
) AS estoque_minimo_12m
```

Tambem foi recalculado `estoque_minimo_antigo` dentro da propria analise, usando a mesma regra de curva:

```text
A/AA = 1.5
B/C = 1.0
```

Isso evita comparar contra coluna antiga da tabela analitica que podia usar outro multiplicador.

Versao de cache atual da analise:

```text
media_12m_impacto_v9_necessidade_antes_depois
```

### Numeros validados

Depois da correcao:

```text
Estoque minimo 3m geral: 28.838
Estoque minimo 12m protegido: 35.041
Dif. estoque minimo: +6.203
```

Por curva:

```text
CURVA A:
  Est. min. 3m: 10.575
  Est. min. 12m protegido: 13.236
  Dif.: +2.661
  Nec. 3m: 2.578
  Nec. 12m: 3.267
  Dif. nec.: +689

CURVA AA:
  Est. min. 3m: 13.702
  Est. min. 12m protegido: 15.625
  Dif.: +1.923
  Nec. 3m: 3.287
  Nec. 12m: 3.844
  Dif. nec.: +557

CURVA B:
  Est. min. 3m: 4.561
  Est. min. 12m protegido: 6.180
  Dif.: +1.619
  Nec. 3m: 1.088
  Nec. 12m: 1.483
  Dif. nec.: +395
```

### Diagnostico por Curva expandido por loja

Foi criado no backend um agregado completo:

```text
por_curva_loja
```

Motivo: nao usar `rows` da tabela de SKUs para agregar por loja, porque `rows` e limitado pelo parametro `limit=1200`. O agregado `por_curva_loja` vem completo da query SQL.

Campos adicionados:

```text
skus_3m
skus_12m
skus_com_gap
necessidade_3m_total
necessidade_12m_total
gap_necessidade_total
estoque_minimo_3m_total
estoque_minimo_12m_total
gap_estoque_minimo_total
```

No frontend:

- Cada card de curva agora pode expandir.
- Ao expandir, mostra uma tabela por loja.
- A tabela por loja foi ajustada para ficar compacta.
- O codigo da loja aparece em badge pequeno.
- Nome da loja fica em uma linha com ellipsis para nao ficar gigante.

Colunas atuais da tabela expandida por loja:

```text
Loja
Est. min. 3m
Est. min. prot.
Dif.
Nec. 3m
Nec. 12m
Dif. nec.
SKUs gap
```

Importante: o usuario nao gostou da coluna `Novos`; ela foi removida porque confundia. A leitura correta deve ser por necessidade total somada:

```text
Nec. 3m = quanto pediria pela regra atual, em pecas
Nec. 12m = quanto pediria pela regra protegida, em pecas
Dif. nec. = aumento de necessidade em pecas
```

`SKUs gap` fica apenas como apoio, nao como leitura principal.

Exemplo validado:

```text
CURVA A / LIEBE PORTO ALEGRE
Nec. 3m: 280
Nec. 12m: 374
Dif. nec.: +94
SKUs gap: 62
```

### Proximo passo pedido pelo usuario

Depois de validar por loja, ele quer abrir por classificacao de linha.

Provavel implementacao:

1. Criar agregado `por_curva_loja_linha` no backend.
2. Agrupar por:

```text
curva_completa
cd_loja
nome_loja
linha
```

3. Retornar os mesmos campos:

```text
necessidade_3m_total
necessidade_12m_total
gap_necessidade_total
estoque_minimo_3m_total
estoque_minimo_12m_total
gap_estoque_minimo_total
skus_com_gap
ruptura_silenciosa
qtd_recuperavel
```

4. No frontend, permitir expandir uma loja para ver as linhas.

## Cuidados

- Nao voltar a usar `entrada_total` como abatimento do pedido normal, a menos que o usuario confirme nova regra.
- Nao chamar `skus_com_gap` de `Novos`.
- Para apresentacao ao chefe, usar sempre:

```text
3m atual vs 12m protegido
Necessidade em pecas
Diferença em pecas
```

- `SKUs gap` e um indicador auxiliar, nao deve ser a coluna principal.

## Estado do git no fim desta sessao

Havia arquivos modificados:

```text
backend/main.py
backend/totvs_moda.py
frontend/app/globals.css
frontend/app/media-12m-impacto/page.tsx
frontend/app/processo-reposicao/page.tsx
frontend/types/reposicao.ts
```

Este arquivo foi criado para continuidade:

```text
CONTEXTO_CONTINUIDADE_2026-09-02.md
```

