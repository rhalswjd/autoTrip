/** Compact side-view mark for journey information, independent of hero artwork. */
export function TrainSilhouette({ size = 22 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 28 24" fill="none" aria-hidden="true">
    <path d="M3 3h8c4 0 6 3 8 7l6 7c1 2 0 3-2 3H5c-2 0-3-1-3-3V5c0-1 0-2 1-2Z" fill="currentColor" />
    <path d="M12 6c2 0 4 3 5 6h-5V6Z" fill="var(--rail-surface,#fff)" />
    <path d="M5 6h3v7H5Z" fill="var(--rail-surface,#fff)" opacity=".85" />
    <path d="M5 23h17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
  </svg>;
}
