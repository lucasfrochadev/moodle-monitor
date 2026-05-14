import { format, formatDistanceToNow, isPast, isToday, isTomorrow, parseISO, differenceInDays } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const date = parseISO(dateStr);
    return format(date, "dd/MM/yyyy 'às' HH:mm", { locale: ptBR });
  } catch {
    return dateStr;
  }
}

export function formatDateShort(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const date = parseISO(dateStr);
    if (isToday(date)) return `Hoje, ${format(date, 'HH:mm')}`;
    if (isTomorrow(date)) return `Amanhã, ${format(date, 'HH:mm')}`;
    return format(date, "dd/MM", { locale: ptBR });
  } catch {
    return dateStr;
  }
}

export function daysUntil(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  try {
    const date = parseISO(dateStr);
    return differenceInDays(date, new Date());
  } catch {
    return null;
  }
}

export function isOverdue(dateStr: string | null | undefined): boolean {
  if (!dateStr) return false;
  try {
    return isPast(parseISO(dateStr));
  } catch {
    return false;
  }
}

export function relativeDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    return formatDistanceToNow(parseISO(dateStr), {
      addSuffix: true,
      locale: ptBR,
    });
  } catch {
    return dateStr;
  }
}

export function formatDateRange(startDate: string | null | undefined, endDate: string | null | undefined): string {
  if (!startDate && !endDate) return '—';
  if (startDate && !endDate) return `Desde ${formatDateShort(startDate)}`;
  if (!startDate && endDate) return `Até ${formatDateShort(endDate)}`;
  return `${formatDateShort(startDate)} — ${formatDateShort(endDate)}`;
}
