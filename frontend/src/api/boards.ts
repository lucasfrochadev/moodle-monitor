import client from './client';
import type { Board, BoardFull } from '../types';

export async function fetchBoards(): Promise<Board[]> {
  const { data } = await client.get('/boards');
  return data;
}

export async function fetchDefaultBoard(): Promise<BoardFull> {
  const { data } = await client.get('/boards/default');
  return data;
}

export async function fetchBoard(id: string): Promise<BoardFull> {
  const { data } = await client.get(`/boards/${id}`);
  return data;
}

export async function createBoard(body: { name: string; description?: string; color?: string }): Promise<Board> {
  const { data } = await client.post('/boards', body);
  return data;
}

export async function updateBoard(id: string, body: Partial<Board>): Promise<Board> {
  const { data } = await client.put(`/boards/${id}`, body);
  return data;
}

export async function deleteBoard(id: string): Promise<void> {
  await client.delete(`/boards/${id}`);
}
