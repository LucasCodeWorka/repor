# SISTEMA DE INTELIGENCIA DE REPOSICAO LIEBE

## VISAO DO ESPECIALISTA EM PCP

### O Problema Central
A reposicao de lojas nao e apenas "mandar produtos". E garantir que **o produto certo chegue na loja certa no momento certo**. Quando isso falha, temos dois cenarios criticos:

1. **RUPTURA** - Cliente quer comprar, produto nao esta la. Venda perdida para sempre.
2. **MORTE SILENCIOSA** - Produto zerou, parou de vender, saiu da curva, "nao tem mais necessidade". O sistema para de pedir porque "nao vende". Mas nao vende porque nao tem!

### Metricas que Importam (Visao PCP)

**MACRO (Saude da Operacao)**
- Taxa de atendimento da necessidade por mes
- Evolucao do gap (falta) ao longo dos meses
- Lojas criticas vs lojas saudaveis
- Referencias que estao "morrendo" (tinham curva, agora nao pedem mais)

**MICRO (Diagnostico)**
- SKU a SKU: o que zerou e nunca mais voltou?
- Qual loja esta sendo negligenciada?
- Qual lote esta chegando atrasado sistematicamente?
- Qual referencia curva A esta sem estoque?

---

## ARQUITETURA DO SISTEMA

### Backend (FastAPI + PostgreSQL)

```
/api
├── /config
│   ├── GET  /meses-relevantes         # Retorna config de meses para media
│   ├── POST /meses-relevantes         # Salva config
│   └── GET  /ultima-atualizacao       # Quando o cache foi atualizado
│
├── /cache
│   ├── POST /atualizar                # Dispara recalculo do cache
│   ├── GET  /status                   # Status do processamento
│   └── POST /atualizar-mes/{mes}      # Atualiza apenas um mes
│
├── /dashboard
│   ├── GET /resumo-geral              # Cards do topo (totais)
│   ├── GET /evolucao-mensal           # Grafico de linha (necessidade vs entrada vs falta)
│   ├── GET /lojas-ranking             # Ranking de lojas por atendimento
│   └── GET /alertas                   # SKUs criticos, referencias morrendo
│
├── /analise
│   ├── GET /por-loja/{cd_loja}        # Detalhe de uma loja
│   ├── GET /por-mes/{mes}             # Detalhe de um mes
│   ├── GET /por-referencia/{ref}      # Historico de uma referencia
│   ├── GET /entradas/{mes}            # Entradas: periodo, atrasada, sem_lote
│   └── GET /necessidade-zerada        # SKUs que zeraram e pararam de ter necessidade
│
├── /micro
│   ├── GET /sku/{cd_produto}          # Historico completo de um SKU
│   ├── GET /loja/{cd_loja}/criticos   # SKUs criticos nessa loja
│   └── GET /referencias-morrendo      # Referencias que tinham venda e sumiram
│
└── /export
    ├── GET /excel/{tipo}              # Exporta para Excel
    └── GET /csv/{tipo}                # Exporta para CSV
```

### Estrutura do Cache (Tabelas Materializadas)

```sql
-- Cache principal (atualizado sob demanda)
CREATE TABLE cache_reposicao_resumo (
    id SERIAL PRIMARY KEY,
    mes VARCHAR(7),
    cd_loja INTEGER,
    nome_loja VARCHAR(100),

    -- Totais
    qtd_skus INTEGER,
    qtd_skus_demanda INTEGER,

    -- Necessidade
    estoque_minimo_total NUMERIC,
    saldo_inicial_total NUMERIC,
    necessidade_total NUMERIC,

    -- Entradas por tipo
    entrada_periodo NUMERIC,
    entrada_atrasada NUMERIC,
    entrada_sem_lote NUMERIC,
    entrada_total NUMERIC,

    -- Gaps
    faltou NUMERIC,
    taxa_atendimento NUMERIC,  -- entrada_total / necessidade * 100

    -- Status counts
    skus_ok INTEGER,
    skus_parcial INTEGER,
    skus_zerados INTEGER,
    skus_sem_necessidade INTEGER,

    -- Metadata
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Cache de SKUs criticos (os que zeraram e sumiram)
CREATE TABLE cache_skus_mortos (
    cd_produto BIGINT,
    cd_loja INTEGER,
    referencia VARCHAR(50),
    curva_original VARCHAR(20),      -- Qual era a curva quando vendia
    ultimo_mes_com_venda VARCHAR(7), -- Quando parou de vender
    ultimo_mes_com_estoque VARCHAR(7),
    meses_sem_estoque INTEGER,
    vendas_historico NUMERIC,        -- Quanto vendia antes
    status TEXT                       -- 'MORTO', 'CRITICO', 'RECUPERANDO'
);

-- Cache de evolucao mensal (para graficos)
CREATE TABLE cache_evolucao_mensal (
    mes VARCHAR(7),
    cd_loja INTEGER,
    necessidade NUMERIC,
    entrada_total NUMERIC,
    faltou NUMERIC,
    gap_acumulado NUMERIC,  -- Soma das faltas dos meses anteriores
    taxa_atendimento NUMERIC
);
```

