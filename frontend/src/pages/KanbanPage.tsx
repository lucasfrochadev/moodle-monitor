import { useEffect } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { KanbanBoard } from '../components/kanban/KanbanBoard';
import { useBoardStore } from '../store/boardStore';
import { Spinner } from '../components/ui/Spinner';

export default function KanbanPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const isQuadro = location.pathname === '/quadro';
  const { currentBoard, loadBoard, loadDefaultBoard, loading } = useBoardStore();

  useEffect(() => {
    if (isQuadro) loadDefaultBoard();
    else if (id) loadBoard(id);
  }, [id, isQuadro, loadBoard, loadDefaultBoard]);

  if (loading) return <Spinner size="lg" />;
  if (!currentBoard) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-400">Quadro não encontrado</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 lg:px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <span
            className="w-4 h-4 rounded-full"
            style={{ backgroundColor: currentBoard.color }}
          />
          <h2 className="text-lg font-bold text-gray-900">{currentBoard.name}</h2>
          {currentBoard.description && (
            <p className="text-sm text-gray-500 hidden sm:block">{currentBoard.description}</p>
          )}
        </div>
      </div>
      <KanbanBoard />
    </div>
  );
}
