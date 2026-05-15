import { useEffect, useMemo, useState } from 'react';
import {
  Search,
  AlertTriangle,
  BookOpen,
  Calendar,
  ClipboardList,
  Send,
  Archive,
  XCircle,
  Edit3,
  MoreHorizontal,
} from 'lucide-react';
import { useUIStore } from '../../store/uiStore';
import { cn } from '../../utils/cn';
import { formatDateShort, isOverdue, daysUntil } from '../../utils/date';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Spinner } from '../ui/Spinner';
import { EmptyState } from '../ui/EmptyState';
import { STATUS_LABELS, STATUS_COLORS } from '../../types';
import { fetchVigentActivities } from '../../api/tasks';
import type { Task } from '../../types';

export function ActivityList() {
  const { openTaskModal } = useUIStore();
  const [activities, setActivities] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterDiscipline, setFilterDiscipline] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'due_date' | 'priority' | 'discipline'>('due_date');
  const [actionMenu, setActionMenu] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const today = new Date().toISOString().split('T')[0];
        const data = await fetchVigentActivities({ due_date_after: today });
        setActivities(data);
      } catch {
        setActivities([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const disciplines = useMemo(() => {
    const set = new Set<string>();
    activities.forEach((a) => {
      if (a.discipline) set.add(a.discipline);
    });
    return Array.from(set).sort();
  }, [activities]);

  const handleArchive = (id: string) => {
    setActivities((prev) => prev.filter((a) => a.id !== id));
    setActionMenu(null);
  };

  const handleIgnore = (id: string) => {
    setActivities((prev) => prev.filter((a) => a.id !== id));
    setActionMenu(null);
  };

  const handleSendToKanban = (_id: string) => {
    setActionMenu(null);
  };

  const filtered = useMemo(() => {
    let items = [...activities];

    if (search) {
      const q = search.toLowerCase();
      items = items.filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          a.discipline.toLowerCase().includes(q)
      );
    }

    if (filterStatus !== 'all') {
      items = items.filter((a) => a.status === filterStatus);
    }

    if (filterDiscipline !== 'all') {
      items = items.filter((a) => a.discipline === filterDiscipline);
    }

    items.sort((a, b) => {
      if (sortBy === 'priority') return b.priority - a.priority;
      if (sortBy === 'discipline') return a.discipline.localeCompare(b.discipline);
      if (a.due_date && b.due_date) return a.due_date.localeCompare(b.due_date);
      if (a.due_date) return -1;
      if (b.due_date) return 1;
      return 0;
    });

    return items;
  }, [activities, search, filterStatus, filterDiscipline, sortBy]);

  const stats = useMemo(() => {
    const total = activities.length;
    const overdue = activities.filter((a) => isOverdue(a.due_date) && a.status !== 'completed').length;
    const dueThisWeek = activities.filter((a) => {
      const d = daysUntil(a.due_date);
      return d !== null && d >= 0 && d <= 7;
    }).length;
    return { total, overdue, dueThisWeek };
  }, [activities]);

  return (
    <div className="p-4 lg:p-6 max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500">Total de Atividades</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{stats.total}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500">Atrasadas</p>
          <p className={cn('text-2xl font-bold mt-1', stats.overdue > 0 ? 'text-red-500' : 'text-gray-900')}>
            {stats.overdue}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500">Vencem Esta Semana</p>
          <p className={cn('text-2xl font-bold mt-1', stats.dueThisWeek > 0 ? 'text-orange-500' : 'text-gray-900')}>
            {stats.dueThisWeek}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500">Taxa de Conclusão</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {stats.total > 0 ? Math.round((stats.total - stats.overdue - stats.dueThisWeek) / stats.total * 100) : 0}%
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar atividades..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
          >
            <option value="all">Todos os status</option>
            {Object.entries(STATUS_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
          <select
            value={filterDiscipline}
            onChange={(e) => setFilterDiscipline(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
          >
            <option value="all">Todas as disciplinas</option>
            {disciplines.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
          >
            <option value="due_date">Ordenar por Prazo</option>
            <option value="priority">Ordenar por Prioridade</option>
            <option value="discipline">Ordenar por Disciplina</option>
          </select>
        </div>
      </div>

      {loading ? (
        <Spinner />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<ClipboardList size={48} />}
          title="Nenhuma atividade encontrada"
          description={search || filterStatus !== 'all' || filterDiscipline !== 'all'
            ? 'Tente ajustar os filtros'
            : 'Nenhuma atividade importada ainda. Use o botão Sincronizar para importar do monitor.'
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((activity) => {
            const overdue = isOverdue(activity.due_date) && activity.status !== 'completed';
            const dueDays = daysUntil(activity.due_date);
            const isUrgent = dueDays !== null && dueDays >= 0 && dueDays <= 2;
            const isOpen = actionMenu === activity.id;

            return (
              <div
                key={activity.id}
                className={cn(
                  'bg-white rounded-xl border p-4 transition-all duration-150 group',
                  'hover:shadow-md hover:border-gray-300',
                  overdue && 'border-l-[3px] border-l-red-500',
                  isUrgent && !overdue && 'border-l-[3px] border-l-orange-400'
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-gray-900 line-clamp-2 leading-snug">
                      {activity.title}
                    </h3>
                    {activity.discipline && (
                      <div className="flex items-center gap-1.5 mt-1.5 text-xs text-gray-500">
                        <BookOpen size={13} />
                        <span className="truncate">{activity.discipline}</span>
                      </div>
                    )}
                  </div>
                  <div className="relative shrink-0">
                    <button
                      onClick={(e) => { e.stopPropagation(); setActionMenu(isOpen ? null : activity.id); }}
                      className="p-1.5 rounded-lg hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
                    >
                      <MoreHorizontal size={15} className="text-gray-400" />
                    </button>
                    {isOpen && (
                      <div className="absolute right-0 top-9 z-50 w-44 bg-white rounded-xl shadow-lg border border-gray-200 py-1">
                        <button
                          onClick={() => handleSendToKanban(activity.id)}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer"
                        >
                          <Send size={14} className="text-primary" />
                          Enviar para Kanban
                        </button>
                        <button
                          onClick={() => { openTaskModal(activity.id, activity.board_id); setActionMenu(null); }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer"
                        >
                          <Edit3 size={14} className="text-gray-400" />
                          Editar
                        </button>
                        <button
                          onClick={() => handleArchive(activity.id)}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer"
                        >
                          <Archive size={14} className="text-gray-400" />
                          Arquivar
                        </button>
                        <div className="border-t border-gray-100 my-1" />
                        <button
                          onClick={() => handleIgnore(activity.id)}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                        >
                          <XCircle size={14} />
                          Ignorar
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  <Badge className={cn('text-[10px]', STATUS_COLORS[activity.status])}>
                    {STATUS_LABELS[activity.status] || activity.status}
                  </Badge>
                  {activity.priority > 0 && (
                    <span className={cn(
                      'text-[10px] px-1.5 py-0.5 rounded-full font-medium',
                      activity.priority === 3 ? 'bg-red-100 text-red-700' :
                      activity.priority === 2 ? 'bg-orange-100 text-orange-700' :
                      'bg-blue-100 text-blue-700'
                    )}>
                      {activity.priority === 3 ? 'Urgente' : activity.priority === 2 ? 'Alta' : 'Média'}
                    </span>
                  )}
                  {(activity.due_date || activity.publication_date) && (
                    <span className={cn(
                      'flex items-center gap-1 text-xs ml-auto',
                      overdue ? 'text-red-500 font-semibold' : isUrgent ? 'text-orange-500 font-medium' : 'text-gray-500'
                    )}>
                      {overdue ? <AlertTriangle size={12} /> : <Calendar size={12} />}
                      {activity.due_date ? formatDateShort(activity.due_date) : 'Pub. ' + formatDateShort(activity.publication_date!)}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button variant="ghost" size="sm" className="text-xs flex-1 h-8" onClick={() => handleSendToKanban(activity.id)}>
                    <Send size={13} />
                    Kanban
                  </Button>
                  <Button variant="ghost" size="sm" className="text-xs flex-1 h-8" onClick={() => handleArchive(activity.id)}>
                    <Archive size={13} />
                    Arquivar
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
