import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { FixturePreview } from './FixturePreview';

createRoot(document.getElementById('root')!).render(<StrictMode><FixturePreview /></StrictMode>);
