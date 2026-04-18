/**
 * KIRA — Assessment Page
 *
 * Store submission form with multi-image upload, GPS input,
 * and optional metadata. Submits to POST /api/v1/assess.
 *
 * Props: None (always rendered inside LenderShell via /app/tools/assessment)
 *     
 *
 * Owner: Frontend Lead
 * Phase: 5.2 → 10 (updated for Issues 2 & 3: auth guard, GPS accuracy)
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Store, AlertCircle, Rocket, User, Phone, Loader2, CheckCircle2, TrendingUp } from 'lucide-react';
import ImageUploader from '../components/ImageUploader';
import GeoInput from '../components/GeoInput';
import StatementUploadCard from '../components/StatementUploadCard';
import { submitAssessment, getCasePrefillData } from '../api/kiraApi';
import { adjustGpsAccuracy } from '../utils/gpsUtils';
import { useAuth } from '../context/useAuth';

const SHOP_SIZE_PRESETS = [
  { label: 'Small', value: '100' },
  { label: 'Medium', value: '250' },
  { label: 'Large', value: '500' },
];

export default function Assessment() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const caseId = searchParams.get('caseId');
  const { user, org } = useAuth();

  const [images, setImages] = useState([]);
  const [gpsData, setGpsData] = useState({ latitude: null, longitude: null, accuracy: null });
  const [storeName, setStoreName] = useState('');
  const [ownerName, setOwnerName] = useState('');
  const [ownerMobile, setOwnerMobile] = useState('');
  const [shopSize, setShopSize] = useState('');
  const [rent, setRent] = useState('');
  const [yearsInOperation, setYearsInOperation] = useState('');

  const [isPrefilling, setIsPrefilling] = useState(false);
  const [prefillSuccess, setPrefillSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [monthlyRevenueHint, setMonthlyRevenueHint] = useState(null);
  const [monthlyRevenueHintSource, setMonthlyRevenueHintSource] = useState('');

  const gpsValidationError = gpsData.validationError;
  const imageCountValid = images.length >= 3 && images.length <= 5;
  const gpsValid = Boolean(gpsData.latitude && gpsData.longitude && !gpsValidationError);
  const canSubmit = !isSubmitting && imageCountValid && gpsValid;

  useEffect(() => {
    if (!caseId) return;

    async function loadPrefill() {
      try {
        setIsPrefilling(true);
        const res = await getCasePrefillData(caseId);
        const data = res.data;

        if (data.store_name) setStoreName(data.store_name);
        if (data.owner_name) setOwnerName(data.owner_name);
        if (data.owner_mobile) setOwnerMobile(data.owner_mobile);
        if (data.shop_size) setShopSize(data.shop_size);
        if (data.rent) setRent(data.rent.toString());
        if (data.years_in_operation) setYearsInOperation(data.years_in_operation.toString());
        if (data.monthly_revenue_hint) setMonthlyRevenueHint(Number(data.monthly_revenue_hint));
        if (data.monthly_revenue_hint_source) setMonthlyRevenueHintSource(data.monthly_revenue_hint_source);

        setPrefillSuccess(true);
      } catch (err) {
        console.error('Failed to prefill case data:', err);
        setError('Failed to load case data. You can proceed manually.');
      } finally {
        setIsPrefilling(false);
      }
    }
    loadPrefill();
  }, [caseId]);

  const handleStatementUpload = (payload) => {
    setMonthlyRevenueHint(50000); // Mock revenue hint from statement
    setMonthlyRevenueHintSource(payload.source_kind || 'statement');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Initial validations to avoid wasted backend hits
    if (images.length < 3 || images.length > 5) {
      setError('Please ensure you have uploaded between 3 and 5 images.');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    if (!gpsData.latitude || !gpsData.longitude) {
      setError('GPS Coordinates are required. Please auto-detect or enter them manually.');
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
      images.forEach((img) => {
        formData.append('images', img.file);
        formData.append('image_types', img.type);
      });

      // Append Location
      formData.append('gps_latitude', parseFloat(gpsData.latitude));
      formData.append('gps_longitude', parseFloat(gpsData.longitude));

      // GPS Accuracy
      if (gpsData.accuracy) {
        const finalAccuracy = gpsData.adjustedAccuracy ?? adjustGpsAccuracy(gpsData.accuracy);
        if (finalAccuracy !== null) {
          formData.append('gps_accuracy', finalAccuracy);
        }
      }

      // Append Metadata
      if (storeName.trim()) formData.append('store_name', storeName.trim());
      if (ownerName.trim()) formData.append('owner_name', ownerName.trim());
      if (ownerMobile.trim()) formData.append('owner_mobile', ownerMobile.trim());

      // Append Optional AI Inputs
      if (shopSize) formData.append('shop_size', shopSize);
      if (rent) formData.append('rent', parseFloat(rent));
      if (yearsInOperation) formData.append('years_in_operation', parseFloat(yearsInOperation));

      // Auto case context
      if (caseId) {
        formData.append('case_id', caseId);
      } else if (org?.id && user?.id) {
        formData.append('org_id', org.id);
        formData.append('created_by_user_id', user.id);
      }

      const response = await submitAssessment(formData);

      const newCaseId = response.data?.case_id;
      if (newCaseId) {
        navigate(`/app/cases/${newCaseId}`);
      } else {
        // Fallback if case creation failed or wasn't expected
        const sessionId = response.data.session_id;
        navigate(`/app/tools/assessment/${sessionId}`, { state: { assessment: response.data } });
      }
    } catch (err) {
      console.error(err);
      setError(
        err?.response?.data?.detail ||
        'An error occurred while uploading. Please check API connectivity and backend logs.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isPrefilling) {
    return (
      <div className="flex flex-col items-center justify-center p-32">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin mb-4" />
        <p className="text-slate-500 font-medium">Loading case details...</p>
      </div>
    );
  }

  const content = (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 animate-fade-in space-y-6">
      <header className="relative overflow-hidden rounded-3xl border border-slate-200 bg-linear-to-br from-white via-slate-50 to-primary-50/40 p-6 sm:p-8 shadow-sm">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-linear-to-r from-primary-500 via-indigo-400 to-cyan-400" />
        <div className="space-y-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-slate-900 mb-2">
              {caseId ? 'Continue Store Assessment' : 'New Store Assessment'}
            </h1>
            <p className="text-slate-600 max-w-3xl">
              Capture storefront imagery, precise location, and borrower context for visual + spatial underwriting in one guided flow.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold ${imageCountValid ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700'}`}>
              {images.length}/5 images (min 3)
            </span>
            <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold ${gpsValid ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-100 text-slate-700'}`}>
              GPS required
            </span>
            <span className="inline-flex items-center rounded-full border border-primary-200 bg-primary-50 px-3 py-1 text-xs font-bold text-primary-700">
              AI Risk + Loan Sizing
            </span>
          </div>
        </div>
      </header>

      {prefillSuccess && caseId && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-4 rounded-2xl flex items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <div className="font-medium text-sm">
              Assessment linked to case: <span className="font-bold">{storeName || 'Unknown Store'}</span>
            </div>
          </div>
          {!isSubmitting && (
            <Link to={`/app/cases/${caseId}`} className="text-xs font-bold text-emerald-700 bg-emerald-100 hover:bg-emerald-200 px-3 py-1.5 rounded-lg transition">
              View Case
            </Link>
          )}
        </div>
      )}

      {monthlyRevenueHint > 0 && (
        <div className="bg-sky-50 border border-sky-200 text-sky-900 p-4 rounded-2xl flex items-start gap-3 shadow-sm">
          <TrendingUp className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-sm">
              Monthly revenue hint available: {new Intl.NumberFormat('en-IN', {
                style: 'currency',
                currency: 'INR',
                maximumFractionDigits: 0,
              }).format(monthlyRevenueHint)}
            </div>
            <div className="text-xs text-sky-700 mt-1">
              Derived from the attached {monthlyRevenueHintSource || 'statement'} data. This helps the assessment and later restructuring recommendation stay aligned with recent transaction trends.
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-2xl flex items-start gap-3 shadow-sm animate-scale-in">
          <AlertCircle className="w-6 h-6 shrink-0 mt-0.5" />
          <div className="font-medium">{error}</div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid sm:grid-cols-3 gap-3">
          <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm">
            <p className="text-[11px] uppercase tracking-[0.16em] font-bold text-slate-400">Step 1</p>
            <p className="text-sm font-semibold text-slate-700 mt-1">Upload Store Images</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm">
            <p className="text-[11px] uppercase tracking-[0.16em] font-bold text-slate-400">Step 2</p>
            <p className="text-sm font-semibold text-slate-700 mt-1">Capture GPS Coordinates</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm">
            <p className="text-[11px] uppercase tracking-[0.16em] font-bold text-slate-400">Step 3</p>
            <p className="text-sm font-semibold text-slate-700 mt-1">Add Store & Owner Context</p>
          </div>
        </div>

        <ImageUploader images={images} onImagesChange={setImages} />

        <GeoInput gpsData={gpsData} onGpsChange={setGpsData} />

        <div className="space-y-4">
          <StatementUploadCard
            onSubmit={handleStatementUpload}
            title="Optional: Paytm / Bank Statement"
            description="Attach a recent Paytm, PhonePe, or bank statement to refine revenue assessment during AI analysis."
            submitLabel="Attach statement"
            useSampleLabel="Use sample"
            className="rounded-2xl"
          />
        </div>

        <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-linear-to-r from-indigo-500 via-sky-400 to-cyan-400" />
          <h2 className="text-xl font-bold flex items-center gap-2 mb-5 text-slate-800">
            <Store className="text-indigo-600" /> Borrower & Store Details
          </h2>
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-semibold text-slate-700 mb-1">Store Name {caseId ? '' : '*'}</label>
              <input
                type="text"
                value={storeName}
                required={!caseId}
                onChange={(e) => setStoreName(e.target.value)}
                placeholder="e.g., Gupta General Store"
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-slate-800 outline-none transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              />
            </div>

            {!caseId && (
              <>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Owner Name</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="text"
                      value={ownerName}
                      onChange={(e) => setOwnerName(e.target.value)}
                      placeholder="e.g., Sanjay Gupta"
                      className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-3 text-slate-800 outline-none transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Mobile Number</label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="tel"
                      value={ownerMobile}
                      onChange={(e) => setOwnerMobile(e.target.value)}
                      placeholder="+91-9876543210"
                      className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-3 text-slate-800 outline-none transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Shop Area (sq ft) (Optional)</label>
              <div className="flex gap-2 mb-2">
                {SHOP_SIZE_PRESETS.map((preset) => {
                  const isActive = shopSize === preset.value;
                  return (
                    <button
                      key={preset.value}
                      type="button"
                      onClick={() => setShopSize(preset.value)}
                      className={`flex-1 rounded-lg py-1.5 text-xs font-semibold transition ${isActive ? 'border border-indigo-300 bg-indigo-50 text-indigo-700' : 'border border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
                    >
                      {preset.label} ({preset.value})
                    </button>
                  );
                })}
              </div>
              <input
                type="number"
                min="0"
                value={shopSize}
                onChange={(e) => setShopSize(e.target.value)}
                placeholder="e.g., 7500"
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-slate-800 outline-none transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">Years in Operation (Optional)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={yearsInOperation}
                onChange={(e) => setYearsInOperation(e.target.value)}
                placeholder="e.g., 5.5"
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-slate-800 outline-none transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-semibold text-slate-700 mb-1">Monthly Rent (INR) (Optional)</label>
              <input
                type="number"
                min="0"
                value={rent}
                onChange={(e) => setRent(e.target.value)}
                placeholder="e.g., 15000"
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-slate-800 outline-none transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              />
            </div>
          </div>

          <p className="text-xs text-slate-500 mt-2">
            {!caseId && "A new case and borrower profile will be automatically created upon submission. "}
            Providing optional details helps the AI Fusion Engine provide a more accurate risk assessment and loan size.
          </p>
        </div>

        <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
          <div className="text-xs text-slate-500">
            Required to submit: 3-5 images and valid GPS coordinates.
          </div>
          <button
            type="submit"
            disabled={!canSubmit}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-8 py-4 text-lg font-bold text-white shadow-md transition-all hover:-translate-y-0.5 hover:bg-indigo-700 disabled:translate-y-0 disabled:cursor-not-allowed disabled:bg-slate-300"
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
  );

  return (
    <div className="text-slate-900 font-sans pb-20 animate-fade-in">
      {content}
    </div>
  );
}
