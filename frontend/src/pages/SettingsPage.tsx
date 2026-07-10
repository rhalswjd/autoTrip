import { Settings as SettingsIcon } from 'lucide-react';
import { Sidebar } from '../layouts/Sidebar';

export function SettingsPage() {
  return (
    <div className="split-view">
      <Sidebar />

      <main className="detail-panel">
        <div className="detail-panel-inner">
          <div className="placeholder">
            <SettingsIcon className="placeholder-icon" />
            <span className="placeholder-text">
              Settings will be available here
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
