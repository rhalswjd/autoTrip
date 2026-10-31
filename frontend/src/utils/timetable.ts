import type { DepartureInfo, Timetable } from '../api/types';

export interface SelectedTimetableBucket {
  calendar: Timetable['selected_calendar'];
  label: string;
  departures: DepartureInfo[];
}

export function selectedTimetableBucket(
  timetable: Timetable | undefined,
): SelectedTimetableBucket {
  const calendar = timetable?.selected_calendar ?? 'weekday';
  const labels: Record<Timetable['selected_calendar'], string> = {
    weekday: 'Weekday',
    saturday: 'Saturday',
    holiday: 'Sunday / Holiday',
  };
  return {
    calendar,
    label: labels[calendar],
    departures: timetable?.[calendar] ?? [],
  };
}
