import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ClipboardList,
  BookOpen,
  Plus,
  CalendarDays,
  GraduationCap,
  Settings,
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { useBoardStore } from '../../store/boardStore';
import { useUIStore } from '../../store/uiStore';
import { useEffect } from 'react';
import { Button } from '../ui/Button';
import { CreateBoardModal } from '../boards/CreateBoardModal';

interface SidebarProps {
  open: boolean;
}

export function Sidebar({ open }: SidebarProps) {
  const { boards, loadBoards, createBoard } = useBoardStore();
  const { setCreateBoardModalOpen, createBoardModalOpen } = useUIStore();

  useEffect(() => {
    loadBoards();
  }, [loadBoards]);

  const mainNavItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard', exact: true },
    { to: '/atividades', icon: ClipboardList, label: 'Atividades Vigentes' },
    { to: '/calendario', icon: CalendarDays, label: 'Calendário' },
    { to: '/disciplinas', icon: GraduationCap, label: 'Disciplinas' },
  ];

  const bottomNavItems = [
    { to: '/configuracoes', icon: Settings, label: 'Configurações' },
  ];

  const handleCreateBoard = async (name: string, description?: string, color?: string) => {
    await createBoard(name, description, color);
  };

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

        <div className="pt-4 pb-2">
          <div className={cn(
            'px-3 text-xs font-semibold uppercase tracking-wider text-gray-500',
            !open && 'lg:text-center lg:px-0'
          )}>
            <span className={!open ? 'lg:hidden' : ''}>Quadros</span>
            {!open && <span className="hidden lg:inline">Q</span>}
          </div>
        </div>

        {boards.map((board) => (
          <NavLink
            key={board.id}
            to={`/board/${board.id}`}
            className={({ isActive }) => cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              isActive
                ? 'bg-primary/20 text-primary-light'
                : 'text-gray-400 hover:bg-sidebar-hover hover:text-white',
              !open && 'lg:justify-center lg:px-2'
            )}
          >
            <span
              className="w-3 h-3 rounded-full shrink-0"
              style={{ backgroundColor: board.color || '#4A90D9' }}
            />
            <span className={cn('truncate', !open && 'lg:hidden')}>{board.name}</span>
          </NavLink>
        ))}
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
        <div className={cn('p-2', !open && 'lg:p-1')}>
          <Button
            variant="ghost"
            size="sm"
            className={cn(
              'w-full text-gray-400 hover:text-white hover:bg-sidebar-hover',
              !open && 'lg:justify-center lg:px-2'
            )}
            onClick={() => setCreateBoardModalOpen(true)}
          >
            <Plus size={18} />
            <span className={!open ? 'lg:hidden' : ''}>Novo Quadro</span>
          </Button>
        </div>
      </div>

      <CreateBoardModal
        open={createBoardModalOpen}
        onClose={() => setCreateBoardModalOpen(false)}
        onSubmit={handleCreateBoard}
      />
    </aside>
  );
}
