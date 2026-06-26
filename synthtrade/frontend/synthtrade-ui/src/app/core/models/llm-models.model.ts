export interface LLMModelsPayload {
  cascade: string[];
  fallback: string;
  use_case?: string;
}

export interface LLMUseCase {
  id: string;
  name: string;
  description: string;
}

export const LLM_USE_CASES: LLMUseCase[] = [
  { id: 'pipeline_eval', name: 'Pipeline Eval', description: 'Modelli per valutazione pipeline strategie' },
  { id: 'supervisor', name: 'Supervisor AI', description: 'Modelli per supervisor decisioni trading' },
];