### Funcao de Atualizacao do Cache

```python
# backend/services/cache_service.py

async def atualizar_cache_completo():
    """
    Atualiza todo o cache de reposicao.
    Deve ser chamado manualmente ou por scheduler.
    """

    # 1. Limpa caches antigos
    await db.execute("TRUNCATE cache_reposicao_resumo")

    # 2. Popula resumo por mes/loja
    await db.execute("""
        INSERT INTO cache_reposicao_resumo (
            mes, cd_loja, nome_loja,
            qtd_skus, qtd_skus_demanda,
            estoque_minimo_total, saldo_inicial_total, necessidade_total,
            entrada_periodo, entrada_atrasada, entrada_sem_lote, entrada_total,
            faltou, taxa_atendimento,
            skus_ok, skus_parcial, skus_zerados, skus_sem_necessidade
        )
        SELECT
            mes, cd_loja, nome_loja,
            COUNT(*),
            COUNT(*) FILTER (WHERE necessidade > 0),
            SUM(estoque_minimo),
            SUM(saldo_inicial),
            SUM(necessidade),
            SUM(entrada_periodo),
            SUM(entrada_atrasada),
            SUM(entrada_sem_lote),
            SUM(entrada_total),
            SUM(faltou),
            CASE WHEN SUM(necessidade) > 0
                 THEN ROUND(SUM(entrada_total) / SUM(necessidade) * 100, 1)
                 ELSE 100 END,
            COUNT(*) FILTER (WHERE status_reposicao = 'OK'),
            COUNT(*) FILTER (WHERE status_reposicao = 'PARCIAL'),
            COUNT(*) FILTER (WHERE status_reposicao IN ('ZERADO', 'SEM ENTRADA')),
            COUNT(*) FILTER (WHERE status_reposicao = 'SEM NECESSIDADE')
        FROM extrato_reposicao_loja_perm_analitico
        GROUP BY mes, cd_loja, nome_loja
    """)

    # 3. Identifica SKUs mortos
    await identificar_skus_mortos()

    # 4. Calcula gap acumulado
    await calcular_gap_acumulado()

    return {"status": "ok", "atualizado_em": datetime.now()}
```

---

## FRONTEND (Next.js + Tailwind + Tremor)

### Estrutura de Pastas

```
src/
├── app/
│   ├── layout.tsx              # Layout com sidebar rosa
│   ├── page.tsx                # Dashboard principal
│   ├── lojas/
│   │   ├── page.tsx            # Lista de lojas
│   │   └── [id]/page.tsx       # Detalhe da loja
│   ├── meses/
│   │   ├── page.tsx            # Analise por mes
│   │   └── [mes]/page.tsx      # Detalhe do mes
│   ├── referencias/
│   │   └── [ref]/page.tsx      # Historico da referencia
│   ├── alertas/
│   │   └── page.tsx            # SKUs criticos e mortos
│   └── configuracoes/
│       └── page.tsx            # Config de meses, cache, etc
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx         # Sidebar rosa LIEBE
│   │   ├── Header.tsx          # Header com logo e ultima atualizacao
│   │   └── PageContainer.tsx
│   │
│   ├── cards/
│   │   ├── MetricCard.tsx      # Card de metrica (necessidade, entrada, falta)
│   │   ├── AlertCard.tsx       # Card de alerta (vermelho/amarelo)
│   │   ├── LojaCard.tsx        # Card resumo de loja
│   │   └── StatusCard.tsx      # Card com status (OK, PARCIAL, ZERADO)
│   │
│   ├── charts/
│   │   ├── EvolucaoMensal.tsx  # Grafico de linha
│   │   ├── ComparacaoLojas.tsx # Grafico de barras
│   │   ├── PizzaStatus.tsx     # Distribuicao de status
│   │   └── HeatmapLojasMeses.tsx # Matriz loja x mes
│   │
│   ├── tables/
│   │   ├── TabelaResumo.tsx    # Tabela com totais
│   │   ├── TabelaSKUs.tsx      # Tabela detalhada de SKUs
│   │   └── TabelaEntradas.tsx  # Entradas por tipo
│   │
│   └── filters/
│       ├── FiltroMes.tsx
│       ├── FiltroLoja.tsx
│       ├── FiltroCurva.tsx
│       └── FiltroStatus.tsx
│
├── hooks/
│   ├── useReposicao.ts         # Hook principal de dados
│   ├── useCache.ts             # Hook de gerenciamento de cache
│   └── useConfig.ts            # Hook de configuracoes
│
├── services/
│   ├── api.ts                  # Cliente axios/fetch
│   └── reposicaoService.ts     # Chamadas de API
│
└── types/
    └── reposicao.ts            # Tipos TypeScript
```

