import client from './client';
import type { DashboardStats, SyncResult } from '../types';

export async function fetchDashboard(): Promise<DashboardStats> {
  const { data } = await client.get('/dashboard');
  return data;
}

export async function triggerSync(): Promise<SyncResult> {
  const { data } = await client.post('/sync');
  return data;
}

export async function fetchSyncStatus(): Promise<{ monitor_db_exists: boolean; study_db_exists: boolean }> {
  const { data } = await client.get('/sync/status');
  return data;
}

export async function fetchTaskHistory(taskId: string, limit?: number): Promise<any[]> {
  const { data } = await client.get(`/history/${taskId}`, { params: { limit } });
  return data;
}
