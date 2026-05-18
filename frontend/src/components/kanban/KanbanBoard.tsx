import { useState, useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  horizontalListSortingStrategy,
} from '@dnd-kit/sortable';
import { Plus } from 'lucide-react';
import { KanbanColumn } from './KanbanColumn';
import { KanbanCard } from './KanbanCard';
import { Button } from '../ui/Button';
import { CreateColumnModal } from './CreateColumnModal';
import { EditColumnModal } from './EditColumnModal';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { useBoardStore } from '../../store/boardStore';
import { useTaskStore } from '../../store/taskStore';
import { useUIStore } from '../../store/uiStore';
import type { ColumnWithTasks } from '../../types';

const COL_PREFIX = 'column:';
function colSortableId(colId: string) { return COL_PREFIX + colId; }

export function KanbanBoard() {
  const { currentBoard, loadBoard, addColumn, updateColumn, deleteColumn, reorderColumns } = useBoardStore();
  const { deleteTask, moveTask } = useTaskStore();
  const { openTaskModal, openCreateTask, setCreateColumnModalOpen, createColumnModalOpen, confirmDialog, showConfirm, closeConfirm } = useUIStore();
  const [activeTask, setActiveTask] = useState<any>(null);
  const [activeColumnId, setActiveColumnId] = useState<string | null>(null);
  const [editingColumn, setEditingColumn] = useState<ColumnWithTasks | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

  const boardId = currentBoard?.id;
  const columnSortableIds = useMemo(
    () => (currentBoard?.columns ?? []).map((c) => colSortableId(c.id)),
    [currentBoard?.columns]
  );

  const handleDragStart = (event: DragStartEvent) => {
    const id = event.active.id as string;
    if (id.startsWith(COL_PREFIX)) {
      setActiveColumnId(id);
      return;
    }
    if (!currentBoard) return;
    for (const col of currentBoard.columns) {
      const task = col.tasks.find((t) => t.id === id);
      if (task) {
        setActiveTask(task);
        break;
      }
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveTask(null);
    setActiveColumnId(null);
    const { active, over } = event;
    if (!over || !boardId) return;

    // Column reorder
    if (String(active.id).startsWith(COL_PREFIX) && String(over.id).startsWith(COL_PREFIX)) {
      const items = (currentBoard?.columns ?? []).map((c, i) => ({
        id: c.id,
        position: i,
      }));
      const activeColId = String(active.id).slice(COL_PREFIX.length);
      const overColId = String(over.id).slice(COL_PREFIX.length);
      const activeIdx = items.findIndex((i) => i.id === activeColId);
      const overIdx = items.findIndex((i) => i.id === overColId);
      if (activeIdx === -1 || overIdx === -1 || activeIdx === overIdx) return;

      const reordered = [...items];
      const [moved] = reordered.splice(activeIdx, 1);
      reordered.splice(overIdx, 0, moved);
      const updated = reordered.map((item, pos) => ({ id: item.id, position: pos }));
      await reorderColumns(updated);
      return;
    }

    // Task move
    const taskId = active.id as string;
    const overId = over.id as string;
    let targetColumnId: string | undefined;
    let targetPosition = 0;

    const overColumn = currentBoard?.columns.find((c) => c.id === overId);
    if (overColumn) {
      targetColumnId = overColumn.id;
      targetPosition = overColumn.tasks.length;
    } else {
      for (const col of currentBoard?.columns || []) {
        const task = col.tasks.find((t) => t.id === overId);
        if (task) {
          targetColumnId = col.id;
          targetPosition = col.tasks.findIndex((t) => t.id === overId);
          break;
        }
      }
    }

    if (!targetColumnId) return;

    let sourceColumnId: string | undefined;
    for (const col of currentBoard?.columns || []) {
      if (col.tasks.find((t) => t.id === taskId)) {
        sourceColumnId = col.id;
        break;
      }
    }

    if (sourceColumnId === targetColumnId) return;

    await moveTask(boardId, taskId, targetColumnId, targetPosition);
    if (boardId) loadBoard(boardId);
  };

  const handleAddColumn = async (name: string, color?: string) => {
    await addColumn(name, color);
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!boardId) return;
    await deleteTask(boardId, taskId);
    loadBoard(boardId);
  };

  const confirmDeleteTask = (taskId: string) => {
    showConfirm({
      title: 'Excluir tarefa',
      message: 'Tem certeza que deseja excluir esta tarefa? Esta ação não pode ser desfeita.',
      confirmLabel: 'Excluir',
      variant: 'danger',
      onConfirm: async () => {
        closeConfirm();
        await handleDeleteTask(taskId);
      },
    });
  };

  const confirmDeleteColumn = async (columnId: string, columnName: string) => {
    showConfirm({
      title: 'Excluir coluna',
      message: `Tem certeza que deseja excluir a coluna "${columnName}"? Todas as tarefas nela também serão excluídas.`,
      confirmLabel: 'Excluir Coluna',
      variant: 'danger',
      onConfirm: async () => {
        closeConfirm();
        await deleteColumn(columnId);
      },
    });
  };

  const handleEditTask = (taskId: string) => {
    if (boardId) openTaskModal(taskId, boardId);
  };

  const handleEditColumn = async (name: string, color?: string) => {
    if (!editingColumn || !boardId) return;
    await updateColumn(editingColumn.id, { name, color });
    loadBoard(boardId);
  };

  if (!currentBoard) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-400">Selecione ou crie um quadro para começar</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex-1 overflow-x-auto pb-4">
          <SortableContext items={columnSortableIds} strategy={horizontalListSortingStrategy}>
            <div className="flex gap-4 h-full min-h-[calc(100vh-8rem)] p-4">
              {currentBoard.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  sortableId={colSortableId(column.id)}
                  onAddTask={() => openCreateTask(currentBoard.id, column.id)}
                  onTaskClick={(taskId) => openTaskModal(taskId, currentBoard.id)}
                  onEditTask={handleEditTask}
                  onDeleteTask={(taskId) => confirmDeleteTask(taskId)}
                  onEditColumn={() => setEditingColumn(column)}
                  onDeleteColumn={() => confirmDeleteColumn(column.id, column.name)}
                />
              ))}

              <div className="shrink-0 w-72 self-start">
                <Button
                  variant="ghost"
                  className="w-full border-2 border-dashed border-gray-300 text-gray-400 hover:border-primary hover:text-primary hover:bg-primary/5 transition-all"
                  onClick={() => setCreateColumnModalOpen(true)}
                >
                  <Plus size={18} />
                  Adicionar Coluna
                </Button>
              </div>
            </div>
          </SortableContext>
        </div>

        <DragOverlay>
          {activeTask && (
            <div className="w-72 opacity-95">
              <KanbanCard task={activeTask} isDragOverlay />
            </div>
          )}
          {activeColumnId && currentBoard && (
            <div className="shrink-0 w-72 opacity-90 rotate-2 scale-105">
              <div className="bg-white rounded-xl border-2 border-primary/40 shadow-xl px-3.5 py-3">
                <h3 className="font-semibold text-sm text-gray-800 truncate">
                  {currentBoard.columns.find(c => colSortableId(c.id) === activeColumnId)?.name}
                </h3>
              </div>
            </div>
          )}
        </DragOverlay>
      </DndContext>

      <CreateColumnModal
        open={createColumnModalOpen}
        onClose={() => setCreateColumnModalOpen(false)}
        onSubmit={handleAddColumn}
      />

      <EditColumnModal
        open={!!editingColumn}
        column={editingColumn}
        onClose={() => setEditingColumn(null)}
        onSubmit={handleEditColumn}
      />

      <ConfirmDialog
        open={!!confirmDialog}
        onClose={closeConfirm}
        onConfirm={confirmDialog?.onConfirm || (() => {})}
        title={confirmDialog?.title || ''}
        message={confirmDialog?.message || ''}
        confirmLabel={confirmDialog?.confirmLabel}
        variant={confirmDialog?.variant}
      />
    </div>
  );
}
