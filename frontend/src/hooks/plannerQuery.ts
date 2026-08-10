import { useQuery } from '@tanstack/react-query';
import { getRoutePlanner } from '../api/plannerApi';
import type { Route } from '../api/types';

export function usePlannerRoute(routeId: string, plannerMode: string = 'WEEKDAY', specificDate?: string) {
  return useQuery<Route, Error>({
    // Query Key: route_id뿐만 아니라 모드와 날짜를 포함하여 
    // 파라미터가 변경될 때마다 캐시를 분리하고 자동으로 Query가 호출되도록 설정
    queryKey: ['planner', routeId, plannerMode, specificDate],
    queryFn: () => getRoutePlanner(routeId, { 
      planner_mode: plannerMode, 
      specific_date: specificDate 
    }),
    
    // Cache Policy:
    // 실시간성이 중요하므로 짧은 staleTime 유지
    staleTime: 60 * 1000, 
    
    // 사용자가 다른 페이지로 갔다가 돌아올 때를 대비해 캐시를 10분간 유지
    gcTime: 10 * 60 * 1000, 
    
    // 스크래퍼는 타임아웃, 429 에러 등을 악화시킬 수 있으므로 재시도 안함
    retry: 0, 
    
    // routeId가 존재할 때만 쿼리를 활성화하여 빈 ID로 API가 호출되는 것을 방지합니다.
    enabled: Boolean(routeId),
  });
}
