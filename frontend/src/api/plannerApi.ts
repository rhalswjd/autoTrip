import { api } from './client';
import type { Route } from './types';

export interface PlannerParams {
  planner_mode?: string;
  specific_date?: string;
}

export function getRoutePlanner(routeId: string, params: PlannerParams): Promise<Route> {
  const query = new URLSearchParams();
  if (params.planner_mode) {
    query.set('planner_mode', params.planner_mode);
  }
  
  // planner_mode가 SPECIFIC_DATE일 때만 API에 specific_date 전달
  if (params.planner_mode === 'SPECIFIC_DATE' && params.specific_date) {
    query.set('specific_date', params.specific_date);
  }
  
  return api.get<Route>(`/routes/${routeId}/planner?${query.toString()}`);
}
