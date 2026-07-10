import { useState, useRef, useEffect } from 'react';
import type { ReactNode } from 'react';
import { Portal } from './Portal';
import { useEscapeKey } from '../../utils/keyboard';
import './Tooltip.css';

export interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  delayMs?: number;
}

export function Tooltip({ content, children, delayMs = 400 }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<number | undefined>(undefined);

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setPosition({
          top: rect.bottom + window.scrollY + 4,
          left: rect.left + window.scrollX + rect.width / 2,
        });
        setIsVisible(true);
      }
    }, delayMs);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(false);
  };

  useEscapeKey(() => setIsVisible(false), isVisible);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return (
    <>
      <div
        ref={containerRef}
        className="tooltip-container"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleMouseEnter}
        onBlur={handleMouseLeave}
      >
        {children}
      </div>
      {isVisible && (
        <Portal>
          <div
            className="tooltip-portal"
            style={{
              top: position.top,
              left: position.left,
              transform: 'translateX(-50%)',
            }}
            role="tooltip"
          >
            <div className="tooltip-content">{content}</div>
          </div>
        </Portal>
      )}
    </>
  );
}
