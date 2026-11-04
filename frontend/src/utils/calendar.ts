/** Date-only calendar arithmetic. UTC prevents local DST from changing a day. */
export function calendarDate(value: string): Date {
  return new Date(`${value}T12:00:00Z`);
}
export function dateKey(date: Date): string { return date.toISOString().slice(0, 10); }
export function shiftCalendarDay(value: string, days: number): string {
  const date = calendarDate(value);
  date.setUTCDate(date.getUTCDate() + days);
  return dateKey(date);
}
export function shiftCalendarMonth(value: string, months: number): string {
  const date = calendarDate(value);
  const day = date.getUTCDate();
  date.setUTCDate(1);
  date.setUTCMonth(date.getUTCMonth() + months);
  const last = new Date(date);
  last.setUTCMonth(last.getUTCMonth() + 1, 0);
  date.setUTCDate(Math.min(day, last.getUTCDate()));
  return dateKey(date);
}
export function japanToday(): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
  return ['year', 'month', 'day'].map(type => parts.find(part => part.type === type)!.value).join('-');
}
