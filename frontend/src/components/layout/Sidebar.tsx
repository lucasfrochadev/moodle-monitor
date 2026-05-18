import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ClipboardList,
  BookOpen,
  KanbanSquare,
  CalendarDays,
  GraduationCap,
  Settings,
} from 'lucide-react';
import { cn } from '../../utils/cn';

interface SidebarProps {
  open: boolean;
}

export function Sidebar({ open }: SidebarProps) {
  const mainNavItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard', exact: true },
    { to: '/quadro', icon: KanbanSquare, label: 'Quadro' },
    { to: '/atividades', icon: ClipboardList, label: 'Atividades Vigentes' },
    { to: '/calendario', icon: CalendarDays, label: 'Calendário' },
    { to: '/disciplinas', icon: GraduationCap, label: 'Disciplinas' },
  ];

  const bottomNavItems = [
    { to: '/configuracoes', icon: Settings, label: 'Configurações' },
  ];

  return (
    <aside
      className={cn(
        'fixed top-0 left-0 z-40 h-screen bg-sidebar transition-all duration-300 flex flex-col',
        open ? 'w-64' : 'w-0 -translate-x-full lg:w-16 lg:translate-x-0'
      )}
    >
      <div className={cn(
        'flex items-center h-16 px-4 border-b border-white/10',
        !open && 'lg:justify-center'
      )}>
        <BookOpen size={24} className="text-primary shrink-0" />
        <span className={cn(
          'ml-3 text-white font-bold text-lg whitespace-nowrap transition-opacity',
          !open && 'lg:hidden'
        )}>
          StudyBoard
        </span>
      </div>

      <nav className="flex-1 px-2 py-4 overflow-y-auto">
        <div className="space-y-0.5">
          <div className={cn(
            'px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-500',
            !open && 'lg:text-center lg:px-0'
          )}>
            <span className={!open ? 'lg:hidden' : ''}>Principal</span>
            {!open && <span className="hidden lg:inline text-[9px]">P</span>}
          </div>
          {mainNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              className={({ isActive }) => cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/20 text-primary-light'
                  : 'text-gray-400 hover:bg-sidebar-hover hover:text-white',
                !open && 'lg:justify-center lg:px-2'
              )}
            >
              <item.icon size={20} className="shrink-0" />
              <span className={cn('truncate', !open && 'lg:hidden')}>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="border-t border-white/10">
        <div className="p-2 space-y-0.5">
          {bottomNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/20 text-primary-light'
                  : 'text-gray-400 hover:bg-sidebar-hover hover:text-white',
                !open && 'lg:justify-center lg:px-2'
              )}
            >
              <item.icon size={20} className="shrink-0" />
              <span className={cn('truncate', !open && 'lg:hidden')}>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </div>
    </aside>
  );
}
