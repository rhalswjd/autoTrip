import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode, type RefObject, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';
import { CalendarDays, ChevronLeft, ChevronRight, Clock3 } from 'lucide-react';
import { calendarDate, japanToday, shiftCalendarDay, shiftCalendarMonth } from '../../utils/calendar';
import './DateTimePicker.css';

interface FieldProps { id: string; label: string; value: string; onChange: (value: string) => void }

function PickerPopover({ anchor, label, children, onClose }: {
  anchor: RefObject<HTMLButtonElement | null>; label: string; children: ReactNode; onClose: (restoreFocus: boolean) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0, ready: false });
  useLayoutEffect(() => {
    const positionPopup = () => {
      if (!anchor.current || !ref.current) return;
      const target = anchor.current.getBoundingClientRect();
      const popup = ref.current.getBoundingClientRect();
      setPosition({ left: Math.max(12, Math.min(target.left, window.innerWidth - popup.width - 12)),
        top: Math.max(12, target.bottom + popup.height + 12 <= window.innerHeight ? target.bottom + 8 : target.top - popup.height - 8), ready: true });
    };
    positionPopup();
    window.addEventListener('resize', positionPopup);
    window.addEventListener('scroll', positionPopup, true);
    return () => { window.removeEventListener('resize', positionPopup); window.removeEventListener('scroll', positionPopup, true); };
  }, [anchor]);
  useEffect(() => {
    if (position.ready) ref.current?.querySelector<HTMLButtonElement>('[data-picker-focus="true"]')?.focus({ preventScroll: true });
  }, [position.ready]);
  useEffect(() => {
    const outside = (event: Event) => {
      const target = event.target as Node;
      if (!ref.current?.contains(target) && !anchor.current?.contains(target)) onClose(false);
    };
    const escape = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); onClose(true); }
    };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('focusin', outside);
    document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('focusin', outside); document.removeEventListener('keydown', escape); };
  }, [anchor, onClose]);
  return createPortal(<div ref={ref} className="rail-picker-popover" role="dialog" aria-label={label}
    style={{ top: position.top, left: position.left, visibility: position.ready ? 'visible' : 'hidden' }}>{children}</div>, document.body);
}

const monthNames = Array.from({ length: 12 }, (_, month) => new Intl.DateTimeFormat('en', { month: 'long', timeZone: 'UTC' }).format(new Date(Date.UTC(2026, month, 1))));
const fullDate = (value: string) => new Intl.DateTimeFormat('en', { dateStyle: 'full', timeZone: 'UTC' }).format(calendarDate(value));

