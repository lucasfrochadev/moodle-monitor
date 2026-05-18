import client from './client';
import type { CalendarEvent, CalendarBoardTask } from '../types';

export async function fetchEvents(month?: string): Promise<CalendarEvent[]> {
  const params: any = {};
  if (month) params.month = month;
  const { data } = await client.get('/calendar/events', { params });
  return data;
}

export async function createEvent(body: {
  title: string;
  event_date: string;
  event_time?: string;
  event_type?: string;
  description?: string;
  color?: string;
}): Promise<CalendarEvent> {
  const { data } = await client.post('/calendar/events', body);
  return data;
}

export async function updateEvent(id: string, body: Partial<CalendarEvent>): Promise<CalendarEvent> {
  const { data } = await client.put(`/calendar/events/${id}`, body);
  return data;
}

export async function deleteEvent(id: string): Promise<void> {
  await client.delete(`/calendar/events/${id}`);
}

export async function fetchBoardTasks(): Promise<CalendarBoardTask[]> {
  const { data } = await client.get('/calendar/board-tasks');
  return data;
}
