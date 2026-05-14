import { create } from 'zustand';

interface UIState {
  sidebarOpen: boolean;
  taskModalId: string | null;
  taskModalBoardId: string | null;
  createTaskColumnId: string | null;
  createTaskBoardId: string | null;
  createBoardModalOpen: boolean;
  createColumnModalOpen: boolean;
  confirmDialog: { open: boolean; title: string; message: string; onConfirm: () => void; variant?: 'danger' | 'primary'; confirmLabel?: string } | null;

  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  openTaskModal: (taskId: string, boardId: string) => void;
  closeTaskModal: () => void;
  openCreateTask: (boardId: string, columnId: string) => void;
  closeCreateTask: () => void;
  setCreateBoardModalOpen: (open: boolean) => void;
  setCreateColumnModalOpen: (open: boolean) => void;
  showConfirm: (params: { title: string; message: string; onConfirm: () => void; variant?: 'danger' | 'primary'; confirmLabel?: string }) => void;
  closeConfirm: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  taskModalId: null,
  taskModalBoardId: null,
  createTaskColumnId: null,
  createTaskBoardId: null,
  createBoardModalOpen: false,
  createColumnModalOpen: false,
  confirmDialog: null,

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  openTaskModal: (taskId, boardId) => set({ taskModalId: taskId, taskModalBoardId: boardId }),
  closeTaskModal: () => set({ taskModalId: null, taskModalBoardId: null }),

  openCreateTask: (boardId, columnId) => set({ createTaskBoardId: boardId, createTaskColumnId: columnId }),
  closeCreateTask: () => set({ createTaskBoardId: null, createTaskColumnId: null }),

  setCreateBoardModalOpen: (open) => set({ createBoardModalOpen: open }),
  setCreateColumnModalOpen: (open) => set({ createColumnModalOpen: open }),

  showConfirm: (params) => set({ confirmDialog: { ...params, open: true } }),
  closeConfirm: () => set({ confirmDialog: null }),
}));
