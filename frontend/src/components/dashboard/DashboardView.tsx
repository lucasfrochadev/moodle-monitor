import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Calendar,
  Clock,
  CheckCircle2,
  ListTodo,
  TrendingUp,
  Layers,
  BookOpen,
  BarChart3,
  PieChart,
} from 'lucide-react';
import { useBoardStore } from '../../store/boardStore';
import { useTaskStore } from '../../store/taskStore';
import { useUIStore } from '../../store/uiStore';
import { cn } from '../../utils/cn';
import { formatDateShort, isOverdue, daysUntil } from '../../utils/date';
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

const WEEKLY_DATA = [
  { day: 'Seg', tasks: 3 },
  { day: 'Ter', tasks: 5 },
  { day: 'Qua', tasks: 2 },
  { day: 'Qui', tasks: 7 },
  { day: 'Sex', tasks: 4 },
  { day: 'Sáb', tasks: 1 },
  { day: 'Dom', tasks: 0 },
];

const DISTRIBUTION_DATA = [
  { name: 'IA', value: 25, color: '#4A90D9' },
  { name: 'BD', value: 20, color: '#6C5CE7' },
  { name: 'Redes', value: 15, color: '#00B894' },
  { name: 'ES', value: 25, color: '#FDCB6E' },
  { name: 'PI', value: 15, color: '#E17055' },
];

const PROGRESS_DATA = [
  { month: 'Jan', completed: 8, pending: 12 },
  { month: 'Fev', completed: 12, pending: 10 },
  { month: 'Mar', completed: 15, pending: 8 },
  { month: 'Abr', completed: 10, pending: 14 },
  { month: 'Mai', completed: 18, pending: 6 },
];

export function DashboardView() {
  const { boards, loadBoards } = useBoardStore();
  const { vigentActivities, loadVigent } = useTaskStore();
  const { openTaskModal } = useUIStore();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [s] = await Promise.all([
          fetchDashboard().catch(() => null),
          loadBoards(),
          loadVigent(),
        ]);
        setStats(s);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [loadBoards, loadVigent]);

  const overdueTasks = useMemo(
    () => vigentActivities.filter((a) => isOverdue(a.due_date) && a.status !== 'completed'),
    [vigentActivities]
  );

  const upcomingTasks = useMemo(() => {
    return vigentActivities
      .filter((a) => {
        const d = daysUntil(a.due_date);
        return d !== null && d >= 0 && d <= 7;
      })
      .sort((a, b) => (a.due_date || '').localeCompare(b.due_date || ''));
  }, [vigentActivities]);

  if (loading) return <Spinner size="lg" />;

  const statCards = [
    { label: 'Total de Tarefas', value: stats?.total_tasks ?? 0, icon: ListTodo, color: 'text-primary', bg: 'bg-primary/10' },
    { label: 'Pendentes', value: stats?.pending ?? 0, icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50' },
    { label: 'Em Andamento', value: stats?.in_progress ?? 0, icon: TrendingUp, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Concluídas', value: stats?.completed ?? 0, icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Atrasadas', value: stats?.overdue ?? 0, icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-50' },
    { label: 'Vencem Esta Semana', value: stats?.due_this_week ?? 0, icon: Calendar, color: 'text-orange-500', bg: 'bg-orange-50' },
  ];

  return (
    <div className="p-4 lg:p-6 max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-1 flex items-center gap-2">
            <BarChart3 size={16} className="text-primary" />
            Atividades por Dia
          </h3>
          <p className="text-xs text-gray-400 mb-4">Distribuição semanal de tarefas</p>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={WEEKLY_DATA}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                  cursor={{ fill: '#f3f4f6' }}
                />
                <Bar dataKey="tasks" radius={[4, 4, 0, 0]} fill="#4A90D9" maxBarSize={32} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-1 flex items-center gap-2">
            <PieChart size={16} className="text-primary" />
            Distribuição por Disciplina
          </h3>
          <p className="text-xs text-gray-400 mb-4">Tarefas por área de estudo</p>
          <div className="flex items-center gap-4">
            <div className="h-40 w-40 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <RePieChart>
                  <Pie
                    data={DISTRIBUTION_DATA}
                    innerRadius={35}
                    outerRadius={60}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {DISTRIBUTION_DATA.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                  />
                </RePieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-2 flex-1">
              {DISTRIBUTION_DATA.map((item) => (
                <div key={item.name} className="flex items-center gap-2 text-xs">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                  <span className="text-gray-600 flex-1">{item.name}</span>
                  <span className="font-medium text-gray-900">{item.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertTriangle size={18} className="text-red-500" />
            Atividades Atrasadas
            {overdueTasks.length > 0 && (
              <span className="text-xs font-normal text-gray-400 ml-1">({overdueTasks.length})</span>
            )}
          </h3>
          {overdueTasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <CheckCircle2 size={32} className="text-emerald-300 mb-2" />
              <p className="text-sm text-gray-400">Nenhuma atividade atrasada!</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-56 overflow-y-auto">
              {overdueTasks.slice(0, 8).map((t) => (
                <div
                  key={t.id}
                  onClick={() => openTaskModal(t.id, t.board_id)}
                  className="flex items-center justify-between p-3 bg-red-50 rounded-lg cursor-pointer hover:bg-red-100 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">{t.title}</p>
                    <p className="text-xs text-gray-500">{t.discipline}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <span className="text-xs text-red-500 font-medium">{formatDateShort(t.due_date)}</span>
                    <AlertTriangle size={14} className="text-red-400" />
                  </div>
                </div>
              ))}
              {overdueTasks.length > 8 && (
                <p className="text-xs text-gray-400 text-center pt-1">
                  + {overdueTasks.length - 8} outras atrasadas
                </p>
              )}
            </div>
          )}
        </div>

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
            <div className="space-y-2 max-h-56 overflow-y-auto">
              {upcomingTasks.slice(0, 8).map((t) => (
                <div
                  key={t.id}
                  onClick={() => openTaskModal(t.id, t.board_id)}
                  className="flex items-center justify-between p-3 bg-orange-50 rounded-lg cursor-pointer hover:bg-orange-100 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">{t.title}</p>
                    <p className="text-xs text-gray-500">{t.discipline}</p>
                  </div>
                  <span className="text-xs text-orange-600 font-medium shrink-0 ml-2">
                    {formatDateShort(t.due_date)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-1 flex items-center gap-2">
            <TrendingUp size={16} className="text-emerald-500" />
            Progresso Mensal
          </h3>
          <p className="text-xs text-gray-400 mb-4">Tarefas concluídas vs pendentes</p>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={PROGRESS_DATA} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                  cursor={{ fill: '#f3f4f6' }}
                />
                <Bar dataKey="completed" name="Concluídas" radius={[4, 4, 0, 0]} fill="#10B981" maxBarSize={24} />
                <Bar dataKey="pending" name="Pendentes" radius={[4, 4, 0, 0]} fill="#F59E0B" maxBarSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Layers size={18} className="text-primary" />
            Seus Quadros
          </h3>
          {boards.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <BookOpen size={32} className="text-gray-300 mb-2" />
              <p className="text-sm text-gray-400">Nenhum quadro ainda.</p>
              <p className="text-xs text-gray-400 mt-1">Crie um quadro na sidebar para começar.</p>
            </div>
          ) : (
            <div className="space-y-2">
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
                  <TrendingUp size={16} className="text-gray-300 group-hover:text-primary transition-colors shrink-0" />
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
