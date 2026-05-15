import { useEffect, useState } from 'react';
import { BookOpen, Clock, TrendingUp, MoreHorizontal, Search } from 'lucide-react';
import { cn } from '../utils/cn';
import { fetchDisciplines, type Discipline } from '../api/other';
import { EmptyState } from '../components/ui/EmptyState';
import { Spinner } from '../components/ui/Spinner';

const DISCIPLINE_COLORS = [
  '#4A90D9', '#6C5CE7', '#00B894', '#E17055', '#FDCB6E',
  '#fd79a8', '#00CEC9', '#636E72', '#F97316', '#8B5CF6', '#10B981',
];

export default function DisciplinesPage() {
  const [disciplines, setDisciplines] = useState<Discipline[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await fetchDisciplines();
        setDisciplines(data);
      } catch {
        setDisciplines([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filtered = search
    ? disciplines.filter((d) =>
        d.name.toLowerCase().includes(search.toLowerCase())
      )
    : disciplines;

  const getColor = (index: number) => DISCIPLINE_COLORS[index % DISCIPLINE_COLORS.length];
  const getInitials = (name: string) =>
    name.split(' ').map((w) => w[0]).join('').slice(0, 2);

  return (
    <div className="p-4 lg:p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen size={22} className="text-primary" />
          <h2 className="text-lg font-semibold text-gray-900">Disciplinas</h2>
          {!loading && (
            <span className="text-xs text-gray-400 bg-gray-100 rounded-full px-2 py-0.5">
              {disciplines.length} ativas
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-gray-100 rounded-lg p-0.5">
            <button
              onClick={() => setView('grid')}
              className={cn(
                'px-3 py-1.5 text-xs rounded-md transition-colors cursor-pointer',
                view === 'grid' ? 'bg-white shadow-sm text-gray-700' : 'text-gray-500 hover:text-gray-700'
              )}
            >
              Grid
            </button>
            <button
              onClick={() => setView('list')}
              className={cn(
                'px-3 py-1.5 text-xs rounded-md transition-colors cursor-pointer',
                view === 'list' ? 'bg-white shadow-sm text-gray-700' : 'text-gray-500 hover:text-gray-700'
              )}
            >
              Lista
            </button>
          </div>
        </div>
      </div>

      <div className="relative max-w-xs">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar disciplina..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
        />
      </div>

      {loading ? (
        <Spinner />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<BookOpen size={48} />}
          title={search ? 'Nenhuma disciplina encontrada' : 'Nenhuma disciplina disponível'}
          description={
            search
              ? 'Tente ajustar a busca'
              : 'As disciplinas aparecerão após a sincronização com o monitor.'
          }
        />
      ) : view === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((d, i) => (
            <div
              key={d.id}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-gray-300 transition-all duration-200 group"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center text-white text-sm font-bold"
                    style={{ backgroundColor: getColor(i) }}
                  >
                    {getInitials(d.name)}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-gray-900 truncate max-w-[160px]">
                      {d.name}
                    </h3>
                    <p className="text-xs text-gray-500">{d.code}</p>
                  </div>
                </div>
                <button className="p-1.5 rounded-lg hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-all cursor-pointer">
                  <MoreHorizontal size={16} className="text-gray-400" />
                </button>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-2 text-xs">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: getColor(i) }}
                />
                <span className="text-gray-500">ID: {d.course_id}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/50">
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Disciplina</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Código</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">ID Moodle</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d, i) => (
                  <tr
                    key={d.id}
                    className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: getColor(i) }}
                        />
                        <span className="font-medium text-gray-900">{d.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{d.code}</td>
                    <td className="px-4 py-3 text-gray-500">{d.course_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
