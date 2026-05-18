import { useEffect, useMemo, useState } from 'react';
import {
  Calendar,
  Clock,
  CheckCircle2,
  ListTodo,
  TrendingUp,
  Layers,
  BookOpen,
  BarChart3,
  PieChart,
  ArrowRight,
} from 'lucide-react';
import { useBoardStore } from '../../store/boardStore';
import { useTaskStore } from '../../store/taskStore';
import { useUIStore } from '../../store/uiStore';
import { cn } from '../../utils/cn';
import { formatDateShort, daysUntil } from '../../utils/date';
import { Spinner } from '../ui/Spinner';
import { fetchDashboard } from '../../api/other';
import type { DashboardStats } from '../../types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RePieChart,
  Pie,
  Cell,
} from 'recharts';

const COLORS = ['#4A90D9', '#6C5CE7', '#00B894', '#FDCB6E', '#E17055', '#E84393', '#00CEC9', '#636E72'];

export function DashboardView() {
  const { boards, loadBoards } = useBoardStore();
  const { vigentActivities, loadVigent } = useTaskStore();
  const { openTaskModal } = useUIStore();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const today = new Date().toISOString().split('T')[0];

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [s] = await Promise.all([
          fetchDashboard({ due_date_after: today }).catch(() => null),
          loadBoards(),
          loadVigent({ due_date_after: today }),
        ]);
        setStats(s);
      } catch {
        // silent
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const upcomingTasks = useMemo(() => {
    return vigentActivities
      .filter((a) => {
        const d = daysUntil(a.due_date);
        return d !== null && d >= 0 && d <= 7;
      })
      .sort((a, b) => (a.due_date || '').localeCompare(b.due_date || ''));
  }, [vigentActivities]);

  // Weekly chart: group upcoming 7 days
  const weeklyData = useMemo(() => {
    const dayNames = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
    const counts = Array(7).fill(0);
    const now = new Date();
    for (let i = 0; i < 7; i++) {
      const d = new Date(now);
      d.setDate(d.getDate() + i);
      const ds = d.toISOString().split('T')[0];
      counts[i] = vigentActivities.filter((a) => a.due_date && a.due_date.startsWith(ds)).length;
    }
    return dayNames.map((day, i) => ({ day, tasks: counts[i] }));
  }, [vigentActivities]);

  // Discipline distribution
  const disciplineData = useMemo(() => {
    const map = new Map<string, number>();
    vigentActivities.forEach((a) => {
      const d = a.discipline || 'Sem disciplina';
      map.set(d, (map.get(d) || 0) + 1);
    });
    const sorted = [...map.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
    return sorted.map(([name, value], i) => ({
      name: name.length > 14 ? name.slice(0, 12) + '...' : name,
      fullName: name,
      value,
      color: COLORS[i % COLORS.length],
    }));
  }, [vigentActivities]);

  // Status breakdown
  const statusData = useMemo(() => {
    const pending = vigentActivities.filter((a) => a.status === 'pending').length;
    const inProgress = vigentActivities.filter((a) => a.status === 'in_progress').length;
    const completed = vigentActivities.filter((a) => a.status === 'completed').length;
    const overdue = vigentActivities.filter((a) => a.status === 'overdue').length;
    return [
      { name: 'Pendentes', value: pending, color: '#F59E0B' },
      { name: 'Em Andamento', value: inProgress, color: '#3B82F6' },
      { name: 'Concluídas', value: completed, color: '#10B981' },
      { name: 'Atrasadas', value: overdue, color: '#EF4444' },
    ].filter((d) => d.value > 0);
  }, [vigentActivities]);

  if (loading) return <Spinner size="lg" />;

  const statCards = [
    { label: 'A Fazer', value: stats?.pending ?? 0, icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50' },
    { label: 'Em Andamento', value: stats?.in_progress ?? 0, icon: TrendingUp, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Concluídas', value: stats?.completed ?? 0, icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Vencem Esta Semana', value: stats?.due_this_week ?? 0, icon: Calendar, color: 'text-orange-500', bg: 'bg-orange-50' },
  ];

  return (
    <div className="p-4 lg:p-6 space-y-6">
      {/* Stats cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-sm transition-shadow">
            <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center mb-3', card.bg)}>
              <card.icon size={20} className={card.color} />
            </div>
            <p className="text-xs text-gray-500">{card.label}</p>
            <p className="text-xl font-bold text-gray-900 mt-0.5">{card.value}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-1 flex items-center gap-2">
            <BarChart3 size={16} className="text-primary" />
            Atividades por Dia
          </h3>
          <p className="text-xs text-gray-400 mb-4">Próximos 7 dias</p>
          {weeklyData.every((d) => d.tasks === 0) ? (
            <div className="h-48 flex items-center justify-center text-sm text-gray-400">
              Nenhuma atividade nos próximos 7 dias
            </div>
          ) : (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weeklyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                    cursor={{ fill: '#f3f4f6' }}
                  />
                  <Bar dataKey="tasks" radius={[4, 4, 0, 0]} fill="#4A90D9" maxBarSize={32} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-1 flex items-center gap-2">
            <PieChart size={16} className="text-primary" />
            Distribuição por Disciplina
          </h3>
          <p className="text-xs text-gray-400 mb-4">{vigentActivities.length} atividades futuras</p>
          {disciplineData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-sm text-gray-400">
              Nenhuma atividade futura
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <div className="h-40 w-40 shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <RePieChart>
                    <Pie
                      data={disciplineData}
                      innerRadius={35}
                      outerRadius={60}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {disciplineData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(_val: any, _name: any, props: any) => [props.payload.fullName]}
                      contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                    />
                  </RePieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2 flex-1 max-h-40 overflow-y-auto">
                {disciplineData.map((item) => (
                  <div key={item.name} className="flex items-center gap-2 text-xs">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                    <span className="text-gray-600 truncate flex-1" title={item.fullName}>{item.fullName}</span>
                    <span className="font-medium text-gray-900">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Upcoming & Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Calendar size={18} className="text-orange-500" />
            Vencimento Próximo
            {upcomingTasks.length > 0 && (
              <span className="text-xs font-normal text-gray-400 ml-1">(7 dias)</span>
            )}
          </h3>
          {upcomingTasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Calendar size={32} className="text-gray-300 mb-2" />
              <p className="text-sm text-gray-400">Nenhuma atividade próxima do vencimento</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {upcomingTasks.slice(0, 10).map((t) => (
                <div
                  key={t.id}
                  onClick={() => openTaskModal(t.id, t.board_id)}
                  className="flex items-center justify-between p-3 bg-orange-50 rounded-lg cursor-pointer hover:bg-orange-100 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">{t.title}</p>
                    {t.discipline && <p className="text-xs text-gray-500 truncate">{t.discipline}</p>}
                  </div>
                  <span className="text-xs text-orange-600 font-medium shrink-0 ml-2">
                    {formatDateShort(t.due_date)}
                  </span>
                </div>
              ))}
              {upcomingTasks.length > 10 && (
                <a
                  href="/quadro"
                  className="flex items-center justify-center gap-1 text-xs text-primary font-medium pt-2 hover:underline"
                >
                  Ver todas no Quadro <ArrowRight size={12} />
                </a>
              )}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Layers size={18} className="text-primary" />
            Status das Atividades
          </h3>
          {statusData.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <ListTodo size={32} className="text-gray-300 mb-2" />
              <p className="text-sm text-gray-400">Nenhuma atividade futura</p>
            </div>
          ) : (
            <div className="space-y-3">
              {statusData.map((s) => (
                <div key={s.name} className="flex items-center gap-3">
                  <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: s.color }} />
                  <span className="text-sm text-gray-700 flex-1">{s.name}</span>
                  <span className="text-sm font-semibold text-gray-900">{s.value}</span>
                  <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${(s.value / Math.max(...statusData.map((d) => d.value), 1)) * 100}%`, backgroundColor: s.color }}
                    />
                  </div>
                </div>
              ))}
              {statusData.some((s) => s.name === 'Atrasadas' && s.value > 0) && (
                <a
                  href="/atividades?filter=vencidas"
                  className="flex items-center justify-center gap-1 text-xs text-red-500 font-medium pt-2 hover:underline"
                >
                  Ver atrasadas no detalhe <ArrowRight size={12} />
                </a>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Boards */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <BookOpen size={18} className="text-primary" />
          Seus Quadros
        </h3>
        {boards.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <BookOpen size={32} className="text-gray-300 mb-2" />
            <p className="text-sm text-gray-400">Nenhum quadro ainda.</p>
            <p className="text-xs text-gray-400 mt-1">Crie um quadro na sidebar para começar.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {boards.map((b) => (
              <a
                key={b.id}
                href={`/board/${b.id}`}
                className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:border-primary/30 hover:bg-primary/5 transition-all group"
              >
                <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: b.color || '#4A90D9' }} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900 transition-colors block truncate">
                    {b.name}
                  </span>
                  {b.description && (
                    <span className="text-xs text-gray-400 truncate block">{b.description}</span>
                  )}
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
