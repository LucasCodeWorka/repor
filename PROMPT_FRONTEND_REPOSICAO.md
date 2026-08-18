# PROMPT PARA DESENVOLVIMENTO DO FRONTEND - SISTEMA REPOSICAO LIEBE

## CONTEXTO

Desenvolver um dashboard de analise de reposicao de lojas para a marca LIEBE (lingerie).
O backend FastAPI ja esta pronto em `backend/main.py` rodando na porta 8001.

## TECNOLOGIAS

- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS
- Tremor (biblioteca de componentes para dashboards)
- Recharts (graficos)
- Lucide React (icones)

## DESIGN SYSTEM LIEBE

### Cores Principais
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
            500: '#ec4899',
            600: '#db2777',
            700: '#be185d',
            800: '#9d174d',
            900: '#831843',
          }
        },
        status: {
          ok: '#22c55e',
          parcial: '#eab308',
          zerado: '#ef4444',
          semNecessidade: '#94a3b8',
        }
      }
    }
  }
}
```

### Sidebar Rosa (Referencia Visual)
A sidebar deve ser um gradiente rosa escuro (pink-700 para pink-900) com:
- Logo "LIEBE" no topo em branco
- Subtitulo "Reposicao" em rosa claro
- Menu com icones brancos/rosa claro
- Hover em pink-600
- Item ativo com fundo pink-600

## ESTRUTURA DE PASTAS

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Layout principal com sidebar
│   │   ├── page.tsx             # Dashboard principal
│   │   ├── globals.css          # Estilos globais
│   │   ├── lojas/
│   │   │   ├── page.tsx         # Lista de lojas
│   │   │   └── [id]/page.tsx    # Detalhe da loja
│   │   ├── meses/
│   │   │   ├── page.tsx         # Analise por mes
│   │   │   └── [mes]/page.tsx   # Detalhe do mes
│   │   ├── alertas/
│   │   │   └── page.tsx         # SKUs criticos
│   │   └── configuracoes/
│   │       └── page.tsx         # Config de cache
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── PageContainer.tsx
│   │   ├── cards/
│   │   │   ├── MetricCard.tsx
│   │   │   └── StatusBadge.tsx
│   │   ├── charts/
│   │   │   ├── EvolucaoMensal.tsx
│   │   │   └── ComparacaoLojas.tsx
│   │   └── tables/
│   │       ├── TabelaLojas.tsx
│   │       └── TabelaSKUs.tsx
│   │
│   ├── hooks/
│   │   └── useApi.ts
│   │
│   ├── services/
│   │   └── api.ts
│   │
│   └── types/
│       └── reposicao.ts
│
├── tailwind.config.ts
├── next.config.js
└── package.json
```

## ENDPOINTS DA API (Backend rodando em http://localhost:8001)

### Dashboard
```
GET /api/dashboard/resumo-geral?year=2026&month=2026-08
Retorna:
{
  "necessidade": 72112.0,
  "entrada_periodo": 54619.0,
  "entrada_atrasada": 27968.0,
  "entrada_sem_lote": 95250.0,
  "entrada_total": 177837.0,
  "faltou": 36663.0,
  "skus_demanda": 35855,
  "skus_ok": 14645,
  "taxa_atendimento": 246.6,
  "pct_periodo": 30.7,
  "pct_atrasada": 15.7,
  "pct_sem_lote": 53.6
}

GET /api/dashboard/evolucao-mensal?year=2026
Retorna: Array de objetos com mes, necessidade, entrada_total, faltou, taxa_atendimento

GET /api/dashboard/lojas-ranking?year=2026&month=2026-08
Retorna: Array ordenado por taxa_atendimento com cd_loja, nome_loja, necessidade, entrada_total, faltou, taxa_atendimento

GET /api/dashboard/alertas?month=2026-08
Retorna: Array de alertas com tipo, severidade, mensagem, dados
```

### Analise
```
GET /api/analise/por-mes/{mes}
GET /api/analise/por-loja/{cd_loja}?year=2026
GET /api/analise/entradas/{mes}
```

