export function parseTimeToMinutes(timeStr: string): number {
  if (!timeStr) return 0;
  // Handle formats like "08:30" or "8:30"
  const parts = timeStr.split(':');
  if (parts.length !== 2) return 0;
  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);
  if (isNaN(hours) || isNaN(minutes)) return 0;
  return hours * 60 + minutes;
}

export function isTimeAfterOrEqual(time1: string, time2: string, bufferMinutes = 0): boolean {
  if (!time1 || !time2) return true; // fallback to true if missing
  let t1 = parseTimeToMinutes(time1);
  let t2 = parseTimeToMinutes(time2) + bufferMinutes;
  
  // Handle simple midnight crossing if t1 < 4 hours (e.g. 01:00) and t2 is > 20:00
  if (t1 < 4 * 60 && t2 > 20 * 60) {
    t1 += 24 * 60;
  }
  // Same for t2
  if (t2 < 4 * 60 && t1 > 20 * 60) {
    t2 += 24 * 60;
  }
  
  return t1 >= t2;
}
