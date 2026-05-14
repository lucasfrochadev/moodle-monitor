import { useState } from 'react';
import { BookOpen, Clock, TrendingUp, MoreHorizontal } from 'lucide-react';
import { cn } from '../utils/cn';

interface Discipline {
  id: string;
  name: string;
  code: string;
  professor: string;
  color: string;
  totalTasks: number;
  completedTasks: number;
  nextDeadline: string;
}

const MOCK_DISCIPLINES: Discipline[] = [
  { id: '1', name: 'Inteligência Artificial', code: 'IA01', professor: 'Dr. Silva', color: '#4A90D9', totalTasks: 12, completedTasks: 5, nextDeadline: '18/05' },
  { id: '2', name: 'Banco de Dados', code: 'BD02', professor: 'Dra. Oliveira', color: '#6C5CE7', totalTasks: 8, completedTasks: 3, nextDeadline: '20/05' },
  { id: '3', name: 'Redes de Computadores', code: 'RC03', professor: 'Dr. Santos', color: '#00B894', totalTasks: 10, completedTasks: 7, nextDeadline: '22/05' },
  { id: '4', name: 'Engenharia de Software', code: 'ES04', professor: 'Dr. Costa', color: '#FDCB6E', totalTasks: 6, completedTasks: 2, nextDeadline: '25/05' },
  { id: '5', name: 'Projeto Integrador', code: 'PI05', professor: 'Dra. Lima', color: '#E17055', totalTasks: 15, completedTasks: 4, nextDeadline: '01/06' },
  { id: '6', name: 'Sistemas Operacionais', code: 'SO06', professor: 'Dr. Pereira', color: '#00CEC9', totalTasks: 9, completedTasks: 6, nextDeadline: '28/05' },
];

export default function DisciplinesPage() {
  const [disciplines] = useState(MOCK_DISCIPLINES);
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [filter, setFilter] = useState('all');

  const filtered = filter === 'all' ? disciplines : disciplines.filter((d) => {
    const progress = d.totalTasks > 0 ? (d.completedTasks / d.totalTasks) * 100 : 0;
    if (filter === 'high') return progress >= 75;
    if (filter === 'medium') return progress >= 40 && progress < 75;
    if (filter === 'low') return progress < 40;
    return true;
  });

  return (
    <div className="p-4 lg:p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen size={22} className="text-primary" />
          <h2 className="text-lg font-semibold text-gray-900">Disciplinas</h2>
          <span className="text-xs text-gray-400 bg-gray-100 rounded-full px-2 py-0.5">{disciplines.length} ativas</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-gray-100 rounded-lg p-0.5">
            <button onClick={() => setView('grid')} className={cn('px-3 py-1.5 text-xs rounded-md transition-colors cursor-pointer', view === 'grid' ? 'bg-white shadow-sm text-gray-700' : 'text-gray-500 hover:text-gray-700')}>Grid</button>
            <button onClick={() => setView('list')} className={cn('px-3 py-1.5 text-xs rounded-md transition-colors cursor-pointer', view === 'list' ? 'bg-white shadow-sm text-gray-700' : 'text-gray-500 hover:text-gray-700')}>Lista</button>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {['all', 'high', 'medium', 'low'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors cursor-pointer',
              filter === f ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            {f === 'all' ? 'Todas' : f === 'high' ? 'Avançado' : f === 'medium' ? 'Médio' : 'Iniciante'}
          </button>
        ))}
      </div>

      {view === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((d) => {
            const progress = d.totalTasks > 0 ? Math.round((d.completedTasks / d.totalTasks) * 100) : 0;
            return (
              <div key={d.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-gray-300 transition-all duration-200 group">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center text-white text-sm font-bold" style={{ backgroundColor: d.color }}>
                      {d.name.charAt(0)}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900">{d.name}</h3>
                      <p className="text-xs text-gray-500">{d.code}</p>
                    </div>
                  </div>
                  <button className="p-1.5 rounded-lg hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-all cursor-pointer">
                    <MoreHorizontal size={16} className="text-gray-400" />
                  </button>
                </div>

                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>Progresso</span>
                    <span className="font-medium">{progress}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${progress}%`, backgroundColor: d.color }} />
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-gray-100 grid grid-cols-2 gap-3 text-xs">
                  <div className="flex items-center gap-1.5 text-gray-500">
                    <Clock size={13} />
                    <span>Prazo: {d.nextDeadline}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-gray-500">
                    <TrendingUp size={13} />
                    <span>{d.totalTasks - d.completedTasks} restantes</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/50">
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Disciplina</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Código</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Professor</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Progresso</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Tarefas</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Próximo Prazo</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d) => {
                  const progress = d.totalTasks > 0 ? Math.round((d.completedTasks / d.totalTasks) * 100) : 0;
                  return (
                    <tr key={d.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                          <span className="font-medium text-gray-900">{d.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{d.code}</td>
                      <td className="px-4 py-3 text-gray-500">{d.professor}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${progress}%`, backgroundColor: d.color }} />
                          </div>
                          <span className="text-xs text-gray-500">{progress}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{d.completedTasks}/{d.totalTasks}</td>
                      <td className="px-4 py-3 text-gray-500">{d.nextDeadline}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
