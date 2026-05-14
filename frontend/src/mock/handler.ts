import type { Task } from '../types';
import { MOCK_BOARDS, MOCK_COLUMNS, MOCK_DASHBOARD_STATS, MOCK_TASKS, MOCK_VIGENT_ACTIVITIES, getMockBoardFull } from './data';

export function handleMockRequest(method: string, url?: string, data?: any): { data: any } | null {
  if (!url) return null;
  const baseUrl = url.replace(/^\/api/, '');
  const segments = baseUrl.split('/').filter(Boolean);

  if (baseUrl === '/boards' && method === 'GET') {
    return { data: MOCK_BOARDS };
  }

  if (segments[0] === 'boards' && segments.length === 2 && method === 'GET') {
    const board = getMockBoardFull(segments[1]);
    return board ? { data: board } : null;
  }

  if (segments[0] === 'boards' && segments.length === 2 && method === 'DELETE') {
    return { data: { deleted: true } };
  }

  if (segments[0] === 'boards' && segments.length === 2 && method === 'PUT') {
    const board = MOCK_BOARDS.find(b => b.id === segments[1]);
    return board ? { data: { ...board, ...data } } : null;
  }

  if (segments[0] === 'boards' && segments.length === 2 && method === 'POST') {
    const newBoard = {
      id: `board-${Date.now()}`,
      name: data?.name || 'Novo Quadro',
      description: data?.description || '',
      color: data?.color || '#4A90D9',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    return { data: newBoard };
  }

  const boardIdMatch = baseUrl.match(/^\/boards\/([^/]+)\/(.+)/);
  if (boardIdMatch) {
    const [, bid, action] = boardIdMatch;

    if (action === 'columns' && method === 'GET') {
      return { data: MOCK_COLUMNS.filter(c => c.board_id === bid) };
    }

    if (action === 'columns' && method === 'POST') {
      return {
        data: {
          id: `col-${Date.now()}`,
          board_id: bid,
          name: data?.name || 'Nova Coluna',
          position: MOCK_COLUMNS.length,
          color: data?.color || '#636E72',
          created_at: new Date().toISOString(),
        },
      };
    }

    const colSegments = action.split('/');
    if (colSegments[0] === 'columns' && colSegments.length >= 2) {
      const colId = colSegments[1];
      const subAction = colSegments[2];

      if (subAction === 'reorder' && method === 'PUT') {
        return { data: { success: true } };
      }

      if (!subAction && method === 'DELETE') {
        return { data: { deleted: true } };
      }

      if (!subAction && method === 'PUT') {
        const col = MOCK_COLUMNS.find(c => c.id === colId);
        return col ? { data: { ...col, ...data } } : null;
      }

      if (method === 'GET') {
        const col = MOCK_COLUMNS.find(c => c.id === colId);
        return col ? { data: col } : null;
      }

      return { data: { success: true } };
    }

    if (action === 'tasks' && method === 'GET') {
      const allTasks: Task[] = Object.values(MOCK_TASKS).flat();
      return { data: allTasks.filter(t => t.board_id === bid) };
    }

    if (action.startsWith('tasks/') && action.endsWith('/move') && method === 'PUT') {
      return { data: { ...MOCK_TASKS['col-pend-1']?.[0], column_id: data?.column_id, position: data?.position } };
    }

    if (action === 'tasks/reorder' && method === 'PUT') {
      return { data: { success: true } };
    }

    if (action.startsWith('tasks/') && method === 'DELETE') {
      return { data: { deleted: true } };
    }

    if (action.startsWith('tasks/') && method === 'GET') {
      const taskId = action.split('/')[1];
      const allTasks: Task[] = Object.values(MOCK_TASKS).flat();
      const task = allTasks.find(t => t.id === taskId);
      return task ? { data: task } : null;
    }

    if (action.startsWith('tasks/') && method === 'PUT') {
      const taskId = action.split('/')[1];
      const allTasks: Task[] = Object.values(MOCK_TASKS).flat();
      const task = allTasks.find(t => t.id === taskId);
      return task ? { data: { ...task, ...data } } : null;
    }

    if (action === 'tasks' && method === 'POST') {
      return {
        data: {
          id: `task-${Date.now()}`,
          column_id: data?.column_id,
          board_id: bid,
          title: data?.title || 'Nova Tarefa',
          description: data?.description || '',
          discipline: data?.discipline || '',
          due_date: data?.due_date || null,
          publication_date: new Date().toISOString(),
          status: data?.status || 'pending',
          priority: data?.priority || 0,
          position: 0,
          progress: 0,
          activity_url: '',
          archived: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          source_course_name: '',
          source_activity_id: '',
          assignee: 'João Silva',
        },
      };
    }

    return null;
  }

  if (baseUrl === '/activities/vigent' && method === 'GET') {
    return { data: MOCK_VIGENT_ACTIVITIES };
  }

  if (baseUrl === '/activities/imported' && method === 'GET') {
    return { data: MOCK_VIGENT_ACTIVITIES.slice(0, 3) };
  }

  if (baseUrl === '/dashboard' && method === 'GET') {
    return { data: MOCK_DASHBOARD_STATS };
  }

  if (baseUrl === '/sync' && method === 'POST') {
    return { data: { imported: 2, updated: 0, errors: 0, message: 'Sincronização concluída com sucesso!' } };
  }

  if (baseUrl === '/sync/status' && method === 'GET') {
    return { data: { monitor_db_exists: true, study_db_exists: true } };
  }

  if (baseUrl?.startsWith('/history/') && method === 'GET') {
    return { data: [] };
  }

  if (baseUrl === '/health' && method === 'GET') {
    return { data: { status: 'ok' } };
  }

  return null;
}
