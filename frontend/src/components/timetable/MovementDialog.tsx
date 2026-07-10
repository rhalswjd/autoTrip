import { useEffect } from 'react';
import type { Route, DepartureInfo } from '../../api/types';
import { Modal, Button } from '../ui';
import { useMovement, useToast } from '../../hooks';
import { CheckCircle } from 'lucide-react';
import './Timetable.css';

export interface MovementDialogProps {
  route: Route;
  departure: DepartureInfo;
  isOpen: boolean;
  onClose: () => void;
}

export function MovementDialog({ route, departure, isOpen, onClose }: MovementDialogProps) {
  const { mutate, isPending, isSuccess, data } = useMovement();
  const { success, error: toastError } = useToast();
  
  // Calculate a mock arrival time based on route.total_duration for the API requirement
  // Since we don't have real math here, we just pass the duration or a dummy string.
  // The backend MovementRequest expects `selected_arrival_time`
  const mockArrivalTime = 'N/A (Calculated by backend)'; 

  useEffect(() => {
    if (isSuccess && data) {
      success('Movement Created', 'Successfully added to Notion!');
    }
  }, [isSuccess, data, success]);

  const handleConfirm = () => {
    mutate(
      {
        route_id: route.id,
        selected_departure_time: departure.time,
        selected_arrival_time: mockArrivalTime,
        departure_station: route.departure_station,
        arrival_station: route.arrival_station,
      },
      {
        onError: (err: Error) => {
          toastError('Movement Failed', err.message || 'Could not create movement');
        },
      }
    );
  };

  if (isSuccess) {
    return (
      <Modal isOpen={isOpen} onClose={onClose} aria-label="Movement Created">
        <div className="movement-success-content">
          <CheckCircle className="movement-success-icon" />
          <h4 className="movement-success-title">Success</h4>
          <p className="movement-success-desc">
            Your trip has been added to Notion.
          </p>
          <div style={{ marginTop: '16px' }}>
            {data?.notion_url && (
              <Button
                variant="secondary"
                onClick={() => window.open(data.notion_url, '_blank')}
                style={{ marginRight: '8px' }}
              >
                Open Notion
              </Button>
            )}
            <Button variant="primary" onClick={onClose}>
              Done
            </Button>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} aria-label="Confirm Movement">
      <div className="movement-dialog-content">
        <div className="movement-dialog-header">
          <h4 className="movement-dialog-title">Add to Notion</h4>
          <p className="movement-dialog-desc">
            Would you like to save this route schedule as a movement?
          </p>
        </div>

        <div className="movement-dialog-details">
          <div className="movement-detail-row">
            <span className="movement-detail-label">Route</span>
            <span className="movement-detail-value">{route.railway_name}</span>
          </div>
          <div className="movement-detail-row">
            <span className="movement-detail-label">From</span>
            <span className="movement-detail-value">{route.departure_station}</span>
          </div>
          <div className="movement-detail-row">
            <span className="movement-detail-label">To</span>
            <span className="movement-detail-value">{route.arrival_station}</span>
          </div>
          <div className="movement-detail-row">
            <span className="movement-detail-label">Departure</span>
            <span className="movement-detail-value">{departure.time}</span>
          </div>
          <div className="movement-detail-row">
            <span className="movement-detail-label">Train</span>
            <span className="movement-detail-value">{departure.train_name}</span>
          </div>
        </div>

        <div className="movement-dialog-actions">
          <Button variant="ghost" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleConfirm} loading={isPending}>
            Confirm
          </Button>
        </div>
      </div>
    </Modal>
  );
}
