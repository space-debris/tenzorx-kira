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
import { MapPin, Crosshair, AlertCircle } from 'lucide-react';

export default function GeoInput({ gpsData = {}, onGpsChange }) {
  const [isDetecting, setIsDetecting] = useState(false);
  const [error, setError] = useState(null);

  const validateGps = (lat, lng, accuracy) => {
    if (lat < 6.5 || lat > 37.5) return 'Latitude must be within India (6.5°N - 37.5°N)';
    if (lng < 68.0 || lng > 97.5) return 'Longitude must be within India (68.0°E - 97.5°E)';
    if (accuracy !== undefined && accuracy !== null && accuracy !== '' && Number(accuracy) > 100) {
      return 'GPS accuracy must be 100 meters or better.';
    }
    return null;
  };

  const handleDetectLocation = () => {
    setError(null);
    setIsDetecting(true);

    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      setIsDetecting(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        const nextGpsData = {
          latitude: latitude.toFixed(6),
          longitude: longitude.toFixed(6),
          accuracy: accuracy.toFixed(1),
        };
        const validationError = validateGps(latitude, longitude, accuracy);

        setError(validationError);
        onGpsChange({ ...nextGpsData, validationError });
        setIsDetecting(false);
      },
      (err) => {
        setError(`Unable to retrieve your location: ${err.message}`);
        setIsDetecting(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  const handleManualChange = (e) => {
    const { name, value } = e.target;
    const newGpsData = { ...gpsData, [name]: value };

    let validationError = null;
    if (newGpsData.latitude && newGpsData.longitude) {
      validationError = validateGps(
        parseFloat(newGpsData.latitude),
        parseFloat(newGpsData.longitude),
        newGpsData.accuracy,
      );
    }

    setError(validationError);
    onGpsChange({ ...newGpsData, validationError });
  };

  return (
    <div className="bg-white border text-left border-slate-200 rounded-xl p-6 shadow-sm mb-6">
      <h2 className="text-xl font-bold flex items-center gap-2 mb-4 text-slate-800">
        <MapPin className="text-indigo-600" /> Store Location Details
      </h2>
      
      <p className="text-sm text-slate-600 mb-6">
        We use GPS coordinates to estimate catchment population, footfall potential, and local competition. KIRA requires coordinates strictly within India.
      </p>

      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-lg flex items-start gap-2 mb-4 text-sm font-medium">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-1">Latitude</label>
          <input
            type="number"
            step="any"
            name="latitude"
            value={gpsData.latitude || ''}
            onChange={handleManualChange}
            placeholder="e.g. 19.0760"
            className="w-full border border-slate-300 rounded-lg p-3 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-1">Longitude</label>
          <input
            type="number"
            step="any"
            name="longitude"
            value={gpsData.longitude || ''}
            onChange={handleManualChange}
            placeholder="e.g. 72.8777"
            className="w-full border border-slate-300 rounded-lg p-3 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
            required
          />
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-semibold text-slate-700 mb-1">GPS Accuracy (meters)</label>
        <input
          type="number"
          step="0.1"
          min="0"
          name="accuracy"
          value={gpsData.accuracy || ''}
          onChange={handleManualChange}
          placeholder="e.g. 12.5"
          className="w-full border border-slate-300 rounded-lg p-3 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
        />
        <p className="mt-1 text-xs text-slate-500">Optional, but values above 100m are rejected by the underwriting API.</p>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-6 pt-4 border-t border-slate-100">
        {gpsData.accuracy && (
          <div className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full w-max">
            Accuracy: ±{gpsData.accuracy}m
          </div>
        )}
        <button
          type="button"
          onClick={handleDetectLocation}
          disabled={isDetecting}
          className="flex items-center justify-center gap-2 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 px-5 py-2.5 rounded-lg font-semibold transition-colors w-full sm:w-auto"
        >
          {isDetecting ? (
            <span className="flex items-center gap-2"><div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div> Detecting...</span>
          ) : (
            <><Crosshair className="w-5 h-5" /> Auto-Detect via GPS</>
          )}
        </button>
      </div>
    </div>
  );
}