### Design System (Cores LIEBE)

```typescript
// tailwind.config.ts
const config = {
  theme: {
    extend: {
      colors: {
        liebe: {
          pink: {
            50: '#fdf2f8',
            100: '#fce7f3',
            200: '#fbcfe8',
            300: '#f9a8d4',
            400: '#f472b6',
            500: '#ec4899',  // Principal
            600: '#db2777',
            700: '#be185d',
            800: '#9d174d',
            900: '#831843',
          },
          rose: {
            light: '#ffe4e6',
            DEFAULT: '#f43f5e',
            dark: '#be123c',
          }
        },
        status: {
          ok: '#22c55e',       // Verde
          parcial: '#eab308',  // Amarelo
          zerado: '#ef4444',   // Vermelho
          semNecessidade: '#94a3b8', // Cinza
        }
      }
    }
  }
}
```

### Componentes Principais

#### Sidebar Rosa

```tsx
// components/layout/Sidebar.tsx
export function Sidebar() {
  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', href: '/' },
    { icon: Store, label: 'Lojas', href: '/lojas' },
    { icon: Calendar, label: 'Meses', href: '/meses' },
    { icon: Package, label: 'Referencias', href: '/referencias' },
    { icon: AlertTriangle, label: 'Alertas', href: '/alertas' },
    { icon: TrendingDown, label: 'SKUs Mortos', href: '/skus-mortos' },
    { divider: true },
    { icon: Settings, label: 'Configuracoes', href: '/configuracoes' },
    { icon: RefreshCw, label: 'Atualizar Cache', href: '/cache' },
  ];

  return (
    <aside className="w-64 bg-gradient-to-b from-liebe-pink-600 to-liebe-pink-800 min-h-screen">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-white">LIEBE</h1>
        <p className="text-liebe-pink-200 text-sm">Reposicao</p>
      </div>

      <nav className="mt-6">
        {menuItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center px-6 py-3 text-liebe-pink-100
                       hover:bg-liebe-pink-700 hover:text-white transition-colors"
          >
            <item.icon className="w-5 h-5 mr-3" />
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
```

#### Cards do Topo

