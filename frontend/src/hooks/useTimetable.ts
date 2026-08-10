import { useQuery } from '@tanstack/react-query';
import { getTimetable, getSegmentTimetable } from '../api';

export function useTimetable(routeId: string | null) {
  return useQuery({
    queryKey: ['timetable', routeId],
    queryFn: () => getTimetable(routeId!),
    enabled: !!routeId,
  });
}

export function useSegmentTimetable(routeId: string | null, segmentIndex: number | null) {
  return useQuery({
    queryKey: ['timetable', routeId, 'segment', segmentIndex],
    queryFn: () => getSegmentTimetable(routeId!, segmentIndex!),
    enabled: !!routeId && segmentIndex !== null,
  });
}
