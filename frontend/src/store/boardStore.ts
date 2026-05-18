import { create } from 'zustand';
import type { Board, BoardFull, ColumnWithTasks } from '../types';
import * as boardsApi from '../api/boards';
import * as columnsApi from '../api/columns';

interface BoardState {
  boards: Board[];
  currentBoard: BoardFull | null;
  loading: boolean;
  error: string | null;

  loadBoards: () => Promise<void>;
  loadBoard: (id: string) => Promise<void>;
  loadDefaultBoard: () => Promise<void>;
  createBoard: (name: string, description?: string, color?: string) => Promise<Board>;
  updateBoard: (id: string, data: Partial<Board>) => Promise<void>;
  deleteBoard: (id: string) => Promise<void>;

  addColumn: (name: string, color?: string) => Promise<void>;
  updateColumn: (columnId: string, data: Partial<ColumnWithTasks>) => Promise<void>;
  deleteColumn: (columnId: string) => Promise<void>;
  reorderColumns: (items: { id: string; position: number }[]) => Promise<void>;
}

export const useBoardStore = create<BoardState>((set, get) => ({
  boards: [],
  currentBoard: null,
  loading: false,
  error: null,

  loadBoards: async () => {
    set({ loading: true, error: null });
    try {
      const boards = await boardsApi.fetchBoards();
      set({ boards, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  loadDefaultBoard: async () => {
    set({ loading: true, error: null });
    try {
      const board = await boardsApi.fetchDefaultBoard();
      set({ currentBoard: board, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  loadBoard: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const board = await boardsApi.fetchBoard(id);
      set({ currentBoard: board, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  createBoard: async (name, description, color) => {
    const board = await boardsApi.createBoard({ name, description, color });
    set((s) => ({ boards: [...s.boards, board] }));
    return board;
  },

  updateBoard: async (id, data) => {
    await boardsApi.updateBoard(id, data);
    set((s) => ({
      boards: s.boards.map((b) => (b.id === id ? { ...b, ...data } : b)),
      currentBoard: s.currentBoard?.id === id ? { ...s.currentBoard, ...data } : s.currentBoard,
    }));
  },

  deleteBoard: async (id) => {
    await boardsApi.deleteBoard(id);
    set((s) => ({
      boards: s.boards.filter((b) => b.id !== id),
      currentBoard: s.currentBoard?.id === id ? null : s.currentBoard,
    }));
  },

  addColumn: async (name, color) => {
    const board = get().currentBoard;
    if (!board) return;
    const col = await columnsApi.createColumn(board.id, { name, color });
    set((s) => {
      if (!s.currentBoard || s.currentBoard.id !== board.id) return s;
      return {
        currentBoard: {
          ...s.currentBoard,
          columns: [...s.currentBoard.columns, { ...col, tasks: [] }],
        },
      };
    });
  },

  updateColumn: async (columnId, data) => {
    const board = get().currentBoard;
    if (!board) return;
    await columnsApi.updateColumn(board.id, columnId, data);
    set((s) => ({
      currentBoard: s.currentBoard
        ? {
            ...s.currentBoard,
            columns: s.currentBoard.columns.map((c) =>
              c.id === columnId ? { ...c, ...data } : c
            ),
          }
        : null,
    }));
  },

  deleteColumn: async (columnId) => {
    const board = get().currentBoard;
    if (!board) return;
    await columnsApi.deleteColumn(board.id, columnId);
    set((s) => ({
      currentBoard: s.currentBoard
        ? {
            ...s.currentBoard,
            columns: s.currentBoard.columns.filter((c) => c.id !== columnId),
          }
        : null,
    }));
  },

  reorderColumns: async (items) => {
    const board = get().currentBoard;
    if (!board) return;
    await columnsApi.reorderColumns(board.id, items);
    set((s) => {
      if (!s.currentBoard) return s;
      const itemMap = new Map(items.map((i) => [i.id, i.position]));
      return {
        currentBoard: {
          ...s.currentBoard,
          columns: [...s.currentBoard.columns]
            .sort((a, b) => (itemMap.get(a.id) ?? a.position) - (itemMap.get(b.id) ?? b.position)),
        },
      };
    });
  },
}));