```tsx
// components/cards/MetricCards.tsx
export function MetricCards({ data }: { data: ResumoGeral }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
      <Card className="bg-white border-l-4 border-l-liebe-pink-500">
        <Text className="text-gray-500">Necessidade Total</Text>
        <Metric className="text-liebe-pink-600">
          {formatNumber(data.necessidade)}
        </Metric>
        <Text className="text-xs text-gray-400">
          {data.skus_demanda} SKUs com demanda
        </Text>
      </Card>

      <Card className="bg-white border-l-4 border-l-blue-500">
        <Text className="text-gray-500">Entrada Periodo</Text>
        <Metric className="text-blue-600">
          {formatNumber(data.entrada_periodo)}
        </Metric>
        <Badge color="blue">{data.pct_periodo}% do total</Badge>
      </Card>

      <Card className="bg-white border-l-4 border-l-amber-500">
        <Text className="text-gray-500">Entrada Atrasada</Text>
        <Metric className="text-amber-600">
          {formatNumber(data.entrada_atrasada)}
        </Metric>
        <Badge color="amber">{data.pct_atrasada}% do total</Badge>
      </Card>

      <Card className="bg-white border-l-4 border-l-gray-400">
        <Text className="text-gray-500">Sem Lote</Text>
        <Metric className="text-gray-600">
          {formatNumber(data.entrada_sem_lote)}
        </Metric>
        <Badge color="gray">{data.pct_sem_lote}% do total</Badge>
      </Card>

      <Card className={`bg-white border-l-4 ${
        data.taxa_atendimento >= 100 ? 'border-l-green-500' :
        data.taxa_atendimento >= 70 ? 'border-l-amber-500' :
        'border-l-red-500'
      }`}>
        <Text className="text-gray-500">Taxa Atendimento</Text>
        <Metric className={
          data.taxa_atendimento >= 100 ? 'text-green-600' :
          data.taxa_atendimento >= 70 ? 'text-amber-600' :
          'text-red-600'
        }>
          {data.taxa_atendimento}%
        </Metric>
        <Text className="text-xs text-gray-400">
          Faltou: {formatNumber(data.faltou)}
        </Text>
      </Card>
    </div>
  );
}
```

---

## TELAS DO SISTEMA

### 1. Dashboard Principal

```
+------------------------------------------------------------------+
|  LIEBE          |  DASHBOARD - REPOSICAO                         |
|  Reposicao      |  Ultima atualizacao: 07/08/2026 10:30          |
|                 |                                                 |
|  [Dashboard]    |  +----------+ +----------+ +----------+ +-------|
|  Lojas          |  |NECESSID. | |ENTRADA   | |ATRASADA  | |FALTOU |
|  Meses          |  |  9.301   | | 9.939    | |  770     | | 7.954 |
|  Referencias    |  +----------+ +----------+ +----------+ +-------|
|  Alertas        |                                                 |
|  SKUs Mortos    |  [GRAFICO: Evolucao Mensal Jan-Ago 2026]       |
|  -----------    |  - Linha azul: Necessidade                      |
|  Configuracoes  |  - Linha verde: Entrada                         |
|  Atualizar      |  - Linha vermelha: Falta                        |
|                 |                                                 |
|                 |  +---------------------------------------------+|
|                 |  | RANKING LOJAS POR TAXA ATENDIMENTO         ||
|                 |  | 1. Iguatemi      - 85% [========  ]         ||
|                 |  | 2. Maraponga     - 78% [=======   ]         ||
|                 |  | 3. North         - 45% [====      ] ALERTA  ||
|                 |  +---------------------------------------------+|
+------------------------------------------------------------------+
```

### 2. Analise por Mes

```
+------------------------------------------------------------------+
|  ANALISE: JUNHO 2026                                             |
|                                                                  |
|  +-------+ +-------+ +-------+ +-------+ +-------+               |
|  |NECESS.| |PERIODO| |ATRASA.| |S/LOTE | |FALTOU |               |
|  |11.487 | | 8.524 | |  770  | |20.769 | | 5.482 |               |
|  +-------+ +-------+ +-------+ +-------+ +-------+               |
|                                                                  |
|  DETALHAMENTO POR LOJA                                           |
|  +----------------------------------------------------------+   |
|  | Loja          | Necess. | Entrada | Faltou | Status      |   |
|  |---------------|---------|---------|--------|-------------|   |
|  | Iguatemi      |   1.637 |   5.529 |    395 | OK 76%      |   |
|  | Maraponga     |   1.466 |   4.403 |    361 | OK 75%      |   |
|  | North         |     490 |     776 |    352 | PARCIAL 28% |   |
|  +----------------------------------------------------------+   |
|                                                                  |
|  ALERTAS DO MES                                                  |
|  [!] 45 SKUs curva A sem entrada                                 |
|  [!] 12 referencias zeraram em 3+ lojas                          |
+------------------------------------------------------------------+
```

### 3. Tela de SKUs Mortos (CRITICA)

