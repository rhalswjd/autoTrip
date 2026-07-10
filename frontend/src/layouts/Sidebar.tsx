import { NavLink } from 'react-router-dom';
import { Search, Settings } from 'lucide-react';
import type { ReactNode } from 'react';

interface SidebarProps {
  children?: ReactNode;
}

export function Sidebar({ children }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo">AutoTrip</span>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `sidebar-nav-item ${isActive ? 'active' : ''}`
          }
          end
        >
          <Search className="sidebar-nav-icon" />
          <span>Search</span>
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `sidebar-nav-item ${isActive ? 'active' : ''}`
          }
        >
          <Settings className="sidebar-nav-icon" />
          <span>Settings</span>
        </NavLink>
      </nav>

      {children && (
        <>
          <div className="sidebar-divider" />
          <div className="sidebar-content">{children}</div>
        </>
      )}
    </aside>
  );
}
