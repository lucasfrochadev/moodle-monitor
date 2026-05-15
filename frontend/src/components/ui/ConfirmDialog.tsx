import { AlertTriangle, Info } from 'lucide-react';
import { Modal } from './Modal';
import { Button } from './Button';
import { cn } from '../../utils/cn';

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  variant?: 'danger' | 'primary';
  loading?: boolean;
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirmar',
  variant = 'danger',
  loading = false,
}: ConfirmDialogProps) {
  const iconConfig = {
    danger: { Icon: AlertTriangle, bg: 'bg-red-100', color: 'text-red-500' },
    primary: { Icon: Info, bg: 'bg-blue-100', color: 'text-blue-500' },
  };
  const { Icon, bg, color } = iconConfig[variant];

  return (
    <Modal open={open} onClose={onClose} title={title} size="sm">
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <div className={cn('w-10 h-10 rounded-full flex items-center justify-center shrink-0', bg)}>
            <Icon size={20} className={color} />
          </div>
          <p className="text-sm text-gray-600 leading-relaxed pt-1">{message}</p>
        </div>
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button variant={variant} size="sm" onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
