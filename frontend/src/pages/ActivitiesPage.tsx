import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { ActivityList } from '../components/activities/ActivityList';
import { Button } from '../components/ui/Button';
import { triggerSync } from '../api/other';
import { showToast } from '../components/ui/Toast';

export default function ActivitiesPage() {
  const [syncing, setSyncing] = useState(false);
  const [syncKey, setSyncKey] = useState(0);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await triggerSync();
      showToast('success', 'Sincronizado!', result.message || 'Atividades importadas com sucesso.');
      setSyncKey((k) => k + 1);
    } catch (e: any) {
      showToast('error', 'Erro na sincronização', e?.message || 'Não foi possível sincronizar.');
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="px-4 lg:px-6 pt-4 flex items-center justify-between">
        <div />
        <Button variant="primary" size="sm" onClick={handleSync} loading={syncing}>
          <RefreshCw size={16} />
          Sincronizar
        </Button>
      </div>
      <ActivityList key={syncKey} />
    </div>
  );
}
