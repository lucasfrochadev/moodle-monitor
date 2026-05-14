"""
Interface base para todos os notificadores.
Novos canais implementam esta interface.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.detector.comparator import ChangeType, DetectedChange, Severity


class Notifier(ABC):
    """Interface para envio de notificações."""

    @abstractmethod
    async def send(
        self,
        change: DetectedChange,
        activity_name: str,
        course_name: str,
        activity_url: str,
    ) -> bool:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    def _format_message(
        self,
        change: DetectedChange,
        activity_name: str,
        course_name: str,
        activity_url: str,
    ) -> str:
        emoji = self._get_emoji(change.change_type)
        severity_label = self._get_severity_label(change.severity)

        header = f"{emoji} *{self._get_change_label(change.change_type)}* [{severity_label}]"
        lines = [
            header,
            "",
            f"📚 Disciplina: {course_name}",
            f"📝 Atividade: {activity_name}",
            f"🔗 Link: {activity_url}",
            "",
        ]

        details = self._format_details(change)
        if details:
            lines.append(details)

        lines.append("")
        lines.append(f"🕐 Detectado: {change.detected_at.strftime('%d/%m/%Y %H:%M')}")

        return "\n".join(lines)

    def _format_details(self, change: DetectedChange) -> Optional[str]:
        if change.change_type == ChangeType.DEADLINE_CHANGE:
            return (
                f"📅 *Prazo anterior:* {change.old_value or 'não definido'}\n"
                f"📅 *Novo prazo:* {change.new_value or 'não definido'}"
            )
        if change.change_type == ChangeType.FILE_ADDED:
            return f"📎 *Novo arquivo:* {change.new_value or 'desconhecido'}"
        if change.change_type == ChangeType.FILE_REMOVED:
            return f"🗑️ *Arquivo removido:* {change.old_value or 'desconhecido'}"
        if change.change_type == ChangeType.DESCRIPTION_CHANGE:
            return "📝 *Descrição da atividade foi alterada*"
        if change.change_type == ChangeType.NAME_CHANGE:
            return (
                f"✏️ *Nome anterior:* {change.old_value}\n"
                f"✏️ *Novo nome:* {change.new_value}"
            )
        if change.change_type == ChangeType.GRADE_CHANGE:
            return (
                f"📊 *Nota anterior:* {change.old_value or 'N/A'}\n"
                f"📊 *Nova nota:* {change.new_value or 'N/A'}"
            )
        if change.change_type == ChangeType.NEW_ACTIVITY:
            return f"📋 *Nova atividade:* {change.new_value}"

        return None

    def _get_emoji(self, change_type: ChangeType) -> str:
        emoji_map = {
            ChangeType.NEW_ACTIVITY: "🆕",
            ChangeType.DEADLINE_CHANGE: "⚠️",
            ChangeType.DESCRIPTION_CHANGE: "📝",
            ChangeType.FILE_ADDED: "📎",
            ChangeType.FILE_REMOVED: "🗑️",
            ChangeType.GRADE_CHANGE: "📊",
            ChangeType.NAME_CHANGE: "✏️",
            ChangeType.OPEN_DATE_CHANGE: "🔓",
            ChangeType.CUTOFF_DATE_CHANGE: "🚫",
            ChangeType.SECTION_CHANGE: "📂",
        }
        return emoji_map.get(change_type, "🔔")

    def _get_change_label(self, change_type: ChangeType) -> str:
        label_map = {
            ChangeType.NEW_ACTIVITY: "Nova atividade detectada!",
            ChangeType.DEADLINE_CHANGE: "Prazo alterado!",
            ChangeType.DESCRIPTION_CHANGE: "Descrição alterada",
            ChangeType.FILE_ADDED: "Novo arquivo disponível",
            ChangeType.FILE_REMOVED: "Arquivo removido",
            ChangeType.GRADE_CHANGE: "Nota máxima alterada",
            ChangeType.NAME_CHANGE: "Nome da atividade alterado",
            ChangeType.OPEN_DATE_CHANGE: "Data de abertura alterada",
            ChangeType.CUTOFF_DATE_CHANGE: "Data de corte alterada",
            ChangeType.SECTION_CHANGE: "Seção alterada",
        }
        return label_map.get(change_type, "Mudança detectada")

    def _get_severity_label(self, severity: Severity) -> str:
        labels = {
            Severity.CRITICAL: "IMPORTANTE",
            Severity.WARNING: "ATENÇÃO",
            Severity.INFO: "INFO",
        }
        return labels.get(severity, "INFO")
