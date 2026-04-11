/**
 * KIRA — Assessment Page
 *
 * Store submission form with multi-image upload, GPS input,
 * and optional metadata. Submits to POST /api/v1/assess.
 *
 * Owner: Frontend Lead
 * Phase: 5.2
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ImageUploader from '../components/ImageUploader';
import GeoInput from '../components/GeoInput';
import { submitAssessment } from '../api/kiraApi';

export default function Assessment() {
  const navigate = useNavigate();
  const [images, setImages] = useState([]);
  const [gpsData, setGpsData] = useState({ latitude: null, longitude: null, accuracy: null });
  const [storeName, setStoreName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // TODO: Implement form submission handler
  //   1. Validate 3-5 images uploaded
  //   2. Validate GPS coordinates present
  //   3. Build FormData with images, image_types, gps, store_name
  //   4. Call submitAssessment(formData)
  //   5. Navigate to /results/:sessionId on success
  //   6. Show error state on failure

  return (
    <div>
      <h1>Store Assessment</h1>
      {/* TODO: Build assessment form */}
      <ImageUploader images={images} onImagesChange={setImages} />
      <GeoInput gpsData={gpsData} onGpsChange={setGpsData} />
      {/* TODO: Store name input, submit button, loading state, error display */}
    </div>
  );
}
