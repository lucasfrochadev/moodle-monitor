import type { Board, BoardFull, Column, ColumnWithTasks, Task, DashboardStats } from '../types';

const NOW = new Date();
const DAY = 86400000;

function daysFromNow(n: number): string {
  return new Date(NOW.getTime() + n * DAY).toISOString();
}
function daysAgo(n: number): string {
  return new Date(NOW.getTime() - n * DAY).toISOString();
}

export const MOCK_USER = {
  name: 'João Silva',
  email: 'joao.silva@email.com',
  avatar: null,
};

export const MOCK_BOARDS: Board[] = [
  { id: 'board-1', name: 'Estudos de Matemática', description: 'Disciplinas do semestre 2026.1', color: '#4A90D9', created_at: daysAgo(30), updated_at: daysAgo(1) },
  { id: 'board-2', name: 'Projetos de Programação', description: 'Trabalhos e projetos práticos', color: '#6C5CE7', created_at: daysAgo(25), updated_at: daysAgo(2) },
  { id: 'board-3', name: 'TCC - Planejamento', description: 'Etapas do Trabalho de Conclusão', color: '#00B894', created_at: daysAgo(20), updated_at: daysAgo(3) },
  { id: 'board-4', name: 'Leituras e Resenhas', description: 'Livros e artigos para ler', color: '#E17055', created_at: daysAgo(15), updated_at: daysAgo(4) },
];

export const MOCK_TASKS: Record<string, Task[]> = {
  'col-pend-1': [
    { id: 'task-1', column_id: 'col-pend-1', board_id: 'board-1', title: 'Resolver lista de exercícios - Capítulo 5', description: 'Exercícios 1 a 20 sobre derivadas parciais', discipline: 'Cálculo II', due_date: daysFromNow(3), publication_date: daysAgo(7), status: 'pending', priority: 2, position: 0, progress: 0, activity_url: '', archived: false, created_at: daysAgo(7), updated_at: daysAgo(7), source_course_name: 'Cálculo Diferencial', source_activity_id: 'act-001', assignee: 'João Silva' },
    { id: 'task-2', column_id: 'col-pend-1', board_id: 'board-1', title: 'Estudar transformações lineares', description: 'Revisar notas de aula e fazer resumo', discipline: 'Álgebra Linear', due_date: daysFromNow(5), publication_date: daysAgo(3), status: 'pending', priority: 1, position: 1, progress: 10, activity_url: '', archived: false, created_at: daysAgo(3), updated_at: daysAgo(2), source_course_name: 'Álgebra Linear', source_activity_id: 'act-002', assignee: 'João Silva' },
    { id: 'task-3', column_id: 'col-pend-1', board_id: 'board-1', title: 'Preparar apresentação sobre IoT', description: 'Slides para seminário da disciplina de Redes', discipline: 'Redes de Computadores', due_date: daysFromNow(7), publication_date: daysAgo(10), status: 'pending', priority: 3, position: 2, progress: 5, activity_url: '', archived: false, created_at: daysAgo(10), updated_at: daysAgo(1), source_course_name: 'Redes', source_activity_id: 'act-003', assignee: 'Maria Santos' },
    { id: 'task-4', column_id: 'col-pend-1', board_id: 'board-1', title: 'Ler artigo sobre Machine Learning', description: 'Artigo: "A Survey of Deep Learning Techniques"', discipline: 'Inteligência Artificial', due_date: daysFromNow(10), publication_date: daysAgo(5), status: 'pending', priority: 1, position: 3, progress: 0, activity_url: '', archived: false, created_at: daysAgo(5), updated_at: daysAgo(5), source_course_name: 'IA', source_activity_id: 'act-004' },
  ],
  'col-prog-1': [
    { id: 'task-5', column_id: 'col-prog-1', board_id: 'board-1', title: 'Implementar algoritmo de ordenação', description: 'Merge Sort e Quick Sort em Python', discipline: 'Algoritmos', due_date: daysAgo(1), publication_date: daysAgo(14), status: 'in_progress', priority: 2, position: 0, progress: 60, activity_url: '', archived: false, created_at: daysAgo(14), updated_at: daysAgo(1), source_course_name: 'EDA', source_activity_id: 'act-005', assignee: 'João Silva' },
    { id: 'task-6', column_id: 'col-prog-1', board_id: 'board-1', title: 'Criar API REST com FastAPI', description: 'Endpoint CRUD para sistema de biblioteca', discipline: 'Desenvolvimento Web', due_date: daysFromNow(4), publication_date: daysAgo(7), status: 'in_progress', priority: 2, position: 1, progress: 35, activity_url: '', archived: false, created_at: daysAgo(7), updated_at: daysAgo(1), source_course_name: 'Web', source_activity_id: 'act-006', assignee: 'Ana Costa' },
    { id: 'task-7', column_id: 'col-prog-1', board_id: 'board-1', title: 'Modelagem de Banco de Dados', description: 'Diagrama ER para o projeto da biblioteca', discipline: 'Banco de Dados', due_date: daysFromNow(2), publication_date: daysAgo(10), status: 'in_progress', priority: 3, position: 2, progress: 80, activity_url: '', archived: false, created_at: daysAgo(10), updated_at: daysAgo(1), source_course_name: 'BD', source_activity_id: 'act-007', assignee: 'João Silva' },
  ],
  'col-rev-1': [
    { id: 'task-8', column_id: 'col-rev-1', board_id: 'board-1', title: 'Relatório de laboratório - Física', description: 'Experimento sobre lei de Ohm', discipline: 'Física Experimental', due_date: daysAgo(2), publication_date: daysAgo(21), status: 'pending', priority: 2, position: 0, progress: 90, activity_url: '', archived: false, created_at: daysAgo(21), updated_at: daysAgo(1), source_course_name: 'Física', source_activity_id: 'act-008', assignee: 'João Silva' },
  ],
  'col-done-1': [
    { id: 'task-9', column_id: 'col-done-1', board_id: 'board-1', title: 'Quiz online - Semana 4', description: 'Nota: 9.5/10', discipline: 'Matemática Discreta', due_date: daysAgo(5), publication_date: daysAgo(14), status: 'completed', priority: 1, position: 0, progress: 100, activity_url: '', archived: false, created_at: daysAgo(14), updated_at: daysAgo(5), source_course_name: 'Matemática', source_activity_id: 'act-009' },
    { id: 'task-10', column_id: 'col-done-1', board_id: 'board-1', title: 'TP1 - Estrutura de Dados', description: 'Aprovado com 8.5', discipline: 'Estrutura de Dados', due_date: daysAgo(10), publication_date: daysAgo(30), status: 'completed', priority: 2, position: 1, progress: 100, activity_url: '', archived: false, created_at: daysAgo(30), updated_at: daysAgo(10), source_course_name: 'EDA', source_activity_id: 'act-010', assignee: 'João Silva' },
  ],
};

