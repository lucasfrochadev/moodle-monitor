import { useState } from 'react';
import { Settings, Bell, Palette, Shield, Globe, Database, RefreshCw, User, ChevronRight } from 'lucide-react';
import { cn } from '../utils/cn';
import { Button } from '../components/ui/Button';

const SECTIONS = [
  { id: 'profile', icon: User, label: 'Perfil', description: 'Informações pessoais e preferências' },
  { id: 'notifications', label: 'Notificações', icon: Bell, description: 'Configurar alertas e lembretes' },
  { id: 'appearance', label: 'Aparência', icon: Palette, description: 'Tema, cores e layout' },
  { id: 'privacy', label: 'Privacidade', icon: Shield, description: 'Controle de dados e segurança' },
  { id: 'integration', label: 'Integrações', icon: Database, description: 'Moodle e outras plataformas' },
  { id: 'sync', label: 'Sincronização', icon: RefreshCw, description: 'Agenda e frequência de sync' },
  { id: 'regional', label: 'Regional', icon: Globe, description: 'Idioma e fuso horário' },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState('profile');

  const ActiveSection = () => {
    switch (activeSection) {
      case 'profile':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-base font-semibold text-gray-900 mb-4">Informações do Perfil</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Nome</label>
                  <input type="text" defaultValue="João Silva" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Email</label>
                  <input type="email" defaultValue="joao.silva@email.com" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Instituição</label>
                  <input type="text" defaultValue="Universidade Salesiana" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Curso</label>
                  <input type="text" defaultValue="Ciência da Computação" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all" />
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3 pt-4 border-t border-gray-100">
              <Button variant="primary">Salvar Alterações</Button>
              <Button variant="ghost">Cancelar</Button>
            </div>
          </div>
        );
      case 'notifications':
        return (
          <div className="space-y-4">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Preferências de Notificação</h3>
            {[
              { label: 'Lembretes de prazo', desc: 'Notificar 24h antes do vencimento', enabled: true },
              { label: 'Novas atividades', desc: 'Alertar quando novas atividades forem importadas', enabled: true },
              { label: 'Atualizações de tarefas', desc: 'Notificar quando tarefas forem movidas ou editadas', enabled: false },
              { label: 'Relatório semanal', desc: 'Resumo de progresso toda semana', enabled: true },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between py-3 px-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">{item.label}</p>
                  <p className="text-xs text-gray-500">{item.desc}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked={item.enabled} className="sr-only peer" />
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary" />
                </label>
              </div>
            ))}
          </div>
        );
      case 'appearance':
        return (
          <div className="space-y-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Personalizar Aparência</h3>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-2">Tema</label>
              <div className="flex gap-2">
                {['Claro', 'Escuro', 'Sistema'].map((t) => (
                  <button key={t} className={cn('px-4 py-2 text-sm rounded-lg border transition-all cursor-pointer', t === 'Claro' ? 'border-primary bg-primary/5 text-primary font-medium' : 'border-gray-200 text-gray-600 hover:border-gray-300')}>{t}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-2">Cor de Destaque</label>
              <div className="flex gap-2">
                {['#4A90D9', '#6C5CE7', '#00B894', '#E17055', '#FDCB6E', '#fd79a8'].map((c) => (
                  <button key={c} className={cn('w-8 h-8 rounded-full border-2 transition-all cursor-pointer', c === '#4A90D9' ? 'border-gray-900 scale-110' : 'border-transparent')} style={{ backgroundColor: c }} />
                ))}
              </div>
            </div>
          </div>
        );
      default:
        return (
          <div className="flex items-center justify-center h-48 text-sm text-gray-400">
            Configurações de "{SECTIONS.find(s => s.id === activeSection)?.label}" em desenvolvimento
          </div>
        );
    }
  };

  return (
    <div className="p-4 lg:p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Settings size={22} className="text-primary" />
        <h2 className="text-lg font-semibold text-gray-900">Configurações</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <nav className="bg-white rounded-xl border border-gray-200 p-2 space-y-0.5">
            {SECTIONS.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all text-left cursor-pointer',
                  activeSection === section.id
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-gray-600 hover:bg-gray-50'
                )}
              >
                <section.icon size={18} />
                <div className="flex-1 min-w-0">
                  <span className="block truncate">{section.label}</span>
                </div>
                <ChevronRight size={14} className={cn('text-gray-300 shrink-0', activeSection === section.id && 'text-primary')} />
              </button>
            ))}
          </nav>
        </div>

        <div className="lg:col-span-3">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <ActiveSection />
          </div>
        </div>
      </div>
    </div>
  );
}
