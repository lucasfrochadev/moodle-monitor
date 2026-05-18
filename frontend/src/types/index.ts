export interface Board {
  id: string;
  name: string;
  description: string;
  color: string;
  created_at: string;
  updated_at: string;
}

export interface Column {
  id: string;
  board_id: string;
  name: string;
  position: number;
  color: string;
  created_at: string;
}

export interface Task {
  id: string;
  column_id: string | null;
  board_id: string;
  title: string;
  description: string;
  discipline: string;
  due_date: string | null;
  publication_date: string | null;
  status: string;
  priority: number;
  position: number;
  progress: number;
  activity_url: string;
  archived: boolean;
  created_at: string;
  updated_at: string;
  source_course_name: string;
  source_activity_id: string;
  assignee?: string;
  tags?: string[];
}

export interface ColumnWithTasks extends Column {
  tasks: Task[];
}

export interface BoardFull extends Board {
  columns: ColumnWithTasks[];
}

export interface DashboardStats {
  total_tasks: number;
  pending: number;
  in_progress: number;
  completed: number;
  overdue: number;
  archived: number;
  due_this_week: number;
  total_boards: number;
  total_activities_imported: number;
}

export interface VigentActivity {
  id: string;
  title: string;
  description: string;
  discipline: string;
  due_date: string | null;
  publication_date: string | null;
  status: string;
  priority: number;
  activity_url: string;
  source_course_name: string;
  days_until_due: number | null;
  is_overdue: boolean;
}

export interface CalendarEvent {
  id: string;
  title: string;
  event_date: string;
  event_time: string;
  event_type: string;
  description: string;
  color: string;
  created_at: string;
  updated_at: string;
}

export interface CalendarBoardTask {
  id: string;
  title: string;
  discipline: string;
  due_date: string;
  priority: number;
  status: string;
  column_id: string;
  board_id: string;
}

export const EVENT_TYPE_LABELS: Record<string, string> = {
  exam: 'Prova',
  appointment: 'Compromisso',
  study: 'Estudo',
  other: 'Outro',
};

export const EVENT_TYPE_COLORS: Record<string, string> = {
  exam: '#EF4444',
  appointment: '#F59E0B',
  study: '#3B82F6',
  other: '#8B5CF6',
};

export interface SyncResult {
  imported: number;
  updated: number;
  errors: number;
  message: string;
}

export interface TaskHistory {
  id: string;
  task_id: string;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  changed_by: string;
  created_at: string;
}

export type Priority = 0 | 1 | 2 | 3;
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'overdue' | 'archived';

export const PRIORITY_LABELS: Record<Priority, string> = {
  0: 'Normal',
  1: 'Média',
  2: 'Alta',
  3: 'Urgente',
};

export const PRIORITY_COLORS: Record<Priority, string> = {
  0: 'bg-gray-100 text-gray-700',
  1: 'bg-blue-100 text-blue-700',
  2: 'bg-orange-100 text-orange-700',
  3: 'bg-red-100 text-red-700',
};

export const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  in_progress: 'Em Andamento',
  completed: 'Concluída',
  overdue: 'Atrasada',
  archived: 'Arquivada',
};

export const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  overdue: 'bg-red-100 text-red-800',
  archived: 'bg-gray-100 text-gray-600',
};
