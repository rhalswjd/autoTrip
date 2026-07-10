import { useState } from 'react';
import { SearchBox, EmptyView } from '../components';

export function SearchPage() {
  const [query, setQuery] = useState('');

  return (
    <div className="content-inner">
      <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', marginBottom: 'var(--space-6)', letterSpacing: '-0.02em' }}>Search Routes</h1>
      <SearchBox
        value={query}
        onChange={setQuery}
        placeholder="Where are you going?"
        autoFocus
      />
      <div style={{ marginTop: 'var(--space-10)' }}>
        <EmptyView
          title="Search for a route"
          description="Enter departure and arrival stations to find available train routes."
        />
      </div>
    </div>
  );
}
