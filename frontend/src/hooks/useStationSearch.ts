import { useQuery } from '@tanstack/react-query';
import { searchStations } from '../api';

export function useStationSearch(query: string) {
  return useQuery({
    queryKey: ['stations', query],
    queryFn: () => searchStations(query),
    enabled: query.length >= 2,
  });
}
