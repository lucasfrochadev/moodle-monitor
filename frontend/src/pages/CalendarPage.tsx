import { useState } from 'react';
import { ChevronLeft, ChevronRight, CalendarDays, Clock, AlertTriangle, BookOpen } from 'lucide-react';
import { cn } from '../utils/cn';
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, isSameDay, isToday, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const MOCK_EVENTS = [
  { id: '1', title: 'Entrega TP1 - Inteligência Artificial', date: '2026-05-18', discipline: 'Inteligência Artificial', priority: 3 },
  { id: '2', title: 'Prova - Banco de Dados', date: '2026-05-20', discipline: 'Banco de Dados', priority: 2 },
  { id: '3', title: 'Lista de Exercícios - Redes', date: '2026-05-22', discipline: 'Redes de Computadores', priority: 1 },
  { id: '4', title: 'Seminário - Engenharia de Software', date: '2026-05-25', discipline: 'Engenharia de Software', priority: 2 },
  { id: '5', title: 'Entrega Final - Projeto Integrador', date: '2026-06-01', discipline: 'Projeto Integrador', priority: 3 },
];

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const calStart = startOfWeek(monthStart, { locale: ptBR });
  const calEnd = endOfWeek(monthEnd, { locale: ptBR });
  const days = eachDayOfInterval({ start: calStart, end: calEnd });

  const eventsForSelected = selectedDate
    ? MOCK_EVENTS.filter((e) => isSameDay(parseISO(e.date), selectedDate))
    : [];

  const prevMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));

  return (
    <div className="p-4 lg:p-6 max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5">
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
              const events = MOCK_EVENTS.filter((e) => isSameDay(parseISO(e.date), day));
              const isSelected = selectedDate && isSameDay(day, selectedDate);
              return (
                <button
                  key={i}
                  onClick={() => setSelectedDate(day)}
                  className={cn(
                    'min-h-[72px] p-1.5 border border-transparent rounded-lg text-left transition-all cursor-pointer',
                    'hover:bg-gray-50',
                    !isSameMonth(day, currentDate) && 'opacity-30',
                    isSelected && 'bg-primary/5 border-primary/30 ring-1 ring-primary/20',
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
                    {events.slice(0, 2).map((e) => (
                      <div
                        key={e.id}
                        className={cn(
                          'text-[9px] px-1 py-0.5 rounded font-medium truncate',
                          e.priority === 3 ? 'bg-red-100 text-red-700' : e.priority === 2 ? 'bg-orange-100 text-orange-700' : 'bg-blue-100 text-blue-700'
                        )}
                      >
                        {e.title}
                      </div>
                    ))}
                    {events.length > 2 && (
                      <div className="text-[9px] text-gray-400 px-1">+{events.length - 2} mais</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">
            {selectedDate ? format(selectedDate, "dd 'de' MMMM", { locale: ptBR }) : 'Selecione uma data'}
          </h3>
          {eventsForSelected.length === 0 ? (
            <div className="text-sm text-gray-400 py-8 text-center">
              {selectedDate ? 'Nenhuma atividade nesta data' : 'Clique em uma data para ver atividades'}
            </div>
          ) : (
            <div className="space-y-3">
              {eventsForSelected.map((e) => (
                <div key={e.id} className="p-3 rounded-lg bg-gray-50 border border-gray-100 space-y-2">
                  <div className="flex items-start gap-2">
                    <span className={cn(
                      'w-2 h-2 rounded-full mt-1.5 shrink-0',
                      e.priority === 3 ? 'bg-red-500' : e.priority === 2 ? 'bg-orange-400' : 'bg-blue-400'
                    )} />
                    <h4 className="text-sm font-medium text-gray-900">{e.title}</h4>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span className="flex items-center gap-1"><BookOpen size={12} />{e.discipline}</span>
                    <span className="flex items-center gap-1">
                      {e.priority === 3 ? <AlertTriangle size={12} className="text-red-500" /> : <Clock size={12} />}
                      {e.priority === 3 ? 'Urgente' : e.priority === 2 ? 'Alta' : 'Normal'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