### Cache
```
GET /api/cache/status
POST /api/cache/atualizar
GET /api/config/ultima-atualizacao
```

## COMPONENTES DETALHADOS

### 1. Sidebar.tsx

```tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Store,
  Calendar,
  AlertTriangle,
  Settings,
  RefreshCw,
  TrendingDown,
} from 'lucide-react';

const menuItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/' },
  { icon: Store, label: 'Lojas', href: '/lojas' },
  { icon: Calendar, label: 'Meses', href: '/meses' },
  { icon: AlertTriangle, label: 'Alertas', href: '/alertas' },
  { icon: TrendingDown, label: 'SKUs Mortos', href: '/skus-mortos' },
  { divider: true },
  { icon: Settings, label: 'Configuracoes', href: '/configuracoes' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 min-h-screen bg-gradient-to-b from-pink-700 to-pink-900 text-white flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-pink-600">
        <h1 className="text-2xl font-bold tracking-wider">LIEBE</h1>
        <p className="text-pink-300 text-sm mt-1">Reposicao</p>
      </div>

      {/* Menu */}
      <nav className="flex-1 py-4">
        {menuItems.map((item, idx) => {
          if ('divider' in item) {
            return <div key={idx} className="my-4 border-t border-pink-600" />;
          }

          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-3 px-6 py-3 text-sm font-medium
                transition-colors duration-200
                ${isActive
                  ? 'bg-pink-600 text-white border-r-4 border-white'
                  : 'text-pink-200 hover:bg-pink-600 hover:text-white'
                }
              `}
            >
              <Icon className="w-5 h-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-pink-600 text-xs text-pink-300">
        <p>Ultima atualizacao:</p>
        <p className="text-white">07/08/2026 10:30</p>
      </div>
    </aside>
  );
}
```

### 2. MetricCard.tsx

```tsx
interface MetricCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  color: 'pink' | 'blue' | 'amber' | 'gray' | 'green' | 'red';
  percentage?: number;
}

const colorClasses = {
  pink: 'border-l-pink-500 text-pink-600',
  blue: 'border-l-blue-500 text-blue-600',
  amber: 'border-l-amber-500 text-amber-600',
  gray: 'border-l-gray-400 text-gray-600',
  green: 'border-l-green-500 text-green-600',
  red: 'border-l-red-500 text-red-600',
};

export function MetricCard({ title, value, subtitle, color, percentage }: MetricCardProps) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border-l-4 p-4 ${colorClasses[color]}`}>
      <p className="text-gray-500 text-sm font-medium">{title}</p>
      <p className={`text-2xl font-bold mt-1 ${colorClasses[color].split(' ')[1]}`}>
        {typeof value === 'number' ? value.toLocaleString('pt-BR') : value}
      </p>
      {subtitle && (
        <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
      )}
      {percentage !== undefined && (
        <span className={`
          inline-block mt-2 px-2 py-1 rounded text-xs font-medium
          ${color === 'blue' ? 'bg-blue-100 text-blue-700' : ''}
          ${color === 'amber' ? 'bg-amber-100 text-amber-700' : ''}
          ${color === 'gray' ? 'bg-gray-100 text-gray-700' : ''}
        `}>
          {percentage}% do total
        </span>
      )}
    </div>
  );
}
```

### 3. Dashboard Principal (page.tsx)

