import axios from 'axios';

const ENV_API_BASE_URL = String(import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
const API_BASE_URL = ENV_API_BASE_URL || '/api/v1';
const ABSOLUTE_URL_PATTERN = /^https?:\/\//i;
const LOCAL_HOSTNAMES = new Set(['localhost', '127.0.0.1', '0.0.0.0']);

function getResolvedApiBaseUrl() {
  if (typeof window === 'undefined' || !ABSOLUTE_URL_PATTERN.test(API_BASE_URL)) {
    return API_BASE_URL;
  }

  try {
    const parsed = new URL(API_BASE_URL);
    const currentHostname = window.location.hostname;
    if (LOCAL_HOSTNAMES.has(parsed.hostname) && !LOCAL_HOSTNAMES.has(currentHostname)) {
      parsed.hostname = currentHostname;
      parsed.protocol = window.location.protocol;
      return parsed.toString().replace(/\/+$/, '');
    }
  } catch (error) {
    console.warn('Invalid VITE_API_BASE_URL. Falling back to configured value.', error);
  }

  return API_BASE_URL;
}

const RESOLVED_API_BASE_URL = getResolvedApiBaseUrl();

function normalizePath(path = '') {
  if (!path) return '';
  return path.startsWith('/') ? path : `/${path}`;
}

export function resolveApiUrl(path = '') {
  const normalizedPath = normalizePath(path);

  if (ABSOLUTE_URL_PATTERN.test(RESOLVED_API_BASE_URL)) {
    return `${RESOLVED_API_BASE_URL}${normalizedPath}`;
  }

  const basePath = RESOLVED_API_BASE_URL.startsWith('/') ? RESOLVED_API_BASE_URL : `/${RESOLVED_API_BASE_URL}`;
  if (typeof window !== 'undefined') {
    return new URL(`${basePath}${normalizedPath}`, window.location.origin).toString();
  }

  return `${basePath}${normalizedPath}`;
}

const apiClient = axios.create({
  baseURL: RESOLVED_API_BASE_URL,
  timeout: 300000,
});

export async function submitAssessment(formData) {
  return apiClient.post('/assess', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export async function getAssessmentStatus(sessionId) {
  return apiClient.get(`/assess/${sessionId}`);
}

export async function checkHealth() {
  return apiClient.get('/health');
}

export async function getPlatformDemoSnapshot() {
  return apiClient.get('/platform/demo-snapshot');
}

export async function listOrganizations() {
  return apiClient.get('/platform/orgs');
}

export async function getOrganizationDashboard(orgId) {
  return apiClient.get(`/platform/orgs/${orgId}/dashboard`);
}

export async function getOrganizationPortfolio(orgId) {
  return apiClient.get(`/platform/orgs/${orgId}/portfolio`);
}

export async function listOrganizationCases(orgId) {
  return apiClient.get(`/platform/orgs/${orgId}/cases`);
}

export async function createPlatformCase(payload) {
  return apiClient.post('/platform/cases', payload);
}

export async function getPlatformCase(caseId) {
  return apiClient.get(`/platform/cases/${caseId}`);
}

export async function listOrganizationKiranas(orgId) {
  return apiClient.get(`/platform/orgs/${orgId}/kiranas`);
}

export async function getPlatformKiranaDetail(orgId, kiranaId) {
  return apiClient.get(`/platform/orgs/${orgId}/kiranas/${kiranaId}`);
}

export async function updateCaseStatus(caseId, payload) {
  return apiClient.post(`/platform/cases/${caseId}/status`, payload);
}

export async function linkAssessmentToCase(caseId, sessionId, actorUserId) {
  const formData = new FormData();
  if (actorUserId) formData.append('actor_user_id', actorUserId);
  return apiClient.post(`/platform/cases/${caseId}/assessments/${sessionId}/link`, formData);
}

export async function getCaseAuditTrail(caseId) {
  return apiClient.get(`/platform/cases/${caseId}/audit`);
}

export async function getCasePrefillData(caseId) {
  return apiClient.get(`/platform/cases/${caseId}/prefill`);
}

export async function getLoanAccount(caseId) {
  return apiClient.get(`/platform/cases/${caseId}/loan-account`);
}

export async function uploadStatement(caseId, payload) {
  return apiClient.post(`/platform/cases/${caseId}/statements`, payload);
}

export async function getCaseDocuments(caseId) {
  return apiClient.get(`/platform/cases/${caseId}/documents`);
}

export async function exportCaseDocuments(caseId, actorUserId) {
  const formData = new FormData();
  if (actorUserId) formData.append('actor_user_id', actorUserId);
  return apiClient.post(`/platform/cases/${caseId}/documents/export`, formData);
}

export async function getCaseForecast(caseId) {
  return apiClient.get(`/platform/cases/${caseId}/forecast`);
}

export async function simulateCaseScenario(caseId, scenario) {
  return apiClient.get(`/platform/cases/${caseId}/simulate?scenario=${scenario}`);
}

export async function createAAConsent(caseId, orgId) {
  const formData = new FormData();
  if (orgId) formData.append('org_id', orgId);
  return apiClient.post(`/platform/cases/${caseId}/aa_consent`, formData);
}

export async function overrideUnderwritingDecision(caseId, payload) {
  return apiClient.post(`/platform/cases/${caseId}/override`, payload);
}
