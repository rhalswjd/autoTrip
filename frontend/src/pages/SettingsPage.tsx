import { Card } from '../components';

export function SettingsPage() {
  return (
    <div className="content-inner">
      <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', marginBottom: 'var(--space-6)', letterSpacing: '-0.02em' }}>Settings</h1>
      <Card>
        <div style={{ padding: 'var(--space-4)' }}>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Settings will be available in a future update.</p>
        </div>
      </Card>
    </div>
  );
}