export const MOCK_COLUMNS: Column[] = [
  { id: 'col-pend-1', board_id: 'board-1', name: 'Pendente', position: 0, color: '#F59E0B', created_at: daysAgo(30) },
  { id: 'col-prog-1', board_id: 'board-1', name: 'Em Andamento', position: 1, color: '#4A90D9', created_at: daysAgo(30) },
  { id: 'col-rev-1', board_id: 'board-1', name: 'Revisão', position: 2, color: '#8B5CF6', created_at: daysAgo(30) },
  { id: 'col-done-1', board_id: 'board-1', name: 'Concluído', position: 3, color: '#10B981', created_at: daysAgo(30) },
];

export function getMockBoardFull(id: string): BoardFull | undefined {
  const board = MOCK_BOARDS.find(b => b.id === id);
  if (!board) return undefined;
  const columns: ColumnWithTasks[] = MOCK_COLUMNS
    .filter(c => c.board_id === id)
    .map(c => ({
      ...c,
      tasks: MOCK_TASKS[c.id] || [],
    }))
    .sort((a, b) => a.position - b.position);
  return { ...board, columns };
}

export const MOCK_VIGENT_ACTIVITIES: Task[] = [
  { id: 'vig-1', column_id: null, board_id: 'board-1', title: 'Entrega TP2 - Inteligência Artificial', description: 'Segunda avaliação parcial da disciplina', discipline: 'Inteligência Artificial', due_date: daysFromNow(3), publication_date: daysAgo(14), status: 'pending', priority: 3, position: 0, progress: 0, activity_url: 'https://moodle.exemplo.com/mod/assign/view.php?id=123', archived: false, created_at: daysAgo(14), updated_at: daysAgo(1), source_course_name: 'Moodle - IA', source_activity_id: 'm-001' },
  { id: 'vig-2', column_id: null, board_id: 'board-1', title: 'Prova - Banco de Dados II', description: 'Prova bimestral valendo 10 pontos', discipline: 'Banco de Dados', due_date: daysFromNow(5), publication_date: daysAgo(21), status: 'pending', priority: 3, position: 0, progress: 0, activity_url: '', archived: false, created_at: daysAgo(21), updated_at: daysAgo(2), source_course_name: 'Moodle - BD', source_activity_id: 'm-002' },
  { id: 'vig-3', column_id: null, board_id: 'board-1', title: 'Lista de Exercícios - Redes', description: '10 questões sobre TCP/IP', discipline: 'Redes de Computadores', due_date: daysFromNow(7), publication_date: daysAgo(3), status: 'pending', priority: 2, position: 0, progress: 0, activity_url: '', archived: false, created_at: daysAgo(3), updated_at: daysAgo(3), source_course_name: 'Moodle - Redes', source_activity_id: 'm-003' },
  { id: 'vig-4', column_id: null, board_id: 'board-1', title: 'Seminário - Engenharia de Software', description: 'Apresentar artigo sobre metodologias ágeis', discipline: 'Engenharia de Software', due_date: daysFromNow(10), publication_date: daysAgo(7), status: 'pending', priority: 2, position: 0, progress: 15, activity_url: 'https://moodle.exemplo.com/mod/forum/view.php?id=456', archived: false, created_at: daysAgo(7), updated_at: daysAgo(1), source_course_name: 'Moodle - ES', source_activity_id: 'm-004' },
  { id: 'vig-5', column_id: null, board_id: 'board-1', title: 'Questionário Online - Semana 8', description: 'Quiz valendo 2 pontos extras', discipline: 'Sistemas Operacionais', due_date: daysAgo(1), publication_date: daysAgo(7), status: 'overdue', priority: 1, position: 0, progress: 0, activity_url: '', archived: false, created_at: daysAgo(7), updated_at: daysAgo(1), source_course_name: 'Moodle - SO', source_activity_id: 'm-005' },
  { id: 'vig-6', column_id: null, board_id: 'board-1', title: 'Trabalho Final - Projeto Integrador', description: 'Documentação e apresentação do projeto', discipline: 'Projeto Integrador', due_date: daysFromNow(14), publication_date: daysAgo(30), status: 'pending', priority: 3, position: 0, progress: 20, activity_url: '', archived: false, created_at: daysAgo(30), updated_at: daysAgo(1), source_course_name: 'Moodle - PI', source_activity_id: 'm-006' },
];

