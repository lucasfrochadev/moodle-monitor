import { create } from 'zustand';
import type { Task } from '../types';
import * as tasksApi from '../api/tasks';

interface TaskState {
  tasks: Task[];
  vigentActivities: Task[];
  loading: boolean;
  error: string | null;

  loadTasks: (boardId: string, filters?: Record<string, string>) => Promise<void>;
  loadVigent: (filters?: Record<string, string>) => Promise<void>;
  createTask: (boardId: string, data: Partial<Task> & { title: string }) => Promise<Task>;
  updateTask: (boardId: string, taskId: string, data: Partial<Task>) => Promise<void>;
  moveTask: (boardId: string, taskId: string, columnId: string, position?: number) => Promise<void>;
  reorderTasks: (boardId: string, items: { id: string; position: number }[]) => Promise<void>;
  deleteTask: (boardId: string, taskId: string) => Promise<void>;
  clearTasks: () => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  vigentActivities: [],
  loading: false,
  error: null,

  loadTasks: async (boardId, filters) => {
    set({ loading: true, error: null });
    try {
      const tasks = await tasksApi.fetchTasks(boardId, filters as any);
      set({ tasks, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  loadVigent: async (filters) => {
    set({ loading: true, error: null });
    try {
      const data = await tasksApi.fetchVigentActivities(filters as any);
      set({ vigentActivities: data, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  createTask: async (boardId, data) => {
    const task = await tasksApi.createTask(boardId, data);
    set((s) => ({ tasks: [...s.tasks, task] }));
    return task;
  },

  updateTask: async (boardId, taskId, data) => {
    await tasksApi.updateTask(boardId, taskId, data);
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === taskId ? { ...t, ...data } : t)),
      vigentActivities: s.vigentActivities.map((t) =>
        t.id === taskId ? { ...t, ...data } : t
      ),
    }));
  },

  moveTask: async (boardId, taskId, columnId, position) => {
    const updated = await tasksApi.moveTask(boardId, taskId, columnId, position);
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === taskId ? updated : t)),
      vigentActivities: s.vigentActivities.map((t) =>
        t.id === taskId ? { ...t, ...updated } : t
      ),
    }));
  },

  reorderTasks: async (boardId, items) => {
    await tasksApi.reorderTasks(boardId, items);
    set((s) => ({
      tasks: s.tasks.map((t) => {
        const found = items.find((i) => i.id === t.id);
        return found ? { ...t, position: found.position } : t;
      }),
    }));
  },

  deleteTask: async (boardId, taskId) => {
    await tasksApi.deleteTask(boardId, taskId);
    set((s) => ({
      tasks: s.tasks.filter((t) => t.id !== taskId),
      vigentActivities: s.vigentActivities.filter((t) => t.id !== taskId),
    }));
  },

  clearTasks: () => set({ tasks: [], vigentActivities: [] }),
}));
