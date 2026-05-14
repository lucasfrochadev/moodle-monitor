import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { TaskModal } from './components/tasks/TaskModal';
import { CreateTaskModal } from './components/tasks/CreateTaskModal';
import { ToastContainer } from './components/ui/Toast';
import { ConnectionCheck } from './pages/NotFoundPage';
import DashboardPage from './pages/DashboardPage';
import ActivitiesPage from './pages/ActivitiesPage';
import KanbanPage from './pages/KanbanPage';
import CalendarPage from './pages/CalendarPage';
import DisciplinesPage from './pages/DisciplinesPage';
import SettingsPage from './pages/SettingsPage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/atividades" element={<ActivitiesPage />} />
          <Route path="/board/:id" element={<KanbanPage />} />
          <Route path="/calendario" element={<CalendarPage />} />
          <Route path="/disciplinas" element={<DisciplinesPage />} />
          <Route path="/configuracoes" element={<SettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
      <TaskModal />
      <CreateTaskModal />
      <ToastContainer />
      <ConnectionCheck />
    </BrowserRouter>
  );
}
