import { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';

const BOARD_COLORS = [
  { name: 'Azul', value: '#4A90D9' },
  { name: 'Roxo', value: '#6C5CE7' },
  { name: 'Verde', value: '#00B894' },
  { name: 'Vermelho', value: '#E17055' },
  { name: 'Amarelo', value: '#FDCB6E' },
  { name: 'Rosa', value: '#fd79a8' },
  { name: 'Teal', value: '#00CEC9' },
  { name: 'Cinza', value: '#636E72' },
];

interface CreateBoardModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (name: string, description?: string, color?: string) => Promise<void>;
}

export function CreateBoardModal({ open, onClose, onSubmit }: CreateBoardModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState(BOARD_COLORS[0].value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Nome é obrigatório');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onSubmit(name.trim(), description.trim() || undefined, color);
      setName('');
      setDescription('');
      setColor(BOARD_COLORS[0].value);
      onClose();
    } catch (e) {
      setError('Erro ao criar quadro');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Novo Quadro" size="sm">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            Nome <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); setError(''); }}
            placeholder="Ex: Estudos de Matemática"
            className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all ${error ? 'border-red-300 bg-red-50' : 'border-gray-200 focus:border-primary'}`}
            autoFocus
          />
          {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Descrição (opcional)</label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Breve descrição do quadro"
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Cor</label>
          <div className="flex gap-2">
            {BOARD_COLORS.map((c) => (
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
          <Button variant="primary" size="sm" onClick={handleSubmit} loading={saving}>Criar Quadro</Button>
        </div>
      </div>
    </Modal>
  );
}
