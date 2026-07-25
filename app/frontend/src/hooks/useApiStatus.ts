import { useQuery } from '@tanstack/react-query';
import { fetchHealth } from '../api/health';
import { fetchCurrentModel } from '../api/models';

export function useHealthQuery() {
  return useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: 30_000,
    retry: 1,
  });
}

export function useModelQuery() {
  return useQuery({
    queryKey: ['models', 'current'],
    queryFn: ({ signal }) => fetchCurrentModel(signal),
    retry: 1,
  });
}
