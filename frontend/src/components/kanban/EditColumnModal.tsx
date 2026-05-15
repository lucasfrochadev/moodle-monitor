import { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type { ColumnWithTasks } from '../../types';

const COLUMN_COLORS = [
  { name: 'Amarelo', value: '#F59E0B' },
  { name: 'Azul', value: '#4A90D9' },
  { name: 'Roxo', value: '#8B5CF6' },
  { name: 'Verde', value: '#10B981' },
  { name: 'Vermelho', value: '#EF4444' },
  { name: 'Rosa', value: '#EC4899' },
  { name: 'Cinza', value: '#6B7280' },
  { name: 'Laranja', value: '#F97316' },
];

interface EditColumnModalProps {
  open: boolean;
  column: ColumnWithTasks | null;
  onClose: () => void;
  onSubmit: (name: string, color?: string) => Promise<void>;
}

export function EditColumnModal({ open, column, onClose, onSubmit }: EditColumnModalProps) {
  const [name, setName] = useState('');
  const [color, setColor] = useState(COLUMN_COLORS[1].value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (column) {
      setName(column.name);
      setColor(column.color || COLUMN_COLORS[1].value);
      setError('');
    }
  }, [column]);

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Nome é obrigatório');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onSubmit(name.trim(), color);
      onClose();
    } catch {
      setError('Erro ao salvar coluna');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Editar Coluna" size="sm">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            Nome da coluna <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); setError(''); }}
            placeholder="Ex: Em andamento"
            className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all ${error ? 'border-red-300 bg-red-50' : 'border-gray-200'}`}
            autoFocus
          />
          {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Cor</label>
          <div className="flex gap-2">
            {COLUMN_COLORS.map((c) => (
              <button
                key={c.value}
                onClick={() => setColor(c.value)}
                className={`w-8 h-8 rounded-full border-2 transition-all cursor-pointer ${color === c.value ? 'border-gray-900 scale-110 ring-2 ring-offset-1 ring-gray-300' : 'border-transparent hover:scale-105'}`}
                style={{ backgroundColor: c.value }}
                title={c.name}
              />
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-gray-100">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button variant="primary" size="sm" onClick={handleSubmit} loading={saving}>Salvar</Button>
        </div>
      </div>
    </Modal>
  );
}
