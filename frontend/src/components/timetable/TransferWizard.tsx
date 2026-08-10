import { useState, useEffect } from 'react';
import type { Route, DepartureInfo } from '../../api/types';
import { useSegmentTimetable, useMovement, useToast } from '../../hooks';
import { TimetableCard } from './TimetableCard';
import { TimetableLoading } from './TimetableLoading';
import { TimetableEmpty } from './TimetableEmpty';
import { Button, Input } from '../ui';
import { isTimeAfterOrEqual } from '../../utils/time';
import { CheckCircle, AlertTriangle } from 'lucide-react';
import './Timetable.css';

const TRANSFER_BUFFER_MINUTES = 0;

export interface TransferWizardProps {
  route: Route;
}

export function TransferWizard({ route }: TransferWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedLegs, setSelectedLegs] = useState<Record<number, DepartureInfo>>({});
  
  const [notionUrl, setNotionUrl] = useState('');
  const [urlError, setUrlError] = useState('');
  
  const { mutate, isPending, isSuccess, data } = useMovement();
  const { success, error: toastError } = useToast();

  const isSummaryStep = currentStep === route.segments.length;
  
  // API call for current segment
  const { data: timetable, isLoading, isError, error } = useSegmentTimetable(
    !isSummaryStep ? route.id : null,
    !isSummaryStep ? currentStep : null
  );

  useEffect(() => {
    if (isError && error) {
      toastError('Timetable Error', error.message || 'Failed to load timetable.');
    }
  }, [isError, error, toastError]);

  useEffect(() => {
    if (isSuccess && data) {
      success('Movement Created', 'Successfully added to Notion!');
    }
  }, [isSuccess, data, success]);

  const validateUrl = (url: string) => {
    if (!url) return true;
    if (!url.includes('notion.so') && !url.includes('notion.site') && !url.includes('app.notion.com')) return false;
    return true;
  };

  const handleNext = () => {
    if (currentStep < route.segments.length) {
      setCurrentStep(c => c + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(c => c - 1);
    }
  };
  
  const handleSelect = (departure: DepartureInfo) => {
    setSelectedLegs(prev => ({ ...prev, [currentStep]: departure }));
  };

  const handleSubmit = () => {
    if (notionUrl && !validateUrl(notionUrl)) {
      setUrlError('올바른 Notion 페이지 링크를 입력해 주세요.');
      return;
    }
    setUrlError('');

    // Map selectedLegs to LegSelection
    const legs = route.segments.map((_, index) => {
      const legDeparture = selectedLegs[index];
      return {
        segment_index: index,
        departure_station: route.stations[index].name,
        arrival_station: route.stations[index + 1].name,
        departure_time: legDeparture.time,
        arrival_time: legDeparture.arrival_time,
        transport_name: legDeparture.train_name,
        platform: legDeparture.platform ? parseInt(legDeparture.platform as string, 10) : undefined,
        fare: undefined // We don't have per-leg fare currently
      };
    });

    const firstLeg = selectedLegs[0];
    const lastLeg = selectedLegs[route.segments.length - 1];

    mutate(
      {
        route_id: route.id,
        selected_departure_time: firstLeg.time,
        selected_arrival_time: lastLeg.arrival_time || 'N/A (Calculated by backend)',
        departure_station: route.departure_station,
        arrival_station: route.arrival_station,
        notion_page_url: notionUrl || undefined,
        legs: legs,
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
      <div className="timetable-container" style={{ padding: '24px', textAlign: 'center' }}>
        <CheckCircle className="movement-success-icon" style={{ margin: '0 auto', display: 'block', marginBottom: '16px' }} />
        <h4 className="movement-success-title">Success</h4>
        <p className="movement-success-desc">
          환승 여정이 Notion에 저장되었습니다.
        </p>
        <div style={{ marginTop: '16px' }}>
          {data?.notion_url && (
            <Button
              variant="secondary"
              onClick={() => window.open(data.notion_url, '_blank')}
            >
              Open Notion
            </Button>
          )}
        </div>
      </div>
    );
  }

  // Filter departures for current step based on previous arrival time
  let availableDepartures = timetable?.weekday || [];
  let prevArrivalTime = '';
  
  if (currentStep > 0) {
    const prevLeg = selectedLegs[currentStep - 1];
    prevArrivalTime = prevLeg?.arrival_time || '';
    if (prevArrivalTime) {
      availableDepartures = availableDepartures.filter((dep: DepartureInfo) => 
        isTimeAfterOrEqual(dep.time, prevArrivalTime, TRANSFER_BUFFER_MINUTES)
      );
    }
  }

  return (
    <div className="timetable-container">
      <div className="wizard-header" style={{ marginBottom: '24px' }}>
        <h3 className="timetable-title" style={{ marginBottom: '12px' }}>환승 시간표 선택</h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {Array.from({ length: route.segments.length + 1 }).map((_, idx) => {
            const isActive = currentStep === idx;
            const isCompleted = currentStep > idx;
            let label = idx < route.segments.length ? `${idx + 1}구간` : '확인';
            return (
              <div key={idx} style={{ 
                display: 'flex', alignItems: 'center', 
                color: isActive ? 'var(--primary-color)' : isCompleted ? 'var(--success-color)' : 'var(--text-secondary)',
                fontWeight: isActive ? 600 : 400,
                fontSize: '14px'
              }}>
                {isCompleted ? '✓ ' : isActive ? '● ' : '○ '}
                {label}
                {idx < route.segments.length && <span style={{ margin: '0 8px', color: 'var(--border-color)' }}>-</span>}
              </div>
            );
          })}
        </div>
      </div>

      {!isSummaryStep ? (
        <div className="wizard-step-content">
          <div style={{ marginBottom: '16px', padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
            <div style={{ fontWeight: 600, marginBottom: '4px' }}>
              {route.stations[currentStep].name} → {route.stations[currentStep + 1].name}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              {route.segments[currentStep].railway_name}
            </div>
          </div>
          
          {currentStep > 0 && !prevArrivalTime && (
             <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px', background: 'var(--warning-bg, #fff3cd)', color: 'var(--warning-text, #856404)', borderRadius: '8px', marginBottom: '16px' }}>
               <AlertTriangle size={16} />
               <span style={{ fontSize: '13px' }}>이전 열차의 도착 시간을 알 수 없어, 이후 모든 시간표가 표시됩니다. 환승 시간을 직접 확인해주세요.</span>
             </div>
          )}

          {isLoading ? (
            <TimetableLoading />
          ) : availableDepartures.length === 0 ? (
            <TimetableEmpty />
          ) : (
            <div className="timetable-list" role="listbox">
              {availableDepartures.map((departure: DepartureInfo) => (
                <TimetableCard
                  key={departure.id}
                  departure={departure}
                  isSelected={selectedLegs[currentStep]?.id === departure.id}
                  onClick={handleSelect}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="wizard-summary-content">
          <h4 style={{ marginBottom: '16px' }}>여정 확인</h4>
          {route.segments.map((_, idx) => {
            const leg = selectedLegs[idx];
            return (
              <div key={idx} style={{ marginBottom: '16px', padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px', textAlign: 'left' }}>
                <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '8px', color: 'var(--primary-color)' }}>[{idx + 1}구간] {route.stations[idx].name} → {route.stations[idx + 1].name}</div>
                <div style={{ fontSize: '13px' }}>{leg?.time} → {leg?.arrival_time || '?'}</div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{leg?.train_name}</div>
              </div>
            );
          })}
          
          <div className="movement-dialog-input-section" style={{ marginTop: '24px', textAlign: 'left' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
              Notion 여행 페이지
            </label>
            <Input 
              type="text" 
              placeholder="Notion 페이지 링크를 붙여넣어 주세요" 
              value={notionUrl}
              onChange={(e) => {
                setNotionUrl(e.target.value);
                if (urlError) setUrlError('');
              }}
              error={!!urlError}
            />
            {urlError ? (
              <p style={{ fontSize: '12px', color: 'var(--danger-color)', marginTop: '4px' }}>
                {urlError}
              </p>
            ) : (
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Notion에서 여행 페이지를 열고 링크를 복사해 붙여넣으면 됩니다.
              </p>
            )}
          </div>
        </div>
      )}

      <div className="wizard-actions" style={{ 
        display: 'flex', 
        justifyContent: 'flex-end', 
        gap: '8px', 
        marginTop: '24px',
        position: 'sticky',
        bottom: '0',
        background: 'var(--bg-primary, #ffffff)',
        padding: '16px 0',
        borderTop: '1px solid var(--border-color)',
        zIndex: 10
      }}>
        {currentStep > 0 && (
          <Button variant="ghost" onClick={handlePrev} disabled={isPending}>
            이전
          </Button>
        )}
        {!isSummaryStep ? (
          <Button 
            variant="primary" 
            onClick={handleNext} 
            disabled={!selectedLegs[currentStep]}
          >
            다음
          </Button>
        ) : (
          <Button 
            variant="primary" 
            onClick={handleSubmit} 
            loading={isPending}
          >
            Notion에 저장
          </Button>
        )}
      </div>
    </div>
  );
}
