# PROMPT DE MELHORIAS - FRONTEND REPOSICAO LIEBE

## PROBLEMAS ATUAIS A CORRIGIR

### 1. DESIGN - IGUALAR AO PLANO DE PRODUCAO

As cores e fontes DEVEM ser identicas ao sistema Plano de Producao existente.

**Cores corretas do Plano de Producao:**
```css
:root {
  /* Fundo e paineis */
  --bg: #f5f6fa;
  --panel: #ffffff;
  --panel-border: #e8eaef;

  /* Texto */
  --text-primary: #1a1d21;
  --text-secondary: #5c6370;
  --text-muted: #8b95a5;

  /* Rosa LIEBE - sidebar */
  --liebe-primary: #c41e56;
  --liebe-dark: #9a1743;
  --liebe-light: #e8cdd6;

  /* Status */
  --status-ok: #27ae60;
  --status-warn: #f39c12;
  --status-error: #e74c3c;
  --status-info: #3498db;

  /* Cards coloridos do topo - cores pasteis */
  --card-pink: #ffeef4;
  --card-blue: #eef6ff;
  --card-amber: #fff8e6;
  --card-gray: #f4f5f7;
  --card-red: #ffeeee;
  --card-green: #eefff4;
}
```

**Fonte correta:**
```css
body {
  font-family: 'Nunito', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px;
  font-weight: 400;
  letter-spacing: -0.01em;
}

h1, h2, h3 {
  font-weight: 700;
  letter-spacing: -0.02em;
}

.eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--liebe-primary);
}
```

**Sidebar identica ao Plano:**
- Fundo: gradiente de #9a1743 para #6d1030
- Sombra interna sutil
- Separadores de secao mais finos
- Icones com 16px
- Links com font-weight: 600 (nao 700)

### 2. CONFIGURACOES - MELHORIAS

A pagina de configuracoes deve permitir:

**Selecao de meses para media:**
- Checkboxes para selecionar quais meses usar no calculo
- Opcao "Ultimos 3 meses" (padrao)
- Opcao "Ultimos 6 meses"
- Opcao "Customizado" - selecionar meses especificos

**Multiplicador POR CURVA:**
```
CURVA AA: [ 2.0 ]
CURVA A:  [ 1.5 ]
CURVA B:  [ 1.2 ]
CURVA C:  [ 1.0 ]
```

Cada curva tem seu proprio multiplicador de estoque minimo.

### 3. DASHBOARD - ANALISE MAIS PROFUNDA

O dashboard atual mostra dados agregados. Precisa mostrar:

**Cards do topo (manter, mas ajustar cores pasteis):**
- Necessidade Total (rosa pastel)
- Entrada Periodo (azul pastel)
- Entrada Atrasada (amarelo pastel)
- Sem Lote (cinza pastel)
- Faltou (vermelho pastel se faltou, verde se OK)

**Novo bloco: Alicerces da Analise**
Criar secao com metricas fundamentais:

```
+------------------------------------------+
| FUNDAMENTOS DA REPOSICAO                 |
+----------+----------+----------+---------+
| Media    | Estoque  | SKUs     | Taxa    |
| Venda    | Minimo   | Abaixo   | Atend.  |
|          | Total    | Meta     |         |
| 12.450   | 36.854   | 4.194    | 106.9%  |
+----------+----------+----------+---------+
```

**Novo grafico: Media de Venda 12 meses**
Grafico de linha mostrando evolucao da media de venda:
- Eixo X: meses (Jan a Ago)
- Eixo Y: media de venda total
- Linha rosa LIEBE

**Novo grafico: Correlacao Falta x Queda de Venda**
Grafico de dispersao ou linha dupla mostrando:
- Linha 1: Falta acumulada
- Linha 2: Media de venda
- Hipotese: faltas nao atendidas = queda na media

### 4. NOVA PAGINA: ANALISE DETALHADA

Criar `/analise` com tabela completa dos dados.

**Fonte de dados:**
```sql
SELECT * FROM extrato_reposicao_loja_perm_analitico
WHERE mes = '2026-06'
ORDER BY nome_loja, referencia;
```

**Colunas da tabela:**
| Coluna | Descricao |
|--------|-----------|
| Loja | nome_loja |
| Referencia | referencia |
| Produto | descricao_produto (truncado) |
| Curva | curva_completa |
| Vendas 3m | vendas_3m |
| Media | media_mensal |
| Est. Min | estoque_minimo |
| Saldo Ini | saldo_inicial |
| Necessidade | necessidade |
| Ent. Periodo | entrada_periodo |
| Ent. Atrasada | entrada_atrasada |
| Ent. Sem Lote | entrada_sem_lote |
| Ent. Total | entrada_total |
| Faltou | faltou |
| Status | status_reposicao |

**Filtros da tabela:**
- Mes (select)
- Loja (select multiple ou chips)
- Curva (chips: A, AA, B, C, Sem Curva)
- Status (chips: OK, PARCIAL, ZERADO, SEM NECESSIDADE)
- Busca por referencia

**Paginacao:**
- 50 registros por pagina
- Navegacao entre paginas

### 5. SEPARAR ENTRADAS

Criar visualizacao clara dos 3 tipos de entrada:

