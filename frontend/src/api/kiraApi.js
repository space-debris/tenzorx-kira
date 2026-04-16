import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
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
