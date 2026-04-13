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
import { Store, AlertCircle, Rocket } from 'lucide-react';
import ImageUploader from '../components/ImageUploader';
import GeoInput from '../components/GeoInput';
import { submitAssessment } from '../api/kiraApi';

export default function Assessment() {
  const navigate = useNavigate();
  const [images, setImages] = useState([]);
  const [gpsData, setGpsData] = useState({ latitude: null, longitude: null, accuracy: null });
  const [storeName, setStoreName] = useState('');
  const [shopSize, setShopSize] = useState('');
  const [rent, setRent] = useState('');
  const [yearsInOperation, setYearsInOperation] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const gpsValidationError = gpsData.validationError;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Initial validations to avoid wasted backend hits
    if (images.length < 3 || images.length > 5) {
      setError("Please ensure you have uploaded between 3 and 5 images.");
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    
    if (!gpsData.latitude || !gpsData.longitude) {
      setError("GPS Coordinates are required. Please auto-detect or enter them manually.");
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    if (gpsValidationError) {
      setError(gpsValidationError);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    try {
      setIsSubmitting(true);
      
      const formData = new FormData();
      
      // Append Images & Types exactly as expected by FastAPI backend
      images.forEach(img => {
        formData.append('images', img.file);
        formData.append('image_types', img.type);
      });
      
      // Append Location
      formData.append('gps_latitude', parseFloat(gpsData.latitude));
      formData.append('gps_longitude', parseFloat(gpsData.longitude));
      
      if (gpsData.accuracy) {
        formData.append('gps_accuracy', parseFloat(gpsData.accuracy));
      }
      
      // Append Metadata
      if (storeName.trim()) {
        formData.append('store_name', storeName.trim());
      }
      
      // Append Optional AI Inputs
      if (shopSize) {
        formData.append('shop_size', shopSize);
      }
      if (rent) {
        formData.append('rent', parseFloat(rent));
      }
      if (yearsInOperation) {
        formData.append('years_in_operation', parseFloat(yearsInOperation));
      }

      const response = await submitAssessment(formData);
      
      // Successfully processed, redirect format depends on response struct
      // using the sessionId created via API wrapper
      const sessionId = response.data.session_id;
      navigate(`/results/${sessionId}`, { state: { assessment: response.data } });
      
    } catch (err) {
      console.error(err);
      setError(err?.response?.data?.detail || "An error occurred while uploading. Please check API connectivity or use mock mode.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans pb-20">
      <nav className="bg-white border-b border-slate-200 px-6 py-4 flex items-center mb-8">
        <div className="flex items-center gap-2 text-indigo-700 font-bold text-xl cursor-pointer" onClick={() => navigate('/')}>
          <Store className="w-6 h-6" /> KIRA
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-extrabold text-slate-900 mb-2">New Store Assessment</h1>
          <p className="text-slate-600">Provide the baseline details required for our visual and spatial underwriting engine.</p>
        </header>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-xl flex items-start gap-3 mb-8 shadow-sm">
            <AlertCircle className="w-6 h-6 shrink-0 mt-0.5" />
            <div className="font-medium">{error}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <ImageUploader images={images} onImagesChange={setImages} />
          
          <GeoInput gpsData={gpsData} onGpsChange={setGpsData} />
          
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
            <h2 className="text-xl font-bold flex items-center gap-2 mb-4 text-slate-800">
              <Store className="text-indigo-600" /> Additional Details (Optional)
            </h2>
            <div className="grid md:grid-cols-2 gap-4 mb-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-semibold text-slate-700 mb-1">Store Name</label>
                <input
                  type="text"
                  value={storeName}
                  onChange={(e) => setStoreName(e.target.value)}
                  placeholder="e.g., Gupta General Store"
                  className="w-full border border-slate-300 rounded-lg p-3 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-slate-800"
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Shop Size</label>
                <div className="relative">
                  <select
                    value={shopSize}
                    onChange={(e) => setShopSize(e.target.value)}
                    className="appearance-none w-full border border-slate-300 bg-white rounded-lg p-3 pr-10 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-slate-800"
                  >
                    <option value="">Select an option</option>
                    <option value="small">Small (&lt;200 sqft)</option>
                    <option value="medium">Medium (200 - 500 sqft)</option>
                    <option value="large">Large (&gt;500 sqft)</option>
                  </select>
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-500">
                    <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Years in Operation</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={yearsInOperation}
                  onChange={(e) => setYearsInOperation(e.target.value)}
                  placeholder="e.g., 5.5"
                  className="w-full border border-slate-300 rounded-lg p-3 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-slate-800"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-semibold text-slate-700 mb-1">Monthly Rent (INR)</label>
                <input
                  type="number"
                  min="0"
                  value={rent}
                  onChange={(e) => setRent(e.target.value)}
                  placeholder="e.g., 15000"
                  className="w-full border border-slate-300 rounded-lg p-3 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-slate-800"
                />
              </div>
            </div>
            
            <p className="text-xs text-slate-500 mt-2">
              Providing these optional details helps the Fusion Engine provide a more accurate risk assessment and loan size.
            </p>
          </div>

          <div className="pt-4 border-t border-slate-200 flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting || images.length < 3 || !gpsData.latitude || !gpsData.longitude || Boolean(gpsValidationError)}
              className="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-8 py-4 rounded-xl font-bold text-lg transition-all shadow-md w-full sm:w-auto min-w-[200px]"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Running Analysis Engine...
                </>
              ) : (
                <>
                  <Rocket className="w-5 h-5" /> Run Assessment
                </>
              )}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
