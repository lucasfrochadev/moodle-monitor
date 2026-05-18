import { useState, useEffect } from 'react';
import {
  Clock,
  AlertTriangle,
  BookOpen,
  Link,
  History,
  Save,
  Trash2,
} from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Spinner } from '../ui/Spinner';
import { useTaskStore } from '../../store/taskStore';
import { useUIStore } from '../../store/uiStore';
import { useBoardStore } from '../../store/boardStore';
import { fetchTaskHistory, fetchDisciplines } from '../../api/other';
import type { Discipline } from '../../api/other';
import { formatDate, formatDateShort, isOverdue } from '../../utils/date';
import type { Task, TaskHistory as TaskHistoryType } from '../../types';
import { PRIORITY_LABELS, STATUS_LABELS, STATUS_COLORS } from '../../types';

export function TaskModal() {
  const { taskModalId, taskModalBoardId, closeTaskModal } = useUIStore();
  const { updateTask, deleteTask } = useTaskStore();
  const { loadBoard } = useBoardStore();

  const [task, setTask] = useState<Task | null>(null);
  const [history, setHistory] = useState<TaskHistoryType[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<'details' | 'history'>('details');

  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editStatus, setEditStatus] = useState('');
  const [editPriority, setEditPriority] = useState(0);
  const [editDiscipline, setEditDiscipline] = useState('');
  const [disciplines, setDisciplines] = useState<Discipline[]>([]);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (!taskModalId || !taskModalBoardId) return;
    setLoading(true);

    const load = async () => {
      try {
        const res = await fetch(`/api/boards/${taskModalBoardId}/tasks/${taskModalId}`);
        const data = await res.json();
        setTask(data);
        setEditTitle(data.title);
        setEditDescription(data.description || '');
        setEditStatus(data.status);
        setEditPriority(data.priority);
        setEditDiscipline(data.discipline || '');
        setHasChanges(false);

        const [hist, disciplines] = await Promise.all([
          fetchTaskHistory(taskModalId),
          fetchDisciplines().catch(() => [] as Discipline[]),
        ]);
        setHistory(hist);
        setDisciplines(disciplines);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [taskModalId, taskModalBoardId]);

  if (!taskModalId || !taskModalBoardId) return null;

  const handleSave = async () => {
    if (!task || !taskModalBoardId) return;
    setSaving(true);
    try {
      await updateTask(taskModalBoardId, task.id, {
        title: editTitle,
        description: editDescription,
        status: editStatus,
        priority: editPriority,
        discipline: editDiscipline,
      });
      setTask((prev) =>
        prev
          ? { ...prev, title: editTitle, description: editDescription, status: editStatus, priority: editPriority, discipline: editDiscipline }
          : prev
      );
      setHasChanges(false);
      loadBoard(taskModalBoardId);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!task || !taskModalBoardId) return;
    if (!confirm('Tem certeza que deseja excluir esta tarefa?')) return;
    await deleteTask(taskModalBoardId, task.id);
    closeTaskModal();
  };

  const overdue = task && isOverdue(task.due_date) && task.status !== 'completed';

  return (
    <Modal
      open={!!taskModalId}
      onClose={closeTaskModal}
      title="Detalhes da Tarefa"
      size="lg"
    >
      {loading ? (
        <Spinner />
      ) : !task ? (
        <p className="text-gray-400">Tarefa não encontrada</p>
      ) : (
        <div className="space-y-6">
          {/* Campos editáveis */}
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Título</label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => { setEditTitle(e.target.value); setHasChanges(true); }}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Descrição</label>
              <textarea
                value={editDescription}
                onChange={(e) => { setEditDescription(e.target.value); setHasChanges(true); }}
                rows={4}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => { setEditStatus(e.target.value); setHasChanges(true); }}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                >
                  {Object.entries(STATUS_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Prioridade</label>
                <select
                  value={editPriority}
                  onChange={(e) => { setEditPriority(Number(e.target.value)); setHasChanges(true); }}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                >
                  {Object.entries(PRIORITY_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Disciplina</label>
              <select
                value={editDiscipline}
                onChange={(e) => { setEditDiscipline(e.target.value); setHasChanges(true); }}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              >
                <option value="">Sem disciplina</option>
                {disciplines.map((d) => (
                  <option key={d.id} value={d.name}>{d.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Info não editável */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            {task.discipline && (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <BookOpen size={16} className="text-gray-400" />
                <span>{task.discipline}</span>
              </div>
            )}
            {task.due_date && (
              <div className={`flex items-center gap-2 text-sm ${overdue ? 'text-overdue' : 'text-gray-600'}`}>
                {overdue ? <AlertTriangle size={16} /> : <Clock size={16} />}
                <span>
                  Prazo: {formatDate(task.due_date)}
                  {overdue && ' (Atrasada)'}
                </span>
              </div>
            )}
            {task.activity_url && (
              <div className="flex items-center gap-2 text-sm">
                <Link size={16} className="text-gray-400" />
                <a
                  href={task.activity_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline truncate"
                >
                  {task.activity_url}
                </a>
              </div>
            )}
            <div className="flex items-center gap-2">
              <Badge className={STATUS_COLORS[task.status] || ''}>
                {STATUS_LABELS[task.status] || task.status}
              </Badge>
              {task.source_course_name && (
                <Badge variant="info">{task.source_course_name}</Badge>
              )}
            </div>
          </div>

          {/* Ações */}
          <div className="flex items-center justify-between pt-2">
            <Button variant="danger" size="sm" onClick={handleDelete}>
              <Trash2 size={16} />
              Excluir
            </Button>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={closeTaskModal}>
                Cancelar
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSave}
                loading={saving}
                disabled={!hasChanges}
              >
                <Save size={16} />
                Salvar
              </Button>
            </div>
          </div>

          {/* Histórico */}
          <div>
            <button
              onClick={() => setTab(tab === 'history' ? 'details' : 'history')}
              className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 cursor-pointer"
            >
              <History size={16} />
              Histórico de alterações ({history.length})
            </button>

            {tab === 'history' && history.length > 0 && (
              <div className="mt-3 space-y-2 max-h-48 overflow-y-auto">
                {history.map((h) => (
                  <div key={h.id} className="text-xs text-gray-500 bg-gray-50 rounded p-2">
                    <span className="font-medium text-gray-700">{h.field_name}:</span>{' '}
                    <span className="line-through text-gray-400">{h.old_value || '(vazio)'}</span>
                    {' → '}
                    <span className="text-gray-600">{h.new_value}</span>
                    <span className="ml-2 text-gray-300">{formatDateShort(h.created_at)}</span>
                  </div>
                ))}
              </div>
            )}
            {tab === 'history' && history.length === 0 && (
              <p className="text-xs text-gray-400 mt-2">Nenhuma alteração registrada.</p>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
