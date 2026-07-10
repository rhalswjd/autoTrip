import { useQuery } from '@tanstack/react-query';
import { getTimetable } from '../api';

export function useTimetable(routeId: string | null) {
  return useQuery({
    queryKey: ['timetable', routeId],
    queryFn: () => getTimetable(routeId!),
    enabled: !!routeId,
  });
}
