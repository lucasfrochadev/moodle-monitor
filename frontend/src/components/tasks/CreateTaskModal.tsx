import { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { useUIStore } from '../../store/uiStore';
import { useBoardStore } from '../../store/boardStore';
import { useTaskStore } from '../../store/taskStore';
import { fetchDisciplines } from '../../api/other';
import type { Discipline } from '../../api/other';

const PRIORITY_OPTIONS = [
  { value: 0, label: 'Normal' },
  { value: 1, label: 'Média' },
  { value: 2, label: 'Alta' },
  { value: 3, label: 'Urgente' },
];

export function CreateTaskModal() {
  const { createTaskBoardId, createTaskColumnId, closeCreateTask } = useUIStore();
  const { loadBoard, currentBoard } = useBoardStore();
  const { createTask } = useTaskStore();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState(0);
  const [discipline, setDiscipline] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [disciplines, setDisciplines] = useState<Discipline[]>([]);

  useEffect(() => {
    fetchDisciplines().then(setDisciplines).catch(() => {});
  }, []);

  if (!createTaskBoardId || !createTaskColumnId) return null;

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!title.trim()) errs.title = 'Título é obrigatório';
    if (title.length > 200) errs.title = 'Título muito longo (máx. 200 caracteres)';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setSaving(true);
    try {
      await createTask(createTaskBoardId, {
        title: title.trim(),
        description: description.trim(),
        column_id: createTaskColumnId,
        priority: priority as any,
        discipline: discipline.trim(),
        due_date: dueDate || null,
        status: 'pending',
      } as any);
      loadBoard(createTaskBoardId);
      closeCreateTask();
      setTitle('');
      setDescription('');
      setPriority(0);
      setDiscipline('');
      setDueDate('');
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const columnName = currentBoard?.columns.find(c => c.id === createTaskColumnId)?.name || '';

  return (
    <Modal open={!!createTaskBoardId} onClose={closeCreateTask} title="Nova Tarefa" size="md">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            Título <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => { setTitle(e.target.value); setErrors(prev => ({ ...prev, title: '' })); }}
            placeholder="Digite o título da tarefa"
            className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all ${errors.title ? 'border-red-300 bg-red-50' : 'border-gray-200'}`}
            autoFocus
          />
          {errors.title && <p className="text-xs text-red-500 mt-1">{errors.title}</p>}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Descrição</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Adicione uma descrição (opcional)"
            rows={3}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Prioridade</label>
            <select
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
            >
              {PRIORITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Disciplina</label>
            <select
              value={discipline}
              onChange={(e) => setDiscipline(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
            >
              <option value="">Sem disciplina</option>
              {disciplines.map((d) => (
                <option key={d.id} value={d.name}>{d.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Prazo</label>
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
          />
        </div>

        <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg text-xs text-gray-500">
          <span className="font-medium">Coluna:</span> {columnName || createTaskColumnId}
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-gray-100">
          <Button variant="ghost" size="sm" onClick={closeCreateTask}>Cancelar</Button>
          <Button variant="primary" size="sm" onClick={handleSubmit} loading={saving}>
            Criar Tarefa
          </Button>
        </div>
      </div>
    </Modal>
  );
}
