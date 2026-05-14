import { useState } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Clock, AlertTriangle, MoreHorizontal, Edit3, Trash2 } from 'lucide-react';
import type { Task } from '../../types';
import { cn } from '../../utils/cn';
import { formatDateShort, isOverdue } from '../../utils/date';
import { Badge } from '../ui/Badge';

interface KanbanCardProps {
  task: Task;
  onClick?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  isDragOverlay?: boolean;
}

const PRIORITY_CONFIG: Record<number, { dot: string; label: string; bg: string }> = {
  0: { dot: 'bg-gray-300', label: 'Normal', bg: 'bg-gray-100 text-gray-600' },
  1: { dot: 'bg-blue-400', label: 'Média', bg: 'bg-blue-100 text-blue-700' },
  2: { dot: 'bg-orange-400', label: 'Alta', bg: 'bg-orange-100 text-orange-700' },
  3: { dot: 'bg-red-500', label: 'Urgente', bg: 'bg-red-100 text-red-700' },
};

function getInitials(name?: string): string {
  if (!name) return '?';
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}

const STATUS_PROGRESS: Record<string, number> = {
  pending: 0,
  in_progress: 50,
  completed: 100,
  overdue: 25,
  archived: 100,
};

export function KanbanCard({ task, onClick, onEdit, onDelete, isDragOverlay }: KanbanCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: task.id,
    disabled: isDragOverlay,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const overdue = !isDragOverlay && isOverdue(task.due_date) && task.status !== 'completed';
  const progress = task.progress ?? STATUS_PROGRESS[task.status] ?? 0;
  const priorityCfg = PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG[0];
  const hasDescription = task.description && task.description.length > 0;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'bg-white rounded-xl border border-gray-200 p-3.5 cursor-pointer group relative',
        'hover:shadow-md hover:border-gray-300 transition-all duration-150',
        isDragging && 'opacity-50 shadow-lg ring-2 ring-primary/20',
        isDragOverlay && 'shadow-xl rotate-3 scale-105',
        overdue && 'border-l-[3px] border-l-overdue'
      )}
      onClick={() => {
        if (!menuOpen) onClick?.();
      }}
    >
      <div className="flex items-start gap-2">
        <button
          {...attributes}
          {...listeners}
          className="mt-0.5 cursor-grab active:cursor-grabbing touch-none opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          <GripVertical size={14} className="text-gray-300" />
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className="text-sm font-semibold text-gray-900 leading-snug line-clamp-2 flex-1">
              {task.title}
            </h4>

            <div className="relative shrink-0">
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}
                className="p-1 rounded-lg hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
              >
                <MoreHorizontal size={15} className="text-gray-400" />
              </button>

              {menuOpen && (
                <div className="absolute right-0 top-8 z-50 w-40 bg-white rounded-xl shadow-lg border border-gray-200 py-1 animate-in fade-in slide-in-from-top-1 duration-100">
                  <button
                    onClick={(e) => { e.stopPropagation(); setMenuOpen(false); onEdit?.(); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer"
                  >
                    <Edit3 size={14} />
                    Editar
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setMenuOpen(false); onDelete?.(); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                  >
                    <Trash2 size={14} />
                    Excluir
                  </button>
                </div>
              )}
            </div>
          </div>

          {hasDescription && (
            <p className="text-xs text-gray-400 mt-1.5 line-clamp-2 leading-relaxed">
              {task.description}
            </p>
          )}

          {task.discipline && (
            <div className="flex items-center gap-1.5 mt-2">
              <Badge variant="info" className="text-[10px] px-1.5 py-0.5 font-normal">
                {task.discipline}
              </Badge>
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 space-y-2">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {task.priority > 0 && (
              <span className={cn('w-2 h-2 rounded-full shrink-0', priorityCfg.dot)} title={priorityCfg.label} />
            )}
            {task.due_date && (
              <span className={cn(
                'flex items-center gap-1 text-[11px]',
                overdue ? 'text-overdue font-semibold' : 'text-gray-500'
              )}>
                {overdue ? <AlertTriangle size={11} /> : <Clock size={11} />}
                {formatDateShort(task.due_date)}
              </span>
            )}
          </div>

          {task.assignee && (
            <div className="flex items-center gap-1.5 shrink-0" title={task.assignee}>
              <div className="w-5 h-5 rounded-full bg-primary text-white flex items-center justify-center text-[9px] font-semibold">
                {getInitials(task.assignee)}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500',
                progress >= 100 ? 'bg-green-500' : overdue ? 'bg-overdue' : 'bg-primary'
              )}
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-[10px] font-medium text-gray-400 min-w-[28px] text-right">{progress}%</span>
        </div>
      </div>
    </div>
  );
}