**Card de Entradas do Mes:**
```
+--------------------------------------------------+
| ENTRADAS - JUNHO 2026                            |
+----------------+----------------+----------------+
| DO PERIODO     | ATRASADAS      | SEM LOTE       |
| (lote 26.06%)  | (lotes antigos)| (sem identif.) |
|                |                |                |
|     8.524      |      770       |    20.769      |
|    28.4%       |     2.6%       |     69.1%      |
+----------------+----------------+----------------+
```

**Grafico de pizza:**
Distribuicao percentual das entradas por tipo.

### 6. HISTORICO DE 12 MESES

Criar tabela/grafico de evolucao:

```
+-----+--------+--------+--------+-------+--------+
| Mes | Necess | Entrada| Faltou | Taxa  | Media  |
|     |        |        |        |       | Venda  |
+-----+--------+--------+--------+-------+--------+
| Jan | 10.832 | 25.235 |  3.284 | 233%  | 12.100 |
| Fev |  6.541 | 15.105 |  3.262 | 231%  | 11.800 |
| Mar |  7.288 | 17.129 |  3.301 | 235%  | 11.950 |
| Abr |  6.701 |  9.607 |  4.490 | 143%  | 11.200 |
| Mai | 10.784 | 26.418 |  6.431 | 245%  | 12.500 |
| Jun | 11.487 | 30.063 |  5.482 | 262%  | 12.800 |
| Jul |  9.178 | 44.341 |  2.459 | 483%  | 13.100 |
| Ago |  9.301 |  9.939 |  7.954 | 107%  | 13.200 |
+-----+--------+--------+--------+-------+--------+
```

### 7. ENDPOINT ADICIONAL NO BACKEND

Criar endpoint para media de venda mensal:

```python
@app.get("/api/analise/media-venda-mensal")
def media_venda_mensal(year: int = 2026):
    """
    Retorna a media de venda total por mes.
    """
    query = """
    SELECT
        mes,
        SUM(media_mensal) AS media_venda_total,
        COUNT(DISTINCT cd_produto) AS qtd_skus,
        COUNT(DISTINCT cd_loja) AS qtd_lojas
    FROM extrato_reposicao_loja_perm_analitico
    WHERE mes LIKE %(year_like)s
    GROUP BY mes
    ORDER BY mes
    """
    return fetch_all(query, {"year_like": f"{year}-%"})
```

Criar endpoint para dados detalhados paginados:

```python
@app.get("/api/analise/detalhado")
def analise_detalhada(
    mes: str,
    loja: int | None = None,
    curva: str | None = None,
    status: str | None = None,
    referencia: str | None = None,
    page: int = 1,
    per_page: int = 50
):
    """
    Retorna dados detalhados da tabela analitica com filtros e paginacao.
    """
    # Construir filtros dinamicamente
    # Retornar com total_pages, total_records, data
```

### 8. ESTRUTURA DE ARQUIVOS A CRIAR/MODIFICAR

```
frontend/
├── app/
│   ├── page.tsx                    # MODIFICAR - adicionar graficos
│   ├── analise/
│   │   └── page.tsx               # CRIAR - tabela detalhada
│   ├── configuracoes/
│   │   └── page.tsx               # MODIFICAR - meses e multiplicadores
│   └── globals.css                 # MODIFICAR - cores corretas
│
├── components/
│   ├── charts/
│   │   ├── MediaVendaMensal.tsx   # CRIAR
│   │   ├── CorrelacaoFaltaVenda.tsx # CRIAR
│   │   └── PizzaEntradas.tsx      # CRIAR
│   ├── cards/
│   │   └── FundamentosCard.tsx    # CRIAR
│   └── tables/
│       └── TabelaAnalitica.tsx    # CRIAR
│
└── services/
    └── api.ts                      # MODIFICAR - novos endpoints
```

### 9. EXEMPLO DE CORES CORRETAS NOS CARDS

```tsx
// Cores pasteis como no Plano de Producao
<div className="metricCard" style={{
  background: '#ffeef4',  // Rosa pastel
  borderLeftColor: '#c41e56'
}}>

<div className="metricCard" style={{
  background: '#eef6ff',  // Azul pastel
  borderLeftColor: '#3498db'
}}>

<div className="metricCard" style={{
  background: '#fff8e6',  // Amarelo pastel
  borderLeftColor: '#f39c12'
}}>
```

### 10. CHECKLIST DE VALIDACAO

Antes de considerar pronto, verificar:

- [ ] Fonte Nunito carregada e aplicada
- [ ] Cores identicas ao Plano de Producao
- [ ] Sidebar com gradiente correto
- [ ] Cards com fundo pastel (nao branco)
- [ ] Eyebrow em uppercase com letter-spacing
- [ ] Configuracoes permite selecionar meses
- [ ] Multiplicador configuravel por curva
- [ ] Tabela analitica com todos os campos
- [ ] Filtros funcionando
- [ ] Grafico de media de venda
- [ ] Separacao clara dos tipos de entrada
- [ ] Historico de 12 meses visivel

---

## PRIORIDADE DE IMPLEMENTACAO

1. **URGENTE**: Corrigir cores e fontes (globals.css)
2. **ALTA**: Criar pagina de analise detalhada
3. **ALTA**: Melhorar configuracoes (meses + curvas)
4. **MEDIA**: Adicionar graficos de media de venda
5. **MEDIA**: Historico de 12 meses

---

**IMPORTANTE**: O design deve ser IDENTICO ao Plano de Producao. Nao inventar cores ou estilos novos. Copiar exatamente o que ja existe.