```tsx
'use client';

import { useEffect, useState } from 'react';
import { MetricCard } from '@/components/cards/MetricCard';
import { EvolucaoMensal } from '@/components/charts/EvolucaoMensal';
import { TabelaLojas } from '@/components/tables/TabelaLojas';
import { api } from '@/services/api';

export default function DashboardPage() {
  const [resumo, setResumo] = useState<any>(null);
  const [evolucao, setEvolucao] = useState<any[]>([]);
  const [lojas, setLojas] = useState<any[]>([]);
  const [mesSelecionado, setMesSelecionado] = useState('2026-08');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [resumoData, evolucaoData, lojasData] = await Promise.all([
          api.getResumoGeral(2026, mesSelecionado),
          api.getEvolucaoMensal(2026),
          api.getLojasRanking(2026, mesSelecionado),
        ]);
        setResumo(resumoData);
        setEvolucao(evolucaoData);
        setLojas(lojasData);
      } catch (error) {
        console.error('Erro ao carregar dados:', error);
      }
      setLoading(false);
    }
    loadData();
  }, [mesSelecionado]);

  if (loading) {
    return <div className="p-8">Carregando...</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard de Reposicao</h1>
          <p className="text-gray-500">Analise de reposicao das lojas LIEBE</p>
        </div>
        <select
          value={mesSelecionado}
          onChange={(e) => setMesSelecionado(e.target.value)}
          className="border rounded-lg px-4 py-2 text-sm"
        >
          <option value="2026-08">Agosto 2026</option>
          <option value="2026-07">Julho 2026</option>
          <option value="2026-06">Junho 2026</option>
          <option value="2026-05">Maio 2026</option>
          <option value="2026-04">Abril 2026</option>
          <option value="2026-03">Marco 2026</option>
          <option value="2026-02">Fevereiro 2026</option>
          <option value="2026-01">Janeiro 2026</option>
        </select>
      </div>

      {/* Cards de Metricas - 5 colunas como na imagem */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Necessidade Total"
          value={resumo?.necessidade || 0}
          subtitle={`${resumo?.skus_demanda || 0} SKUs com demanda`}
          color="pink"
        />
        <MetricCard
          title="Entrada Periodo"
          value={resumo?.entrada_periodo || 0}
          percentage={resumo?.pct_periodo}
          color="blue"
        />
        <MetricCard
          title="Entrada Atrasada"
          value={resumo?.entrada_atrasada || 0}
          percentage={resumo?.pct_atrasada}
          color="amber"
        />
        <MetricCard
          title="Sem Lote"
          value={resumo?.entrada_sem_lote || 0}
          percentage={resumo?.pct_sem_lote}
          color="gray"
        />
        <MetricCard
          title="Faltou"
          value={resumo?.faltou || 0}
          subtitle={`Taxa: ${resumo?.taxa_atendimento || 0}%`}
          color={resumo?.taxa_atendimento >= 100 ? 'green' : 'red'}
        />
      </div>

      {/* Grafico de Evolucao Mensal */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Evolucao Mensal - 2026
        </h2>
        <EvolucaoMensal data={evolucao} />
      </div>

      {/* Tabela de Lojas */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Ranking de Lojas - {mesSelecionado}
        </h2>
        <TabelaLojas data={lojas} />
      </div>
    </div>
  );
}
```

### 4. EvolucaoMensal.tsx (Grafico)

```tsx
'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface EvolucaoMensalProps {
  data: Array<{
    mes: string;
    necessidade: number;
    entrada_total: number;
    faltou: number;
  }>;
}

export function EvolucaoMensal({ data }: EvolucaoMensalProps) {
  const formattedData = data.map((item) => ({
    ...item,
    mesLabel: item.mes.substring(5), // "01", "02", etc
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={formattedData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="mesLabel"
          tick={{ fontSize: 12 }}
          tickFormatter={(value) => {
            const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
            return meses[parseInt(value) - 1] || value;
          }}
        />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip
          formatter={(value: number) => value.toLocaleString('pt-BR')}
          labelFormatter={(label) => `Mes ${label}`}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="necessidade"
          stroke="#ec4899"
          strokeWidth={2}
          name="Necessidade"
          dot={{ fill: '#ec4899' }}
        />
        <Line
          type="monotone"
          dataKey="entrada_total"
          stroke="#22c55e"
          strokeWidth={2}
          name="Entrada Total"
          dot={{ fill: '#22c55e' }}
        />
        <Line
          type="monotone"
          dataKey="faltou"
          stroke="#ef4444"
          strokeWidth={2}
          name="Faltou"
          dot={{ fill: '#ef4444' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### 5. TabelaLojas.tsx

```tsx
interface TabelaLojasProps {
  data: Array<{
    cd_loja: number;
    nome_loja: string;
    necessidade: number;
    entrada_total: number;
    faltou: number;
    taxa_atendimento: number;
    skus_demanda: number;
    skus_zerados: number;
  }>;
}

