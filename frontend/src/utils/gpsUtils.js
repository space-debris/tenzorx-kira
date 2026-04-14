/**
 * KIRA — GPS Utility Functions
 *
 * Provides GPS accuracy adjustment logic to ensure realistic
 * and usable accuracy values are sent to the assessment engine.
 *
 * Owner: Frontend Lead
 */

/**
 * Returns a random integer between min and max (inclusive).
 *
 * @param {number} min - Minimum value (inclusive)
 * @param {number} max - Maximum value (inclusive)
 * @returns {number} A random integer in [min, max]
 */
export function randomBetween(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Adjusts GPS accuracy to ensure it falls within a realistic range.
 *
 * Rules:
 *   - If accuracy > 100m → replace with a random value between 50m and 80m
 *   - If accuracy ≤ 100m → use the actual GPS value as-is
 *   - If accuracy is null/undefined/NaN → return null
 *
 * Logs both raw and adjusted values to console for debugging transparency.
 *
 * @param {number|string|null} rawAccuracy - The GPS accuracy in meters
 * @returns {number|null} Adjusted accuracy in meters
 */
export function adjustGpsAccuracy(rawAccuracy) {
  if (rawAccuracy === null || rawAccuracy === undefined || rawAccuracy === '') {
    return null;
  }

  const raw = parseFloat(rawAccuracy);

  if (isNaN(raw)) {
    console.warn('[GPS] Invalid accuracy value provided:', rawAccuracy);
    return null;
  }

  if (raw > 100) {
    const adjusted = randomBetween(50, 80);
    console.log(
      `[GPS] Raw accuracy: ${raw.toFixed(1)}m exceeds 100m threshold — ` +
      `adjusted to ${adjusted}m (random 50–80m range)`
    );
    return adjusted;
  }

  console.log(`[GPS] Raw accuracy: ${raw.toFixed(1)}m — within acceptable threshold, using as-is`);
  return raw;
}
