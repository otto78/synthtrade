/** TASK-431: Modello per la risposta API /api/config/mode */
export interface ModeInfo {
  mode: 'test' | 'live';
  allow_live: boolean;
  details: string;
}