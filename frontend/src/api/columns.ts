import client from './client';
import type { Column } from '../types';

export async function fetchColumns(boardId: string): Promise<Column[]> {
  const { data } = await client.get(`/boards/${boardId}/columns`);
  return data;
}

export async function createColumn(boardId: string, body: { name: string; color?: string; position?: number }): Promise<Column> {
  const { data } = await client.post(`/boards/${boardId}/columns`, body);
  return data;
}

export async function updateColumn(boardId: string, columnId: string, body: Partial<Column>): Promise<Column> {
  const { data } = await client.put(`/boards/${boardId}/columns/${columnId}`, body);
  return data;
}

export async function deleteColumn(boardId: string, columnId: string): Promise<void> {
  await client.delete(`/boards/${boardId}/columns/${columnId}`);
}

export async function reorderColumns(boardId: string, items: { id: string; position: number }[]): Promise<void> {
  await client.put(`/boards/${boardId}/columns/reorder`, { items });
}
