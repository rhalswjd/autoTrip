/** A small, unbranded background detail, occluded by the parked train. */
export function PlatformVendingMachine() {
  return <svg className="platform-vending" viewBox="0 0 100 180" aria-hidden="true">
    <path d="M7 9 83 3 96 12V174L83 180H7Z" fill="#c7d6df" />
    <rect x="7" y="9" width="76" height="168" rx="4" fill="#f8fafb" stroke="#9eb4c3" />
    <path d="M7 9H83V28H7Z" fill="#215d91" />
    <text x="15" y="22" fontSize="8" fill="white" letterSpacing="1">DRINKS / 飲料</text>
    <rect x="14" y="34" width="62" height="83" rx="2" fill="#dce9f0" />
    {[43, 68, 93].map(y => <g key={y}>{[22, 39, 56].map((x, i) => <g key={x}>
      <rect x={x} y={y} width="10" height="16" rx="2" fill={['#8cabb6', '#d6ad8e', '#8caea0'][i]} />
      <path d={`M${x + 2} ${y}v-3h6v3`} fill="#f7fafb" />
      <path d={`M${x} ${y + 9}h10`} stroke="#f9fcfc" strokeWidth="4" />
    </g>)}<path d={`M18 ${y + 20}h52`} stroke="#8da9bb" strokeWidth="2" /></g>)}
    <rect x="16" y="137" width="48" height="23" rx="3" fill="#25475d" />
    <rect x="66" y="122" width="10" height="6" rx="2" fill="#3b6b8b" />
    <circle cx="71" cy="135" r="3" fill="#849aaa" />
    <path d="M16 176v4M73 176v4" stroke="#557184" strokeWidth="5" />
  </svg>;
}