export const MOCK_DASHBOARD_STATS: DashboardStats = {
  total_tasks: 28,
  pending: 12,
  in_progress: 6,
  completed: 8,
  overdue: 2,
  archived: 0,
  due_this_week: 5,
  total_boards: 4,
  total_activities_imported: 6,
};

export const MOCK_DISCIPLINES = [
  { id: '16090', name: 'ARQUITETURA DE COMPUTADORES', code: 'COD16090', course_id: 16090 },
  { id: '16057', name: 'BANCO DE DADOS I', code: 'COD16057', course_id: 16057 },
  { id: '16020', name: 'ANALISE E PROJETO DE SISTEMAS ORIENTADO A OBJETOS', code: 'COD16020', course_id: 16020 },
  { id: '16016', name: 'DESENVOLVIMENTO WEB II', code: 'COD16016', course_id: 16016 },
  { id: '16004', name: 'INTERFACE HOMEM-MAQUINA', code: 'COD16004', course_id: 16004 },
  { id: '15298', name: 'INTERNET DAS COISAS', code: 'COD15298', course_id: 15298 },
  { id: '15659', name: 'LABORATORIO DE PROGRAMACAO III', code: 'COD15659', course_id: 15659 },
  { id: '16058', name: 'LINGUAGEM PARA APLICACOES INTERNET I', code: 'COD16058', course_id: 16058 },
  { id: '16003', name: 'METODOLOGIA DA PESQUISA CIENTIFICA', code: 'COD16003', course_id: 16003 },
  { id: '15980', name: 'PRATICA DE ANALISE E PROJETO ORIENTADO A OBJETOS', code: 'COD15980', course_id: 15980 },
  { id: '15423', name: 'PROGRAMACAO AVANCADA', code: 'COD15423', course_id: 15423 },
];
