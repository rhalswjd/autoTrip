interface Props { className?: string }

// Keep the established passenger window and door geometry on every carriage.
function PassengerWindows({ positions }: { positions: number[] }) {
  return positions.map(x => <rect key={x} x={x} y="106" width="90" height="61" rx="15" fill="#37566e" />);
}

function PassengerDoor({ x }: { x: number }) {
  return <g><rect x={x} y="68" width="66" height="211" rx="9" stroke="#b6c7d1" strokeWidth="3" /><rect x={x + 17} y="106" width="32" height="60" rx="8" fill="#37566e" /><path d={`M${x + 10} 205h10`} stroke="#879fad" strokeWidth="3" /></g>;
}

function DrivingCar() {
  return <>
    <path d="M28 284C12 280 18 253 40 233C71 202 120 193 185 178C255 162 301 127 346 86C380 54 416 36 478 36H970V296H100C66 296 42 292 28 284Z" fill="#fbfcfc" stroke="#a5bac9" strokeWidth="3" />
    <path d="M245 183C277 145 326 116 390 107C364 130 310 163 259 181Q248 185 245 183Z" fill="#173c59" />
    <path d="M267 172Q315 135 365 118" stroke="#567991" strokeWidth="4" strokeLinecap="round" />
    <path d="M23 263C98 235 175 211 265 204H970V234H270C170 238 93 267 23 279Z" fill="#0759ad" />
    <path d="M42 287Q68 294 100 294H970V296H100Q65 296 42 287Z" fill="#cad7df" />
    <path d="M478 49H970" stroke="#fff" strokeWidth="8" />
    <PassengerWindows positions={[474, 612, 750]} />
    <PassengerDoor x={870} />
    <path d="M93 249 151 232" stroke="#e6cf86" strokeWidth="7" strokeLinecap="round" />
    <path d="M140 302H970" stroke="#466176" strokeWidth="13" />
  </>;
}

/** A complete five-car set. End cars share one silhouette, mirrored at the rear. */
export function Shinkansen({ className }: Props) {
  return <svg className={className} viewBox="0 0 4010 330" fill="none" aria-hidden="true">
    <g data-car="front"><DrivingCar /></g>
    {[970, 1660, 2350].map(x => <g key={x} data-car="passenger" transform={`translate(${x} 0)`}>
      <path d="M0 36H690V296H0Z" fill="#fbfcfc" stroke="#a5bac9" strokeWidth="3" />
      <path d="M0 49H690" stroke="#fff" strokeWidth="8" />
      <path d="M0 204H690V234H0Z" fill="#0759ad" />
      <path d="M0 294H690" stroke="#cad7df" strokeWidth="3" />
      <PassengerWindows positions={[24, 162, 300, 438]} />
      <PassengerDoor x={568} />
      <path d="M0 302H690" stroke="#466176" strokeWidth="13" />
    </g>)}
    <g data-car="rear" transform="translate(4010 0) scale(-1 1)"><DrivingCar /></g>
    {[970, 1660, 2350, 3040].map(x => <path key={x} d={`M${x} 39V293`} stroke="#a9bdcb" strokeWidth="5" />)}
  </svg>;
}