```
+------------------------------------------------------------------+
|  SKUS MORTOS - Itens que pararam de ter necessidade              |
|                                                                  |
|  ATENCAO: Estes SKUs tinham venda historica mas zeraram o        |
|  estoque e pararam de aparecer como necessidade. Isso pode       |
|  indicar ruptura silenciosa!                                     |
|                                                                  |
|  Filtros: [Curva: A/AA] [Loja: Todas] [Meses sem estoque: 2+]   |
|                                                                  |
|  +----------------------------------------------------------+   |
|  | Referencia | Produto           | Loja      | Ultima | Meses|   |
|  |            |                   |           | Venda  | Sem  |   |
|  |------------|-------------------|-----------|--------|------|   |
|  | 703816     | SUTIA MICROFIBRA  | Iguatemi  | Mar/26 |   4  |   |
|  | 703816     | SUTIA MICROFIBRA  | Maraponga | Abr/26 |   3  |   |
|  | 285901     | CALCINHA RENDA    | North     | Fev/26 |   5  |   |
|  +----------------------------------------------------------+   |
|                                                                  |
|  ACOES RECOMENDADAS:                                             |
|  [ ] Exportar lista para producao                                |
|  [ ] Gerar pedido emergencial                                    |
+------------------------------------------------------------------+
```

### 4. Configuracoes

```
+------------------------------------------------------------------+
|  CONFIGURACOES                                                   |
|                                                                  |
|  CALCULO DA MEDIA MENSAL                                         |
|  +----------------------------------------------------------+   |
|  | Meses para calculo da media:                              |   |
|  | [x] 3 meses anteriores (padrao)                           |   |
|  | [ ] 6 meses anteriores                                    |   |
|  | [ ] Customizado: ___                                      |   |
|  +----------------------------------------------------------+   |
|                                                                  |
|  MULTIPLICADOR DO ESTOQUE MINIMO                                 |
|  +----------------------------------------------------------+   |
|  | Estoque minimo = Media mensal x [ 1.5 ]                   |   |
|  +----------------------------------------------------------+   |
|                                                                  |
|  GERENCIAMENTO DE CACHE                                          |
|  +----------------------------------------------------------+   |
|  | Ultima atualizacao: 07/08/2026 10:30                      |   |
|  | Registros no cache: 114.268                               |   |
|  |                                                           |   |
|  | [Atualizar Tudo]  [Atualizar Apenas Agosto]              |   |
|  |                                                           |   |
|  | Tempo estimado: ~45 minutos para atualizacao completa    |   |
|  +----------------------------------------------------------+   |
+------------------------------------------------------------------+
```

---

## QUERIES OTIMIZADAS

### Query: Evolucao Mensal (para grafico)

```sql
SELECT
    mes,
    SUM(necessidade) AS necessidade,
    SUM(entrada_total) AS entrada,
    SUM(faltou) AS faltou,
    ROUND(SUM(entrada_total) / NULLIF(SUM(necessidade), 0) * 100, 1) AS taxa_atendimento
FROM extrato_reposicao_loja_perm_analitico
WHERE mes BETWEEN '2026-01' AND '2026-08'
GROUP BY mes
ORDER BY mes;
```

### Query: SKUs Mortos (Identificacao)

```sql
-- SKUs que tinham venda e sumiram
WITH vendas_historicas AS (
    SELECT
        cd_loja,
        cd_produto,
        referencia,
        MAX(mes) FILTER (WHERE vendas_3m > 0) AS ultimo_mes_venda,
        MAX(mes) FILTER (WHERE saldo_inicial > 0) AS ultimo_mes_estoque,
        MAX(curva_completa) AS curva
    FROM extrato_reposicao_loja_perm_analitico
    GROUP BY cd_loja, cd_produto, referencia
),
analise AS (
    SELECT
        *,
        -- Calcula meses sem estoque
        EXTRACT(MONTH FROM AGE(
            TO_DATE('2026-08-01', 'YYYY-MM-DD'),
            TO_DATE(ultimo_mes_estoque || '-01', 'YYYY-MM-DD')
        )) AS meses_sem_estoque
    FROM vendas_historicas
    WHERE ultimo_mes_venda IS NOT NULL
      AND ultimo_mes_estoque < '2026-06'  -- Zerou ha 2+ meses
)
SELECT * FROM analise
WHERE curva IN ('CURVA A', 'CURVA AA')  -- Foco nas curvas importantes
ORDER BY meses_sem_estoque DESC;
```

### Query: Gap Acumulado por Loja