function Calendar({ value, onSelect, onClear }: { value: string; onSelect: (value: string) => void; onClear: () => void }) {
  const today = japanToday();
  const [month, setMonth] = useState((value || today).slice(0, 7) + '-01');
  const [active, setActive] = useState(value || today);
  const gridRef = useRef<HTMLDivElement>(null);
  const focusDay = (day: string) => {
    setActive(day); setMonth(day.slice(0, 7) + '-01');
    requestAnimationFrame(() => gridRef.current?.querySelector<HTMLButtonElement>(`[data-date="${day}"]`)?.focus());
  };
  const start = shiftCalendarDay(month, -calendarDate(month).getUTCDay());
  const focusedDay = active.startsWith(month.slice(0, 7)) ? active : month;
  const handleKey = (event: KeyboardEvent, day: string) => {
    const weekday = calendarDate(day).getUTCDay();
    const offsets: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7, Home: -weekday, End: 6 - weekday };
    if (event.key in offsets) { event.preventDefault(); focusDay(shiftCalendarDay(day, offsets[event.key])); }
    if (event.key === 'PageUp' || event.key === 'PageDown') {
      event.preventDefault(); focusDay(shiftCalendarMonth(day, (event.key === 'PageUp' ? -1 : 1) * (event.shiftKey ? 12 : 1)));
    }
  };
  return <>
    <div className="picker-calendar-heading">
      <div><select aria-label="Calendar month" value={calendarDate(month).getUTCMonth()} onChange={event => setMonth(`${month.slice(0, 4)}-${String(Number(event.target.value) + 1).padStart(2, '0')}-01`)}>
        {monthNames.map((name, index) => <option key={name} value={index}>{name}</option>)}
      </select><input aria-label="Calendar year" type="number" min="1" max="9999" value={Number(month.slice(0, 4))} onChange={event => {
        const year = Number(event.target.value); if (year >= 1 && year <= 9999) setMonth(`${String(year).padStart(4, '0')}${month.slice(4)}`);
      }} /></div>
      <button type="button" aria-label="Previous month" onClick={() => setMonth(shiftCalendarMonth(month, -1))}><ChevronLeft size={17} /></button>
      <button type="button" aria-label="Next month" onClick={() => setMonth(shiftCalendarMonth(month, 1))}><ChevronRight size={17} /></button>
    </div>
    <div className="picker-weekdays" aria-hidden="true">{['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(day => <span key={day}>{day}</span>)}</div>
    <div ref={gridRef} className="picker-calendar-grid" role="group" aria-label="Choose travel date">
      {Array.from({ length: 42 }, (_, index) => shiftCalendarDay(start, index)).map(day => <button type="button" key={day} data-date={day}
        tabIndex={day === focusedDay ? 0 : -1} data-picker-focus={day === focusedDay} aria-label={fullDate(day)} aria-pressed={day === value} aria-current={day === today ? 'date' : undefined}
        className={day.slice(0, 7) !== month.slice(0, 7) ? 'outside-month' : ''} onKeyDown={event => handleKey(event, day)} onClick={() => onSelect(day)}>{calendarDate(day).getUTCDate()}</button>)}
    </div>
    <div className="picker-footer"><button type="button" onClick={onClear}>Clear</button><button type="button" onClick={() => onSelect(today)}>Today</button></div>
  </>;
}

export function TravelDatePicker({ id, label, value, onChange }: FieldProps) {
  const [open, setOpen] = useState(false);
  const anchor = useRef<HTMLButtonElement>(null);
  const close = (restore: boolean) => { setOpen(false); if (restore) anchor.current?.focus({ preventScroll: true }); };
  return <div className="rail-picker-field">
    <label id={`${id}-label`} htmlFor={id}>{label}</label>
    <button type="button" id={id} ref={anchor} className="rail-picker-trigger" aria-labelledby={`${id}-label ${id}-value`} aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(previous => !previous)}>
      <span id={`${id}-value`}>{value ? new Intl.DateTimeFormat('en', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(calendarDate(value)) : 'Choose date'}</span><CalendarDays size={18} aria-hidden="true" />
    </button>
    {open && <PickerPopover anchor={anchor} label="Travel date calendar" onClose={close}><Calendar value={value}
      onSelect={day => { onChange(day); close(true); }} onClear={() => { onChange(''); close(true); }} /></PickerPopover>}
  </div>;
}

function TimeColumn({ label, count, value, onChange }: { label: string; count: number; value: number; onChange: (value: number) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const column = ref.current;
    const option = column?.querySelector<HTMLElement>('[aria-selected="true"]');
    if (column && option) column.scrollTop = option.offsetTop - column.offsetTop - (column.clientHeight - option.clientHeight) / 2;
  }, [value]);
  return <div className="picker-time-column"><span>{label}</span><div role="listbox" aria-label={label} ref={ref}>
    {Array.from({ length: count }, (_, index) => <button type="button" role="option" aria-selected={index === value} data-picker-focus={label === 'Hour' && index === value} tabIndex={index === value ? 0 : -1} key={index}
      onClick={() => onChange(index)} onKeyDown={event => {
        const next = event.key === 'ArrowDown' ? (index + 1) % count : event.key === 'ArrowUp' ? (index + count - 1) % count : event.key === 'Home' ? 0 : event.key === 'End' ? count - 1 : null;
        if (next !== null) { event.preventDefault(); onChange(next); (ref.current?.children[next] as HTMLButtonElement)?.focus({ preventScroll: true }); }
      }}>{String(index).padStart(2, '0')}</button>)}
  </div></div>;
}

function TimeOptions({ value, onChange, onClose }: { value: string; onChange: (value: string) => void; onClose: () => void }) {
  const [hour, minute] = (value || '00:00').split(':').map(Number);
  const update = (h: number, m: number) => onChange(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
  return <div>
    <div className="picker-time-heading"><strong>Departure time</strong><span>24-hour · JST</span></div>
    <div className="picker-time-columns"><TimeColumn label="Hour" count={24} value={hour} onChange={h => update(h, minute)} /><span aria-hidden="true">:</span><TimeColumn label="Minute" count={60} value={minute} onChange={m => update(hour, m)} /></div>
    <div className="picker-footer"><button type="button" onClick={() => { onChange(''); onClose(); }}>Clear</button><button type="button" className="picker-done" onClick={onClose}>Done</button></div>
  </div>;
}

export function DepartureTimePicker({ id, label, value, onChange }: FieldProps) {
  const [open, setOpen] = useState(false);
  const anchor = useRef<HTMLButtonElement>(null);
  const description = useId();
  const close = (restore: boolean) => { setOpen(false); if (restore) anchor.current?.focus({ preventScroll: true }); };
  return <div className="rail-picker-field">
    <label id={`${id}-label`} htmlFor={id}>{label}</label>
    <button type="button" id={id} ref={anchor} className="rail-picker-trigger" aria-labelledby={`${id}-label ${id}-value`} aria-describedby={description} aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(previous => !previous)}>
      <span id={`${id}-value`}>{value || 'Choose time'}</span><Clock3 size={18} aria-hidden="true" />
    </button><span id={description} className="sr-only">Japan Standard Time, 24-hour clock</span>
    {open && <PickerPopover anchor={anchor} label="Departure time picker" onClose={close}><TimeOptions value={value} onChange={onChange} onClose={() => close(true)} /></PickerPopover>}
  </div>;
}
