import { PlatformVendingMachine } from './PlatformVendingMachine';
import { ParkedTrain } from './ParkedTrain';

/** Original platform atmosphere; the train animation is independent of journey planning. */
export function StationPlatform() {
  return <div className="station-platform">
    <svg aria-hidden="true" className="platform-structure" viewBox="0 0 1440 480" preserveAspectRatio="xMidYMid slice">
      <path d="M0 0H1440V60L0 142Z" fill="#e9eef0" />
      <path d="M0 142 1440 60M0 116 1440 40" stroke="#ced9df" strokeWidth="3" />
      <path d="M760 0 994 86M1080 0 1180 72M1360 0 1380 62" stroke="#c4d1d8" strokeWidth="8" />
      <path d="M861 90V386M1375 68V350" stroke="#d4dde2" strokeWidth="18" />
      <path d="M853 90V386M1367 68V350" stroke="#edf1f2" strokeWidth="4" />
      <path d="M0 420 1440 332V480H0Z" fill="#e8edef" />
      <path d="M0 423 1440 337" stroke="#9db1c0" strokeWidth="3" />
      <path d="M0 442 1440 353" stroke="#d4c88e" strokeWidth="13" />
      <path d="M0 442 1440 353" stroke="#f2e6b5" strokeWidth="7" strokeDasharray="2 9" />
      <path d="M480 480 960 367M1000 480 1180 354M1350 480 1390 342" stroke="#d6dfe4" />
    </svg>
    <PlatformVendingMachine />
    <ParkedTrain />
    <div className="platform-sign" aria-hidden="true">
      <span className="platform-sign-jp">新大阪</span>
      <strong>Shin-Osaka</strong>
      <span className="platform-sign-line"><span>新しい旅へ / YOUR NEXT JOURNEY</span><b>↗</b></span>
    </div>
    <div className="platform-wash" />
  </div>;
}
