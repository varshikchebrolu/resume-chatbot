export interface OptimizeRequest {
  resume?: string;
  jd: string;
  title?: string;
  save?: boolean;
}

export interface OptimizeResult {
  id: number | null;
  saved: boolean;
  title: string;
  ats_score: number;
  iterations: number;
  matched_keywords: string[];
  unmatched_keywords: string[];
  jd_keywords: string[];
  resume_keywords: string[];
  updated_resume: string;
  original_resume: string;
  jd: string;
}

export interface OptimizationSummary {
  id: number;
  title: string;
  ats_score: number;
  iterations: number;
  created_at: string | null;
}

// Shape returned by GET /optimizations/{id} (backend Optimization.detail()).
export interface OptimizationDetail {
  id: number;
  title: string;
  ats_score: number;
  iterations: number;
  created_at: string | null;
  jd: string;
  original_resume: string;
  optimized_resume: string;
  matched_keywords: string[];
  unmatched_keywords: string[];
  jd_keywords: string[];
  resume_keywords: string[];
}

export interface ResumeStatus {
  has_custom_resume: boolean;
  length: number;
  preview: string;
}
