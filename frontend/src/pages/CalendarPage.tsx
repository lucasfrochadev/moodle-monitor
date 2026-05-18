import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, CalendarDays, Clock, BookOpen, Plus, X, Trash2, Save } from 'lucide-react';
import { cn } from '../utils/cn';
import {
  format, startOfMonth, endOfMonth, startOfWeek, endOfWeek,
  eachDayOfInterval, isSameMonth, isSameDay, isToday, parseISO
} from 'date-fns';
import { ptBR } from 'date-fns/locale';
import * as calendarApi from '../api/calendar';
import type { CalendarEvent, CalendarBoardTask } from '../types';
import { EVENT_TYPE_LABELS, EVENT_TYPE_COLORS } from '../types';

const EVENT_TYPE_OPTIONS = [
  { value: 'exam', label: 'Prova' },
  { value: 'appointment', label: 'Compromisso' },
  { value: 'study', label: 'Estudo' },
  { value: 'other', label: 'Outro' },
];

const TODO_COLORS = ['#EF4444', '#F59E0B', '#3B82F6', '#8B5CF6', '#10B981', '#EC4899', '#6366F1'];

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [boardTasks, setBoardTasks] = useState<CalendarBoardTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);
  const [showForm, setShowForm] = useState(false);

  // Form state
  const [formTitle, setFormTitle] = useState('');
  const [formType, setFormType] = useState('other');
  const [formTime, setFormTime] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formColor, setFormColor] = useState('#8B5CF6');

  const monthStr = format(currentDate, 'yyyy-MM');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [evts, tasks] = await Promise.all([
        calendarApi.fetchEvents(monthStr),
        calendarApi.fetchBoardTasks(),
      ]);
      setEvents(evts);
      setBoardTasks(tasks);
    } catch {
      // silent
    }
    setLoading(false);
  }, [monthStr]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const calStart = startOfWeek(monthStart, { locale: ptBR });
  const calEnd = endOfWeek(monthEnd, { locale: ptBR });
  const days = eachDayOfInterval({ start: calStart, end: calEnd });

  const dateStr = (d: Date) => format(d, 'yyyy-MM-dd');

  const eventsForDate = (d: Date) => {
    const ds = dateStr(d);
    const cal = events.filter((e) => e.event_date === ds);
    const tasks = boardTasks.filter((t) => t.due_date && t.due_date.startsWith(ds));
    return { cal, tasks };
  };

  const selectedEvents = selectedDate ? eventsForDate(selectedDate) : null;

  const resetForm = () => {
    setFormTitle('');
    setFormType('other');
    setFormTime('');
    setFormDesc('');
    setFormColor('#8B5CF6');
    setEditingEvent(null);
    setShowForm(false);
  };

  const handleSave = async () => {
    if (!formTitle.trim() || !selectedDate) return;
    const ds = dateStr(selectedDate);
    try {
      if (editingEvent) {
        await calendarApi.updateEvent(editingEvent.id, {
          title: formTitle,
          event_type: formType,
          event_time: formTime,
          description: formDesc,
          color: formColor,
        });
      } else {
        await calendarApi.createEvent({
          title: formTitle,
          event_date: ds,
          event_time: formTime,
          event_type: formType,
          description: formDesc,
          color: formColor,
        });
      }
      await loadData();
      resetForm();
    } catch {
      // silent
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await calendarApi.deleteEvent(id);
      await loadData();
      if (editingEvent?.id === id) resetForm();
    } catch {
      // silent
    }
  };

  const startEdit = (e: CalendarEvent) => {
    setEditingEvent(e);
    setFormTitle(e.title);
    setFormType(e.event_type);
    setFormTime(e.event_time || '');
    setFormDesc(e.description || '');
    setFormColor(e.color || '#8B5CF6');
    setShowForm(true);
  };

  const openNewForm = () => {
    resetForm();
    setShowForm(true);
  };

  const prevMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));

  const priorityColor = (p: number) =>
    p >= 3 ? 'bg-red-100 text-red-700' : p >= 2 ? 'bg-orange-100 text-orange-700' : 'bg-blue-100 text-blue-700';

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
        {/* Calendar Grid */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <CalendarDays size={22} className="text-primary" />
              <h2 className="text-lg font-semibold text-gray-900">
                {format(currentDate, "MMMM 'de' yyyy", { locale: ptBR })}
              </h2>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={prevMonth} className="p-2 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
                <ChevronLeft size={18} className="text-gray-500" />
              </button>
              <button onClick={() => setCurrentDate(new Date())} className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer font-medium">
                Hoje
              </button>
              <button onClick={nextMonth} className="p-2 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
                <ChevronRight size={18} className="text-gray-500" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-7 mb-2">
            {['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'].map((d) => (
              <div key={d} className="text-center text-xs font-medium text-gray-400 py-2">{d}</div>
            ))}
          </div>

          <div className="grid grid-cols-7">
            {days.map((day, i) => {
              const { cal, tasks } = eventsForDate(day);
              const count = cal.length + tasks.length;
              const isSel = selectedDate && isSameDay(day, selectedDate);
              return (
                <button
                  key={i}
                  onClick={() => setSelectedDate(day)}
                  className={cn(
                    'min-h-[80px] p-1.5 border border-transparent rounded-lg text-left transition-all cursor-pointer',
                    'hover:bg-gray-50',
                    !isSameMonth(day, currentDate) && 'opacity-30',
                    isSel && 'bg-primary/5 border-primary/30 ring-1 ring-primary/20',
                    isToday(day) && 'font-bold'
                  )}
                >
                  <span className={cn(
                    'text-xs w-6 h-6 flex items-center justify-center rounded-full',
                    isToday(day) && 'bg-primary text-white'
                  )}>
                    {format(day, 'd')}
                  </span>
                  <div className="space-y-0.5 mt-0.5">
                    {tasks.slice(0, 1).map((t) => (
                      <div key={t.id} className="text-[9px] px-1 py-0.5 rounded font-medium truncate bg-blue-100 text-blue-700">
                        {t.title}
                      </div>
                    ))}
                    {cal.slice(0, Math.max(0, tasks.length >= 1 ? 1 : 2)).map((e) => (
                      <div
                        key={e.id}
                        className="text-[9px] px-1 py-0.5 rounded font-medium truncate text-white"
                        style={{ backgroundColor: e.color || EVENT_TYPE_COLORS[e.event_type] || '#8B5CF6' }}
                      >
                        {e.title}
                      </div>
                    ))}
                    {count > 2 && (
                      <div className="text-[9px] text-gray-400 px-1">+{count - 2} mais</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Side Panel */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h3 className="text-sm font-semibold text-gray-900">
            {selectedDate ? format(selectedDate, "dd 'de' MMMM", { locale: ptBR }) : 'Selecione uma data'}
          </h3>

          {selectedDate && selectedEvents && (
            <>
              {/* Board tasks on this date */}
              {selectedEvents.tasks.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Atividades do Quadro</h4>
                  {selectedEvents.tasks.map((t) => (
                    <div key={t.id} className="p-3 rounded-lg bg-blue-50 border border-blue-100 space-y-1">
                      <h5 className="text-sm font-medium text-gray-900">{t.title}</h5>
                      {t.discipline && (
                        <span className="inline-block text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">
                          {t.discipline}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Calendar events on this date */}
              {selectedEvents.cal.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Compromissos</h4>
                  {selectedEvents.cal.map((e) => (
                    <div
                      key={e.id}
                      className="p-3 rounded-lg border space-y-1.5 cursor-pointer hover:shadow-sm transition-shadow"
                      style={{ backgroundColor: `${e.color || EVENT_TYPE_COLORS[e.event_type] || '#8B5CF6'}10`, borderColor: `${e.color || EVENT_TYPE_COLORS[e.event_type] || '#8B5CF6'}30` }}
                      onClick={() => startEdit(e)}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h5 className="text-sm font-medium text-gray-900">{e.title}</h5>
                        <button
                          onClick={(ev) => { ev.stopPropagation(); handleDelete(e.id); }}
                          className="p-1 rounded hover:bg-gray-200/50 transition-colors cursor-pointer shrink-0"
                        >
                          <Trash2 size={12} className="text-gray-400" />
                        </button>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <span
                            className="w-2 h-2 rounded-full inline-block"
                            style={{ backgroundColor: e.color || EVENT_TYPE_COLORS[e.event_type] || '#8B5CF6' }}
                          />
                          {EVENT_TYPE_LABELS[e.event_type] || 'Outro'}
                        </span>
                        {e.event_time && (
                          <span className="flex items-center gap-1"><Clock size={11} />{e.event_time}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {selectedEvents.cal.length === 0 && selectedEvents.tasks.length === 0 && !showForm && (
                <p className="text-sm text-gray-400 py-4 text-center">Nenhum evento nesta data</p>
              )}

              {/* Add / Form toggle */}
              {!showForm ? (
                <button
                  onClick={openNewForm}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors cursor-pointer"
                >
                  <Plus size={16} />
                  Adicionar compromisso
                </button>
              ) : (
                <div className="space-y-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-gray-700">
                      {editingEvent ? 'Editar compromisso' : 'Novo compromisso'}
                    </h4>
                    <button onClick={resetForm} className="p-1 rounded hover:bg-gray-200 transition-colors cursor-pointer">
                      <X size={14} className="text-gray-400" />
                    </button>
                  </div>

                  <input
                    type="text"
                    placeholder="Título"
                    value={formTitle}
                    onChange={(e) => setFormTitle(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                    autoFocus
                  />

                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={formType}
                      onChange={(e) => {
                        setFormType(e.target.value);
                        setFormColor(EVENT_TYPE_COLORS[e.target.value] || '#8B5CF6');
                      }}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary bg-white"
                    >
                      {EVENT_TYPE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                    <input
                      type="time"
                      value={formTime}
                      onChange={(e) => setFormTime(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                    />
                  </div>

                  <input
                    type="text"
                    placeholder="Descrição (opcional)"
                    value={formDesc}
                    onChange={(e) => setFormDesc(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                  />

                  <div className="flex items-center gap-2">
                    {TODO_COLORS.map((c) => (
                      <button
                        key={c}
                        onClick={() => setFormColor(c)}
                        className={cn(
                          'w-6 h-6 rounded-full border-2 transition-all cursor-pointer',
                          formColor === c ? 'border-gray-900 scale-110' : 'border-transparent'
                        )}
                        style={{ backgroundColor: c }}
                      />
                    ))}
                  </div>

                  <button
                    onClick={handleSave}
                    disabled={!formTitle.trim()}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                  >
                    <Save size={14} />
                    {editingEvent ? 'Salvar' : 'Adicionar'}
                  </button>
                </div>
              )}
            </>
          )}

          {!selectedDate && (
            <p className="text-sm text-gray-400 py-8 text-center">Clique em uma data para ver ou adicionar eventos</p>
          )}
        </div>
      </div>
    </div>
  );
}
