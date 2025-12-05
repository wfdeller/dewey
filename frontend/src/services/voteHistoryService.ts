import { api } from './api';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';

// Types
export interface VoteHistoryRecord {
  id: string;
  contact_id: string;
  election_name: string;
  election_date: string;
  election_type: string;
  voted: boolean | null;
  voting_method: string | null;
  primary_party_voted: string | null;
  source_file_name: string | null;
  imported_at: string;
  created_at: string;
}

export interface VoteHistorySummary {
  total_elections: number;
  elections_voted: number;
  elections_missed: number;
  elections_unknown: number;
  vote_rate: number;
  general_elections_voted: number;
  primary_elections_voted: number;
  last_voted_date: string | null;
  last_voted_election: string | null;
  most_common_method: string | null;
}

export interface VoteHistoryListResponse {
  items: VoteHistoryRecord[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// API functions
export const voteHistoryService = {
  async getVoteHistory(
    contactId: string,
    page = 1,
    pageSize = 20
  ): Promise<VoteHistoryListResponse> {
    const response = await api.get<VoteHistoryListResponse>(
      `/contacts/${contactId}/vote-history`,
      { params: { page, page_size: pageSize } }
    );
    return response.data;
  },

  async getVoteSummary(contactId: string): Promise<VoteHistorySummary> {
    const response = await api.get<VoteHistorySummary>(
      `/contacts/${contactId}/vote-history/summary`
    );
    return response.data;
  },
};

// React Query hooks

// Get vote history for a contact
export const useVoteHistoryQuery = (
  contactId: string | null,
  page = 1,
  pageSize = 20
) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return useQuery({
    queryKey: ['vote-history', contactId, page, pageSize],
    queryFn: () => voteHistoryService.getVoteHistory(contactId!, page, pageSize),
    enabled: isAuthenticated && !!contactId,
  });
};

// Get vote summary for a contact
export const useVoteSummaryQuery = (contactId: string | null) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return useQuery({
    queryKey: ['vote-summary', contactId],
    queryFn: () => voteHistoryService.getVoteSummary(contactId!),
    enabled: isAuthenticated && !!contactId,
  });
};

// Helper to format voting method
export const formatVotingMethod = (method: string | null): string => {
  if (!method) return 'Unknown';
  const methods: Record<string, string> = {
    election_day: 'Election Day',
    early: 'Early Voting',
    absentee: 'Absentee',
    mail: 'Vote by Mail',
  };
  return methods[method] || method;
};

// Helper to format election type
export const formatElectionType = (type: string): string => {
  const types: Record<string, string> = {
    general: 'General',
    primary: 'Primary',
    special: 'Special',
    municipal: 'Municipal',
    runoff: 'Runoff',
  };
  return types[type] || type;
};
