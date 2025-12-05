import { api } from './api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';

// Types
export interface Job {
  id: string;
  tenant_id: string;
  job_type: string;
  status: string;
  original_filename: string | null;
  file_size_bytes: number | null;
  total_rows: number | null;
  detected_headers: string[] | null;
  suggested_mappings: Record<string, FieldMapping> | null;
  confirmed_mappings: Record<string, string> | null;
  matching_strategy: string | null;
  suggested_matching_strategy: string | null;
  matching_strategy_reason: string | null;
  create_unmatched: boolean;
  rows_processed: number;
  rows_created: number;
  rows_updated: number;
  rows_skipped: number;
  rows_errored: number;
  error_message: string | null;
  error_details: ErrorDetail[] | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  created_by_id: string;
}

export interface FieldMapping {
  field: string | null;
  confidence: number;
  reason: string;
}

export interface ErrorDetail {
  row: number;
  error: string;
  data?: Record<string, string>;
}

export interface JobProgress {
  status: string;
  rows_processed: number;
  rows_created: number;
  rows_updated: number;
  rows_skipped: number;
  rows_errored: number;
  total_rows: number | null;
  percent_complete: number | null;
}

export interface AnalysisResponse {
  job_id: string;
  headers: string[];
  suggested_mappings: Record<string, FieldMapping>;
  vote_history_columns: string[];
  suggested_matching_strategy: string;
  matching_strategy_reason: string;
  total_rows: number;
}

export interface ConfirmMappingsRequest {
  confirmed_mappings: Record<string, string | null>;
  matching_strategy: string;
  create_unmatched: boolean;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  limit: number;
  offset: number;
}

export interface MatchingStrategies {
  strategies: Record<string, string>;
}

// API functions
export const voterImportService = {
  async getStrategies(): Promise<MatchingStrategies> {
    const response = await api.get<MatchingStrategies>('/voter-import/strategies');
    return response.data;
  },

  async uploadFile(file: File): Promise<Job> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<Job>('/voter-import/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async analyzeJob(jobId: string): Promise<AnalysisResponse> {
    const response = await api.post<AnalysisResponse>(`/voter-import/${jobId}/analyze`);
    return response.data;
  },

  async getJob(jobId: string): Promise<Job> {
    const response = await api.get<Job>(`/voter-import/${jobId}`);
    return response.data;
  },

  async getJobProgress(jobId: string): Promise<JobProgress> {
    const response = await api.get<JobProgress>(`/voter-import/${jobId}/progress`);
    return response.data;
  },

  async confirmMappings(jobId: string, data: ConfirmMappingsRequest): Promise<Job> {
    const response = await api.patch<Job>(`/voter-import/${jobId}/confirm`, data);
    return response.data;
  },

  async startImport(jobId: string): Promise<Job> {
    const response = await api.post<Job>(`/voter-import/${jobId}/start`);
    return response.data;
  },

  async deleteJob(jobId: string): Promise<void> {
    await api.delete(`/voter-import/${jobId}`);
  },

  async listJobs(limit = 50, offset = 0): Promise<JobListResponse> {
    const response = await api.get<JobListResponse>('/voter-import', {
      params: { limit, offset },
    });
    return response.data;
  },
};

// React Query hooks

// Get matching strategies
export const useMatchingStrategiesQuery = () => {
  return useQuery({
    queryKey: ['voter-import', 'strategies'],
    queryFn: () => voterImportService.getStrategies(),
    staleTime: 30 * 60 * 1000, // 30 minutes (strategies are static)
  });
};

// Get job by ID
export const useJobQuery = (jobId: string | null) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return useQuery({
    queryKey: ['voter-import', 'job', jobId],
    queryFn: () => voterImportService.getJob(jobId!),
    enabled: isAuthenticated && !!jobId,
    refetchInterval: (query) => {
      // Poll more frequently while processing
      const job = query.state.data;
      if (job?.status === 'processing') return 2000;
      return false;
    },
  });
};

// Get job progress (for polling during import)
export const useJobProgressQuery = (jobId: string | null, enabled = true) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return useQuery({
    queryKey: ['voter-import', 'progress', jobId],
    queryFn: () => voterImportService.getJobProgress(jobId!),
    enabled: isAuthenticated && !!jobId && enabled,
    refetchInterval: 1000, // Poll every second during import
  });
};

// List jobs
export const useJobsQuery = (limit = 50, offset = 0) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return useQuery({
    queryKey: ['voter-import', 'jobs', limit, offset],
    queryFn: () => voterImportService.listJobs(limit, offset),
    enabled: isAuthenticated,
  });
};

// Check for active jobs (for the Jobs pill in the header)
export const useActiveJobsQuery = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return useQuery({
    queryKey: ['voter-import', 'active-jobs'],
    queryFn: async () => {
      const response = await voterImportService.listJobs(10, 0);
      const activeJobs = response.items.filter(
        (job) => job.status === 'processing' || job.status === 'queued' || job.status === 'analyzing'
      );
      return {
        hasActive: activeJobs.length > 0,
        activeCount: activeJobs.length,
        totalJobs: response.total,
      };
    },
    enabled: isAuthenticated,
    refetchInterval: 5000, // Poll every 5 seconds
    staleTime: 2000,
  });
};

// Upload file mutation
export const useUploadFileMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => voterImportService.uploadFile(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voter-import', 'jobs'] });
    },
  });
};

// Analyze job mutation
export const useAnalyzeJobMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => voterImportService.analyzeJob(jobId),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: ['voter-import', 'job', jobId] });
    },
  });
};

