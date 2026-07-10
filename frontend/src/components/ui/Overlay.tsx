import './Overlay.css';

export interface OverlayProps {
  onClick?: () => void;
  className?: string;
}

export function Overlay({ onClick, className = '' }: OverlayProps) {
  return (
    <div
      className={`overlay ${className}`}
      onClick={onClick}
      aria-hidden="true"
    />
  );
}
