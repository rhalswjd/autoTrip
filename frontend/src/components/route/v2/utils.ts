export function getLineColor(railwayName: string): string {
  if (!railwayName || railwayName === 'Walk' || railwayName.includes('徒歩')) return '#9aa0a6';
  
  // Simple hash to generate a consistent color per line
  let hash = 0;
  for (let i = 0; i < railwayName.length; i++) {
    hash = railwayName.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  const colors = [
    '#ea4335', // red
    '#4285f4', // blue
    '#34a853', // green
    '#fbbc04', // yellow
    '#ff6d00', // orange
    '#46bdc6', // teal
    '#9c27b0', // purple
    '#0097a7', // cyan
  ];
  
  return colors[Math.abs(hash) % colors.length];
}
