import { Menu, RefreshCw } from 'lucide-react';
import { useUIStore } from '../../store/uiStore';
import { useLocation } from 'react-router-dom';
import { Button } from '../ui/Button';
import { triggerSync } from '../../api/other';
import { useState } from 'react';

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/atividades': 'Atividades Vigentes',
  '/calendario': 'Calendário',
  '/disciplinas': 'Disciplinas',
  '/configuracoes': 'Configurações',
};

export function Navbar() {
  const { toggleSidebar } = useUIStore();
  const location = useLocation();
  const [syncing, setSyncing] = useState(false);

  const title = Object.entries(PAGE_TITLES).find(([path]) =>
    location.pathname === path
  )?.[1] || 'StudyBoard';

  const handleSync = async () => {
    setSyncing(true);
    try {
      await triggerSync();
    } catch (e) {
      console.error('Sync failed:', e);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 lg:px-6 sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer lg:hidden"
        >
          <Menu size={20} className="text-gray-600" />
        </button>
        <h1 className="text-xl font-bold text-gray-900">{title}</h1>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={handleSync}
          loading={syncing}
        >
          <RefreshCw size={16} />
          Sincronizar
        </Button>
      </div>
    </header>
  );
}