```sql
-- Mostra o debito acumulado de cada loja
SELECT
    cd_loja,
    nome_loja,
    SUM(CASE WHEN mes = '2026-01' THEN faltou ELSE 0 END) AS jan,
    SUM(CASE WHEN mes = '2026-02' THEN faltou ELSE 0 END) AS fev,
    SUM(CASE WHEN mes = '2026-03' THEN faltou ELSE 0 END) AS mar,
    SUM(CASE WHEN mes = '2026-04' THEN faltou ELSE 0 END) AS abr,
    SUM(CASE WHEN mes = '2026-05' THEN faltou ELSE 0 END) AS mai,
    SUM(CASE WHEN mes = '2026-06' THEN faltou ELSE 0 END) AS jun,
    SUM(CASE WHEN mes = '2026-07' THEN faltou ELSE 0 END) AS jul,
    SUM(CASE WHEN mes = '2026-08' THEN faltou ELSE 0 END) AS ago,
    SUM(faltou) AS gap_total_ano
FROM extrato_reposicao_loja_perm_analitico
GROUP BY cd_loja, nome_loja
ORDER BY gap_total_ano DESC;
```

---

## ALERTAS AUTOMATICOS

### Tipos de Alerta

```typescript
enum TipoAlerta {
  RUPTURA_CURVA_A = 'ruptura_curva_a',      // SKU curva A zerou
  LOJA_CRITICA = 'loja_critica',            // Loja com < 50% atendimento
  REFERENCIA_MORRENDO = 'ref_morrendo',     // Ref zerou em 3+ lojas
  LOTE_ATRASADO = 'lote_atrasado',          // Muito produto de lote antigo
  MES_SEM_ENTRADA = 'mes_sem_entrada',      // Loja nao recebeu nada no mes
}

interface Alerta {
  tipo: TipoAlerta;
  severidade: 'critico' | 'alto' | 'medio' | 'baixo';
  mensagem: string;
  dados: Record<string, any>;
  criadoEm: Date;
}
```

### Regras de Alerta

```python
def gerar_alertas():
    alertas = []

    # 1. SKUs Curva A zerados
    skus_a_zerados = db.query("""
        SELECT cd_loja, cd_produto, referencia, nome_loja
        FROM extrato_reposicao_loja_perm_analitico
        WHERE mes = '2026-08'
          AND curva_completa IN ('CURVA A', 'CURVA AA')
          AND saldo_inicial = 0
          AND necessidade = 0
    """)

    for sku in skus_a_zerados:
        alertas.append({
            'tipo': 'RUPTURA_CURVA_A',
            'severidade': 'critico',
            'mensagem': f"SKU Curva A zerado: {sku.referencia} na {sku.nome_loja}",
            'dados': sku
        })

    # 2. Lojas com atendimento < 50%
    lojas_criticas = db.query("""
        SELECT cd_loja, nome_loja,
               SUM(necessidade) AS necessidade,
               SUM(entrada_total) AS entrada,
               ROUND(SUM(entrada_total) / NULLIF(SUM(necessidade), 0) * 100, 1) AS taxa
        FROM extrato_reposicao_loja_perm_analitico
        WHERE mes = '2026-08'
        GROUP BY cd_loja, nome_loja
        HAVING SUM(entrada_total) / NULLIF(SUM(necessidade), 0) < 0.5
    """)

    for loja in lojas_criticas:
        alertas.append({
            'tipo': 'LOJA_CRITICA',
            'severidade': 'alto',
            'mensagem': f"{loja.nome_loja} com apenas {loja.taxa}% de atendimento",
            'dados': loja
        })

    return alertas
```

---

## PROXIMO PASSO: IMPLEMENTACAO

### Fase 1 - Backend (1 semana)
1. Estruturar projeto FastAPI
2. Criar endpoints de cache
3. Implementar queries otimizadas
4. Criar sistema de alertas

### Fase 2 - Frontend (1 semana)
1. Setup Next.js com Tailwind
2. Criar layout com sidebar rosa
3. Implementar cards e graficos
4. Conectar com API

### Fase 3 - Refinamento
1. Testes de carga
2. Otimizacao de queries
3. UX feedback
4. Deploy

---

## COMANDOS PARA INICIAR

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn psycopg2-binary pandas

# Frontend
cd frontend
npx create-next-app@latest . --typescript --tailwind
npm install @tremor/react recharts lucide-react
```

---

**Este documento serve como guia completo para desenvolvimento do sistema de inteligencia de reposicao LIEBE.**