export function TabelaLojas({ data }: TabelaLojasProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-3 px-4 font-medium text-gray-600">Loja</th>
            <th className="text-right py-3 px-4 font-medium text-gray-600">Necessidade</th>
            <th className="text-right py-3 px-4 font-medium text-gray-600">Entrada</th>
            <th className="text-right py-3 px-4 font-medium text-gray-600">Faltou</th>
            <th className="text-right py-3 px-4 font-medium text-gray-600">Taxa</th>
            <th className="text-center py-3 px-4 font-medium text-gray-600">Status</th>
          </tr>
        </thead>
        <tbody>
          {data.map((loja) => (
            <tr key={loja.cd_loja} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-3 px-4 font-medium text-gray-800">
                {loja.nome_loja}
              </td>
              <td className="py-3 px-4 text-right text-gray-600">
                {loja.necessidade.toLocaleString('pt-BR')}
              </td>
              <td className="py-3 px-4 text-right text-gray-600">
                {loja.entrada_total.toLocaleString('pt-BR')}
              </td>
              <td className="py-3 px-4 text-right text-red-600 font-medium">
                {loja.faltou.toLocaleString('pt-BR')}
              </td>
              <td className="py-3 px-4 text-right font-medium">
                <span className={`
                  ${loja.taxa_atendimento >= 100 ? 'text-green-600' : ''}
                  ${loja.taxa_atendimento >= 50 && loja.taxa_atendimento < 100 ? 'text-amber-600' : ''}
                  ${loja.taxa_atendimento < 50 ? 'text-red-600' : ''}
                `}>
                  {loja.taxa_atendimento}%
                </span>
              </td>
              <td className="py-3 px-4 text-center">
                <span className={`
                  inline-block px-2 py-1 rounded-full text-xs font-medium
                  ${loja.taxa_atendimento >= 100 ? 'bg-green-100 text-green-700' : ''}
                  ${loja.taxa_atendimento >= 50 && loja.taxa_atendimento < 100 ? 'bg-amber-100 text-amber-700' : ''}
                  ${loja.taxa_atendimento < 50 ? 'bg-red-100 text-red-700' : ''}
                `}>
                  {loja.taxa_atendimento >= 100 ? 'OK' : loja.taxa_atendimento >= 50 ? 'PARCIAL' : 'CRITICO'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### 6. api.ts (Service)

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export const api = {
  async getResumoGeral(year: number, month?: string) {
    const params = new URLSearchParams({ year: year.toString() });
    if (month) params.append('month', month);
    const res = await fetch(`${API_URL}/api/dashboard/resumo-geral?${params}`);
    if (!res.ok) throw new Error('Erro ao buscar resumo');
    return res.json();
  },

  async getEvolucaoMensal(year: number) {
    const res = await fetch(`${API_URL}/api/dashboard/evolucao-mensal?year=${year}`);
    if (!res.ok) throw new Error('Erro ao buscar evolucao');
    return res.json();
  },

  async getLojasRanking(year: number, month?: string) {
    const params = new URLSearchParams({ year: year.toString() });
    if (month) params.append('month', month);
    const res = await fetch(`${API_URL}/api/dashboard/lojas-ranking?${params}`);
    if (!res.ok) throw new Error('Erro ao buscar lojas');
    return res.json();
  },

  async getAlertas(month?: string) {
    const params = month ? `?month=${month}` : '';
    const res = await fetch(`${API_URL}/api/dashboard/alertas${params}`);
    if (!res.ok) throw new Error('Erro ao buscar alertas');
    return res.json();
  },

  async getAnalisePorMes(mes: string) {
    const res = await fetch(`${API_URL}/api/analise/por-mes/${mes}`);
    if (!res.ok) throw new Error('Erro ao buscar analise do mes');
    return res.json();
  },

  async getAnalisePorLoja(cdLoja: number, year: number) {
    const res = await fetch(`${API_URL}/api/analise/por-loja/${cdLoja}?year=${year}`);
    if (!res.ok) throw new Error('Erro ao buscar analise da loja');
    return res.json();
  },

  async getCacheStatus() {
    const res = await fetch(`${API_URL}/api/cache/status`);
    if (!res.ok) throw new Error('Erro ao buscar status do cache');
    return res.json();
  },

  async atualizarCache() {
    const res = await fetch(`${API_URL}/api/cache/atualizar`, { method: 'POST' });
    if (!res.ok) throw new Error('Erro ao atualizar cache');
    return res.json();
  },
};
```

### 7. Layout Principal (layout.tsx)

```tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Sidebar } from '@/components/layout/Sidebar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'LIEBE Reposicao',
  description: 'Sistema de analise de reposicao de lojas',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className={`${inter.className} bg-gray-50`}>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
```

## INSTRUCOES DE SETUP

```bash
# Na pasta geo2, criar o frontend
cd frontend

# Instalar dependencias
npm install recharts lucide-react

# Configurar variavel de ambiente
echo "NEXT_PUBLIC_API_URL=http://localhost:8001" > .env.local

# Rodar
npm run dev
```

## PAGINAS ADICIONAIS A CRIAR

### /lojas/page.tsx
- Lista todas as lojas com cards
- Filtro por mes
- Link para detalhe de cada loja

### /lojas/[id]/page.tsx
- Evolucao da loja ao longo dos meses
- Tabela de SKUs criticos
- Grafico de pizza de status

### /meses/page.tsx
- Cards para cada mes do ano
- Comparativo visual

### /meses/[mes]/page.tsx
- Detalhe completo do mes
- Todas as lojas lado a lado
- Entradas por tipo (periodo, atrasada, sem lote)

### /alertas/page.tsx
- Lista de alertas agrupados por severidade
- Filtros por tipo
- SKUs curva A zerados
- Referencias morrendo

### /configuracoes/page.tsx
- Status do cache
- Botao de atualizar cache
- Config de meses para media

## COMPORTAMENTOS ESPERADOS

1. **Loading States**: Mostrar skeleton/spinner enquanto carrega
2. **Erro de API**: Mostrar mensagem amigavel
3. **Filtros**: Manter estado ao navegar
4. **Responsivo**: Funcionar em mobile (sidebar collapse)
5. **Cores dinamicas**: Status OK/PARCIAL/CRITICO com cores corretas

## EXEMPLO DE RETORNO DA API PARA TESTES

```json
// /api/dashboard/resumo-geral?year=2026&month=2026-08
{
  "necessidade": 9301,
  "entrada_periodo": 0,
  "entrada_atrasada": 1589,
  "entrada_sem_lote": 8350,
  "entrada_total": 9939,
  "faltou": 7954,
  "skus_demanda": 4194,
  "skus_ok": 491,
  "skus_parcial": 66,
  "skus_zerados": 3637,
  "taxa_atendimento": 106.9,
  "pct_periodo": 0.0,
  "pct_atrasada": 16.0,
  "pct_sem_lote": 84.0
}
```

## CHECKLIST FINAL

- [ ] Sidebar rosa com gradiente
- [ ] 5 cards de metricas no topo
- [ ] Grafico de linha de evolucao mensal
- [ ] Tabela de lojas com status colorido
- [ ] Filtro de mes funcionando
- [ ] Pagina de lojas
- [ ] Pagina de alertas
- [ ] Pagina de configuracoes com cache
- [ ] Loading states
- [ ] Tratamento de erros
- [ ] Responsivo

---

**IMPORTANTE**: O backend ja esta rodando em http://localhost:8001. Testar os endpoints antes de integrar.
