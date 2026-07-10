import './Loading.css';

interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export function Loading({ size = 'md', label }: LoadingProps) {
  return (
    <div className="loading">
      <div className={`loading-spinner loading-${size}`} />
      {label && <span className="loading-label">{label}</span>}
    </div>
  );
}
