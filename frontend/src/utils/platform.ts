import type { PlatformStatus } from '../api/types';

export function platformLabel(value: string | number | null | undefined, status: PlatformStatus | undefined, source: string): string {
  if ((status === 'KNOWN' || !status) && value !== null && value !== undefined && String(value).trim()) return String(value);
  if (status === 'SOURCE_NOT_PROVIDED') return source === 'jr_odekake' ? '공식 정보 미제공' : '출처 정보 미제공';
  return '조회 실패';
}
