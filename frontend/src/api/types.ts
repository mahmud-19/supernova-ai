export type CaseStatus = 'pending' | 'in_review' | 'approved';

export type InferenceResult = {
  id: number;
  case_id: number;
  version: number;
  source: 'ai' | 'expert';
  contour_json: number[][][];
  confidence_score: number;
  total_lesions: number;
  total_pixels: number;
  created_at: string;
};

export type CaseDetail = {
  id: number;
  display_code: string;
  status: CaseStatus;
  owner_name: string | null;
  width: number;
  height: number;
  file_format: string;
  bit_depth: number;
  contrast_adjusted: boolean;
  is_finalized: boolean;
  // Patient / exam metadata
  patient_id: string | null;
  patient_name: string | null;
  age: number | null;
  gender: string | null;
  exam_date: string | null;
  sonologist_note: string | null;
  reviewer_note: string | null;
  submitted: boolean;
  created_at: string;
  updated_at: string;
  current_result: InferenceResult | null;
};