// Confirm mappings mutation
export const useConfirmMappingsMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, data }: { jobId: string; data: ConfirmMappingsRequest }) =>
      voterImportService.confirmMappings(jobId, data),
    onSuccess: (_, { jobId }) => {
      queryClient.invalidateQueries({ queryKey: ['voter-import', 'job', jobId] });
    },
  });
};

// Start import mutation
export const useStartImportMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => voterImportService.startImport(jobId),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: ['voter-import', 'job', jobId] });
      queryClient.invalidateQueries({ queryKey: ['voter-import', 'jobs'] });
    },
  });
};

// Delete job mutation
export const useDeleteJobMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => voterImportService.deleteJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voter-import', 'jobs'] });
    },
  });
};

// Available contact fields for mapping
export const CONTACT_FIELDS = [
  // Contact Info
  { value: 'email', label: 'Email', group: 'Contact' },
  { value: 'secondary_email', label: 'Secondary Email', group: 'Contact' },
  { value: 'phone', label: 'Phone', group: 'Contact' },
  { value: 'mobile_phone', label: 'Mobile Phone', group: 'Contact' },
  { value: 'work_phone', label: 'Work Phone', group: 'Contact' },

  // Name
  { value: 'name', label: 'Full Name', group: 'Name' },
  { value: 'prefix', label: 'Prefix (Mr., Mrs., etc.)', group: 'Name' },
  { value: 'first_name', label: 'First Name', group: 'Name' },
  { value: 'middle_name', label: 'Middle Name', group: 'Name' },
  { value: 'last_name', label: 'Last Name', group: 'Name' },
  { value: 'suffix', label: 'Suffix (Jr., Sr., etc.)', group: 'Name' },
  { value: 'preferred_name', label: 'Preferred Name/Nickname', group: 'Name' },

  // Address
  { value: 'address_street', label: 'Street Address', group: 'Address' },
  { value: 'address_street2', label: 'Address Line 2', group: 'Address' },
  { value: 'address_city', label: 'City', group: 'Address' },
  { value: 'address_state', label: 'State', group: 'Address' },
  { value: 'address_zip', label: 'ZIP Code', group: 'Address' },

  // Geographic/Political
  { value: 'state', label: 'State (2-letter)', group: 'Geographic' },
  { value: 'zip_code', label: 'ZIP Code', group: 'Geographic' },
  { value: 'county', label: 'County', group: 'Geographic' },
  { value: 'congressional_district', label: 'Congressional District', group: 'Geographic' },
  { value: 'state_legislative_district', label: 'State Legislative District', group: 'Geographic' },
  { value: 'precinct', label: 'Precinct', group: 'Geographic' },
  { value: 'school_district', label: 'School District', group: 'Geographic' },
  { value: 'municipal_district', label: 'Municipal District', group: 'Geographic' },

  // Voter Info
  { value: 'state_voter_id', label: 'State Voter ID', group: 'Voter' },
  { value: 'party_affiliation', label: 'Party Affiliation', group: 'Voter' },
  { value: 'voter_status', label: 'Voter Status', group: 'Voter' },
  { value: 'voter_registration_date', label: 'Voter Registration Date', group: 'Voter' },
  { value: 'modeled_party', label: 'Modeled Party', group: 'Voter' },

  // Demographics
  { value: 'date_of_birth', label: 'Date of Birth', group: 'Demographics' },
  { value: 'age_estimate', label: 'Age (Estimated)', group: 'Demographics' },
  { value: 'gender', label: 'Gender', group: 'Demographics' },
  { value: 'pronouns', label: 'Pronouns', group: 'Demographics' },
  { value: 'preferred_language', label: 'Preferred Language', group: 'Demographics' },

  // Socioeconomic
  { value: 'income_bracket', label: 'Income Bracket', group: 'Socioeconomic' },
  { value: 'education_level', label: 'Education Level', group: 'Socioeconomic' },
  { value: 'homeowner_status', label: 'Homeowner Status', group: 'Socioeconomic' },
  { value: 'household_size', label: 'Household Size', group: 'Socioeconomic' },
  { value: 'has_children', label: 'Has Children', group: 'Socioeconomic' },
  { value: 'marital_status', label: 'Marital Status', group: 'Socioeconomic' },

  // Employment
  { value: 'occupation', label: 'Occupation', group: 'Employment' },
  { value: 'employer', label: 'Employer', group: 'Employment' },
  { value: 'job_title', label: 'Job Title', group: 'Employment' },
  { value: 'industry', label: 'Industry', group: 'Employment' },

  // Vote History (for explicit column mapping)
  { value: 'vote_history', label: 'Vote History Column (auto-detect)', group: 'Vote History' },
  { value: 'vh_election_name', label: 'Election Name', group: 'Vote History' },
  { value: 'vh_election_date', label: 'Election Date', group: 'Vote History' },
  { value: 'vh_election_type', label: 'Election Type', group: 'Vote History' },
  { value: 'vh_voted', label: 'Voted (Yes/No)', group: 'Vote History' },
  { value: 'vh_voting_method', label: 'Voting Method', group: 'Vote History' },
  { value: 'vh_primary_party', label: 'Primary Party Voted', group: 'Vote History' },

  // Other
  { value: 'notes', label: 'Notes', group: 'Other' },
  { value: 'is_active', label: 'Is Active', group: 'Other' },
  { value: 'inactive_reason', label: 'Inactive Reason', group: 'Other' },
];

// Group fields for select dropdown
export const getGroupedFieldOptions = () => {
  const groups: Record<string, { value: string; label: string }[]> = {};
  CONTACT_FIELDS.forEach((field) => {
    if (!groups[field.group]) {
      groups[field.group] = [];
    }
    groups[field.group].push({ value: field.value, label: field.label });
  });
  return Object.entries(groups).map(([group, options]) => ({
    label: group,
    options,
  }));
};
