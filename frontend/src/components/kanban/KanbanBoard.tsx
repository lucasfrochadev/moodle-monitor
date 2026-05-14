import { useState } from 'react';
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
import { Plus } from 'lucide-react';
import { KanbanColumn } from './KanbanColumn';
import { KanbanCard } from './KanbanCard';
import { Button } from '../ui/Button';
import { CreateColumnModal } from './CreateColumnModal';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { useBoardStore } from '../../store/boardStore';
import { useTaskStore } from '../../store/taskStore';
import { useUIStore } from '../../store/uiStore';

export function KanbanBoard() {
  const { currentBoard, loadBoard, addColumn, deleteColumn } = useBoardStore();
  const { deleteTask, moveTask } = useTaskStore();
  const { openTaskModal, openCreateTask, setCreateColumnModalOpen, createColumnModalOpen, confirmDialog, showConfirm, closeConfirm } = useUIStore();
  const [activeTask, setActiveTask] = useState<any>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

  const boardId = currentBoard?.id;

  const handleDragStart = (event: DragStartEvent) => {
    const taskId = event.active.id as string;
    if (!currentBoard) return;
    for (const col of currentBoard.columns) {
      const task = col.tasks.find((t) => t.id === taskId);
      if (task) {
        setActiveTask(task);
        break;
      }
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveTask(null);
    const { active, over } = event;
    if (!over || !boardId) return;

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
          <div className="flex gap-4 h-full min-h-[calc(100vh-8rem)] p-4">
            {currentBoard.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                onAddTask={() => openCreateTask(currentBoard.id, column.id)}
                onTaskClick={(taskId) => openTaskModal(taskId, currentBoard.id)}
                onEditTask={handleEditTask}
                onDeleteTask={(taskId) => confirmDeleteTask(taskId)}
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
        </div>

        <DragOverlay>
          {activeTask && (
            <div className="w-72 opacity-95">
              <KanbanCard task={activeTask} isDragOverlay />
            </div>
          )}
        </DragOverlay>
      </DndContext>

      <CreateColumnModal
        open={createColumnModalOpen}
        onClose={() => setCreateColumnModalOpen(false)}
        onSubmit={handleAddColumn}
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
