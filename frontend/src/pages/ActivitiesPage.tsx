import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { ActivityList } from '../components/activities/ActivityList';
import { Button } from '../components/ui/Button';
import { triggerSync } from '../api/other';
import { showToast } from '../components/ui/Toast';
import { cn } from '../utils/cn';

const FILTERS = [
  { key: 'vigentes', label: 'Vigentes' },
  { key: 'todas', label: 'Todas' },
  { key: 'vencidas', label: 'Vencidas' },
] as const;

export type FilterMode = (typeof FILTERS)[number]['key'];

export default function ActivitiesPage() {
  const [syncing, setSyncing] = useState(false);
  const [syncKey, setSyncKey] = useState(0);
  const [filterMode, setFilterMode] = useState<FilterMode>('vigentes');

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await triggerSync();
      showToast('success', 'Sincronizado!', result.message || 'Atividades importadas com sucesso.');
      setTimeout(() => window.location.reload(), 1500);
    } catch (e: any) {
      showToast('error', 'Erro na sincronização', e?.message || 'Não foi possível sincronizar.');
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="px-4 lg:px-6 pt-4 flex items-center justify-between">
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilterMode(f.key)}
              className={cn(
                'px-3 py-1.5 text-sm font-medium rounded-md transition-all cursor-pointer',
                filterMode === f.key
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <Button variant="primary" size="sm" onClick={handleSync} loading={syncing}>
          <RefreshCw size={16} />
          Sincronizar
        </Button>
      </div>
      <ActivityList key={syncKey} filterMode={filterMode} />
    </div>
  );
}
