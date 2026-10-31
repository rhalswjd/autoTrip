import type { Route } from '../../api/types';
import { TransferWizard } from './TransferWizard';

export interface TimetableListProps { route: Route }

export function TimetableList({ route }: TimetableListProps) {
  return <TransferWizard route={route} />;
}
