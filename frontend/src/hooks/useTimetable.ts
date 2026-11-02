import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { getTimetable, getSegmentTimetable } from '../api';
import { getPassengerTimetable } from '../api/routes';

export function usePassengerTimetable(routeId: string, legIndex: number, searchDate: string | undefined, enabled: boolean, notBefore?: string) {
  return useInfiniteQuery({
    queryKey: ['passenger-timetable', routeId, searchDate, legIndex, notBefore],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => getPassengerTimetable(routeId, legIndex, pageParam, searchDate, notBefore),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled,
    retry: false,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}

export function useTimetable(routeId: string | null, searchDate?: string) {
  return useQuery({
    queryKey: ['timetable', routeId, searchDate],
    queryFn: () => getTimetable(routeId!),
    enabled: !!routeId,
  });
}

export function useSegmentTimetable(
  routeId: string | null,
  segmentIndex: number | null,
  searchDate?: string,
) {
  return useQuery({
    queryKey: ['timetable', routeId, searchDate, 'segment', segmentIndex],
    queryFn: () => getSegmentTimetable(routeId!, segmentIndex!),
    enabled: !!routeId && segmentIndex !== null,
  });
}
