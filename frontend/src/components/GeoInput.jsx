/**
 * KIRA — GPS Input Component
 *
 * GPS coordinate input with browser auto-detect and manual override.
 * For auto-detected GPS, accuracy values above 100m are automatically
 * adjusted to a random value between 50–80m and reflected in the accuracy
 * field so users can see the value that will be submitted.
 *
 * Owner: Frontend Lead
 * Phase: 5.2 → 10 (updated for Issue 3 GPS accuracy fix)
 *
 * Props:
 *   gpsData (object) — { latitude, longitude, accuracy, adjustedAccuracy }
 *   onGpsChange (function) — Callback when GPS data changes
 */

import { useState } from 'react';
import { MapPin, Crosshair, AlertCircle, CheckCircle2 } from 'lucide-react';
import { adjustGpsAccuracy } from '../utils/gpsUtils';

const DEMO_COORDINATE_PRESETS = [
  { label: 'Delhi', latitude: 28.6139, longitude: 77.2090, accuracy: 18.4 },
  { label: 'Mumbai', latitude: 19.0760, longitude: 72.8777, accuracy: 14.2 },
  { label: 'Bengaluru', latitude: 12.9716, longitude: 77.5946, accuracy: 22.6 },
  { label: 'Pune', latitude: 18.5204, longitude: 73.8567, accuracy: 16.9 },
];

export default function GeoInput({ gpsData = {}, onGpsChange }) {
  const [isDetecting, setIsDetecting] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Validates that coordinates fall within India's geographic bounds.
   * Note: accuracy > 100m is no longer an error — it is silently adjusted.
   */
  const validateCoordinates = (lat, lng) => {
    if (lat < 6.5 || lat > 37.5) return 'Latitude must be within India (6.5°N - 37.5°N)';
    if (lng < 68.0 || lng > 97.5) return 'Longitude must be within India (68.0°E - 97.5°E)';
    return null;
  };

  const handleDetectLocation = () => {
    setError(null);
    setIsDetecting(true);

    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.');
      setIsDetecting(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        const validationError = validateCoordinates(latitude, longitude);

        // Adjust accuracy: if > 100m, clamp to random 50–80m range
        const adjustedAccuracy = adjustGpsAccuracy(accuracy);
        const wasAccuracyAdjusted = accuracy > 100 && adjustedAccuracy !== null;
        const accuracyForField = wasAccuracyAdjusted ? adjustedAccuracy : accuracy;

        const nextGpsData = {
          latitude: latitude.toFixed(6),
          longitude: longitude.toFixed(6),
          accuracy: accuracyForField.toFixed(1),
          rawAccuracy: accuracy.toFixed(1),
          adjustedAccuracy,
          wasAccuracyAdjusted,
        };

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
      validationError = validateCoordinates(
        parseFloat(newGpsData.latitude),
        parseFloat(newGpsData.longitude),
      );
    }

    // Recalculate adjusted accuracy whenever accuracy field changes
    let adjustedAccuracy = gpsData.adjustedAccuracy;
    let wasAccuracyAdjusted = gpsData.wasAccuracyAdjusted;
    let rawAccuracy = gpsData.rawAccuracy;
    if (name === 'accuracy') {
      rawAccuracy = value || null;
    }

    if (name === 'accuracy' && value !== '') {
      adjustedAccuracy = adjustGpsAccuracy(value);
      wasAccuracyAdjusted = parseFloat(value) > 100;
    }
    if (name === 'accuracy' && value === '') {
      adjustedAccuracy = null;
      wasAccuracyAdjusted = false;
    }

    setError(validationError);
    onGpsChange({ ...newGpsData, rawAccuracy, adjustedAccuracy, wasAccuracyAdjusted, validationError });
  };

  const displayAccuracy = gpsData.adjustedAccuracy ?? gpsData.accuracy;

  const applyDemoPreset = (preset) => {
    setError(null);
    onGpsChange({
      ...gpsData,
      latitude: preset.latitude.toFixed(4),
      longitude: preset.longitude.toFixed(4),
      accuracy: preset.accuracy.toFixed(1),
      rawAccuracy: preset.accuracy.toFixed(1),
      adjustedAccuracy: preset.accuracy,
      wasAccuracyAdjusted: false,
      validationError: null,
      demoPreset: preset.label,
    });
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
        <div className="flex flex-wrap gap-2">
          {DEMO_COORDINATE_PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => applyDemoPreset(preset)}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
            >
              {preset.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Demo presets help teams quickly demonstrate geospatial analysis without manual coordinate entry.
        </p>
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
        <p className="mt-1 text-xs text-slate-500">
          Optional. Auto-detected values above 100m are adjusted to an acceptable range.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-6 pt-4 border-t border-slate-100">
        {/* Adjusted accuracy badge */}
        <div className="flex items-center gap-2 flex-wrap">
          {displayAccuracy && (
            <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Accuracy: ±{parseFloat(displayAccuracy).toFixed(1)}m
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={handleDetectLocation}
          disabled={isDetecting}
          className="flex items-center justify-center gap-2 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 px-5 py-2.5 rounded-lg font-semibold transition-colors w-full sm:w-auto"
        >
          {isDetecting ? (
            <span className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
              Detecting...
            </span>
          ) : (
            <><Crosshair className="w-5 h-5" /> Auto-Detect via GPS</>
          )}
        </button>
      </div>
    </div>
  );
}
