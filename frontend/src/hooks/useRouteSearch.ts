import { useQuery } from '@tanstack/react-query';
import { searchRoutes } from '../api';
import type { SearchParams } from '../api';

export function useRouteSearch(params: SearchParams | null) {
  return useQuery({
    queryKey: ['routes', params],
    queryFn: () => searchRoutes(params!),
    enabled: !!params,
  });
}
