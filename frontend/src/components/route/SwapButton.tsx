import { ArrowDownUp } from 'lucide-react';
import { IconButton } from '../ui';
import './Route.css';

export interface SwapButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

export function SwapButton({ onClick, disabled }: SwapButtonProps) {
  return (
    <div className="swap-button-wrapper">
      <IconButton
        className="swap-button"
        icon={<ArrowDownUp size={16} />}
        onClick={onClick}
        disabled={disabled}
        aria-label="Swap stations"
        title="Swap stations"
      />
    </div>
  );
}
