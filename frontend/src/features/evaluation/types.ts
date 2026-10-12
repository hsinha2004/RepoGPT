export interface BenchmarkQuestion {
  id: string;
  question: string;
  category: "locate" | "explain" | "flow" | "architecture" | "dependency" | "config" | string;
  expected_intent: string;
  expected_files: string[];
  expected_symbols: string[];
  must_mention?: string[];
}

export interface Benchmark {
  id: string;
  name: string;
  description: string;
  repo: {
    type?: string;
    path?: string;
    url?: string;
    ref?: string;
  };
  questions: BenchmarkQuestion[];
  question_count: number;
  is_builtin: boolean;
  owner_id?: string;
  created_at: string;
}

export interface EvalEstimateResponse {
  benchmark_id: string;
  questions_count: number;
  strategies: string[];
  strategies_count: number;
  generate_answers: boolean;
  llm_judge: boolean;
  estimated_llm_calls: number;
  estimated_tokens: number;
  estimated_cost_usd: number;
  estimated_duration_seconds: number;
}

export interface StrategyMetrics {
  strategy: string;
  hit_1: number;
  hit_3: number;
  hit_5: number;
  hit_10: number;
  precision_5: number;
  recall_5: number;
  mrr: number;
  ndcg_5: number;
  ndcg_10: number;
  symbol_recall_5: number;
  citation_validity: number;
  citation_precision: number;
  citation_recall: number;
  must_mention_coverage: number;
  answer_correctness: number;
  brier_score: number;
  ece: number;
  latency_p50: number;
  latency_p95: number;
  latency_route_p50: number;
  latency_retrieve_p50: number;
  latency_rerank_p50: number;
  latency_generate_p50: number;
  total_tokens: number;
  total_cost_usd: number;
}

export interface CalibrationBin {
  bin_idx: number;
  range_label: string;
  min_prob: number;
  max_prob: number;
  count: number;
  mean_predicted_confidence: number;
  empirical_accuracy: number;
}

export interface EvalRunSummary {
  id: string;
  repo_id: string;
  benchmark_id: string;
  benchmark_name: string;
  strategies: string[];
  generate_answers: boolean;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  total_questions: number;
  completed_questions: number;
  created_at: string;
  finished_at?: string | null;
  duration_seconds: number;
  error_message?: string | null;
  strategy_metrics: Record<string, StrategyMetrics>;
  calibration_bins: Record<string, CalibrationBin[]>;
}

export interface EvalQuestionResult {
  id?: string;
  run_id: string;
  question_id: string;
  category: string;
  strategy: string;
  query: string;
  predicted_intent: string;
  hit_1: number;
  hit_3: number;
  hit_5: number;
  hit_10: number;
  precision_5: number;
  recall_5: number;
  symbol_recall_5: number;
  answer: string;
  citations: string[];
  citation_validity: number;
  citation_precision: number;
  citation_recall: number;
  must_mention_coverage: number;
  is_correct: boolean;
  confidence_score: number;
  latency_ms: number;
  total_tokens: number;
}

export interface EvalLiveMetrics {
  questions_per_day: { date: string; count: number }[];
  latency_p50_p95: { date: string; p50: number; p95: number }[];
  tokens_and_cost: { date: string; tokens: number; cost_usd: number }[];
  satisfaction_gauge: {
    positive_ratings: number;
    negative_ratings: number;
    ratio: number;
  };
  confidence_distribution: { range: string; count: number }[];
}
