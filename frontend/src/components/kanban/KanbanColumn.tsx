import { useDroppable } from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { Plus, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { KanbanCard } from './KanbanCard';
import type { ColumnWithTasks } from '../../types';
import { cn } from '../../utils/cn';
import { useState } from 'react';

interface KanbanColumnProps {
  column: ColumnWithTasks;
  onAddTask: () => void;
  onTaskClick: (taskId: string) => void;
  onEditTask: (taskId: string) => void;
  onDeleteTask: (taskId: string) => void;
  onEditColumn?: () => void;
  onDeleteColumn?: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#F59E0B',
  in_progress: '#4A90D9',
  review: '#8B5CF6',
  completed: '#10B981',
};

export function KanbanColumn({ column, onAddTask, onTaskClick, onEditTask, onDeleteTask, onEditColumn, onDeleteColumn }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });
  const [menuOpen, setMenuOpen] = useState(false);

  const colColor = column.color || STATUS_COLORS[column.id] || '#E0E0E0';

  return (
    <div className="shrink-0 w-72 flex flex-col bg-gray-50/80 rounded-xl border border-gray-200/60 max-h-full">
      <div className="flex items-center justify-between px-3.5 py-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: colColor }} />
          <h3 className="font-semibold text-sm text-gray-800 truncate">{column.name}</h3>
          <span className="text-[11px] font-medium text-gray-400 bg-white border border-gray-200 rounded-md px-1.5 py-0.5 shrink-0">
            {column.tasks.length}
          </span>
        </div>
        <div className="flex items-center gap-0.5">
          <button
            onClick={onAddTask}
            className="p-1.5 rounded-lg hover:bg-white hover:shadow-sm transition-all cursor-pointer opacity-0 group-hover:opacity-100"
            title="Adicionar tarefa"
          >
            <Plus size={15} className="text-gray-400" />
          </button>
          {(onEditColumn || onDeleteColumn) && (
            <div className="relative">
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}
                className="p-1.5 rounded-lg hover:bg-white hover:shadow-sm transition-all cursor-pointer"
              >
                <MoreHorizontal size={14} className="text-gray-400" />
              </button>
              {menuOpen && (
                <div className="absolute right-0 top-8 z-50 w-40 bg-white rounded-xl shadow-lg border border-gray-200 py-1">
                  {onEditColumn && (
                    <button
                      onClick={() => { setMenuOpen(false); onEditColumn?.(); }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer"
                    >
                      <Pencil size={14} />
                      Editar coluna
                    </button>
                  )}
                  {onDeleteColumn && (
                    <button
                      onClick={() => { setMenuOpen(false); onDeleteColumn?.(); }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                    >
                      <Trash2 size={14} />
                      Excluir coluna
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div
        ref={setNodeRef}
        className={cn(
          'flex-1 px-2 pb-2 space-y-2 overflow-y-auto overflow-x-hidden min-h-[120px] transition-colors rounded-b-xl',
          isOver && 'bg-primary/5 ring-2 ring-primary/20 ring-inset'
        )}
      >
        <SortableContext
          items={column.tasks.map((t) => t.id)}
          strategy={verticalListSortingStrategy}
        >
          {column.tasks.map((task) => (
            <KanbanCard
              key={task.id}
              task={task}
              onClick={() => onTaskClick(task.id)}
              onEdit={() => onEditTask(task.id)}
              onDelete={() => onDeleteTask(task.id)}
            />
          ))}
        </SortableContext>

        {column.tasks.length === 0 && (
          <div className="flex flex-col items-center justify-center h-24 text-xs text-gray-400 gap-1">
            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
              <Plus size={14} className="text-gray-300" />
            </div>
            <span>Arraste tarefas aqui</span>
          </div>
        )}
      </div>
    </div>
  );
}
