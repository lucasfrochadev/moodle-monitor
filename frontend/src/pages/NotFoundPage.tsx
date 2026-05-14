import { useEffect, useState } from 'react';
import { RefreshCw, ServerCrash, WifiOff } from 'lucide-react';
import client, { setMockMode, isMockMode } from '../api/client';
import { Button } from '../components/ui/Button';

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <ServerCrash size={48} className="text-gray-300 mb-4" />
      <h2 className="text-xl font-bold text-gray-500">Página não encontrada</h2>
      <p className="text-sm text-gray-400 mt-1">A página que você procura não existe.</p>
      <a
        href="/"
        className="mt-4 text-sm text-primary hover:underline"
      >
        Voltar ao Dashboard
      </a>
    </div>
  );
}

export function ConnectionCheck() {
  const [status, setStatus] = useState<'checking' | 'ok' | 'error' | 'mock'>(
    isMockMode() ? 'mock' : 'checking'
  );

  useEffect(() => {
    if (status === 'mock') return;
    client.get('/health')
      .then(() => setStatus('ok'))
      .catch(() => {
        setMockMode(true);
        setStatus('mock');
      });
  }, [status]);

  if (status === 'ok' || status === 'checking') return null;

  if (status === 'mock') {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 shadow-lg flex items-center gap-3">
          <WifiOff size={20} className="text-amber-600" />
          <div>
            <p className="text-sm font-medium text-amber-800">Modo demonstração</p>
            <p className="text-xs text-amber-600">Usando dados mockados — backend offline</p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => window.location.reload()}
          >
            <RefreshCw size={14} />
            Tentar
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 shadow-lg flex items-center gap-3">
        <ServerCrash size={20} className="text-red-500" />
        <div>
          <p className="text-sm font-medium text-red-800">Servidor offline</p>
          <p className="text-xs text-red-600">API não está respondendo</p>
        </div>
        <Button
          variant="danger"
          size="sm"
          onClick={() => window.location.reload()}
        >
          <RefreshCw size={14} />
          Tentar
        </Button>
      </div>
    </div>
  );
}
