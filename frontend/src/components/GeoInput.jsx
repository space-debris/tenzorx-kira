/**
 * KIRA — GPS Input Component
 *
 * GPS coordinate input with browser auto-detect and manual override.
 *
 * Owner: Frontend Lead
 * Phase: 5.2
 *
 * Props:
 *   gpsData (object) — { latitude, longitude, accuracy }
 *   onGpsChange (function) — Callback when GPS data changes
 */

import { useState } from 'react';

export default function GeoInput({ gpsData = {}, onGpsChange }) {
  // TODO: Implement GPS input with:
  //   - "Auto-detect location" button using navigator.geolocation
  //   - Manual latitude/longitude input fields
  //   - GPS accuracy display
  //   - Map preview (optional, using a static map image)
  //   - Validation: coordinates within India (6.5-37.5°N, 68-97.5°E)
  //   - Loading state while detecting GPS

  return (
    <div>
      {/* TODO: Implement GPS input UI */}
      <p>GPS Input — Enter or auto-detect store location</p>
    </div>
  );
}
