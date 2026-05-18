import client from './client';
import type { Task } from '../types';

export async function fetchTasks(boardId: string, params?: { column_id?: string; status?: string; discipline?: string }): Promise<Task[]> {
  const { data } = await client.get(`/boards/${boardId}/tasks`, { params });
  return data;
}

export async function fetchTask(boardId: string, taskId: string): Promise<Task> {
  const { data } = await client.get(`/boards/${boardId}/tasks/${taskId}`);
  return data;
}

export async function createTask(boardId: string, body: Partial<Task> & { title: string }): Promise<Task> {
  const { data } = await client.post(`/boards/${boardId}/tasks`, body);
  return data;
}

export async function updateTask(boardId: string, taskId: string, body: Partial<Task>): Promise<Task> {
  const { data } = await client.put(`/boards/${boardId}/tasks/${taskId}`, body);
  return data;
}

export async function moveTask(boardId: string, taskId: string, columnId: string, position?: number): Promise<Task> {
  const { data } = await client.put(`/boards/${boardId}/tasks/${taskId}/move`, { column_id: columnId, position });
  return data;
}

export async function reorderTasks(boardId: string, items: { id: string; position: number }[]): Promise<void> {
  await client.put(`/boards/${boardId}/tasks/reorder`, { items });
}

export async function deleteTask(boardId: string, taskId: string): Promise<void> {
  await client.delete(`/boards/${boardId}/tasks/${taskId}`);
}

export async function fetchVigentActivities(params?: {
  disciplina?: string;
  status?: string;
  due_date_before?: string;
  due_date_after?: string;
}): Promise<Task[]> {
  const { data } = await client.get('/activities/vigent', { params });
  return data;
}

export async function fetchImportedActivities(limit?: number): Promise<Task[]> {
  const { data } = await client.get('/activities/imported', { params: { limit } });
  return data;
}
