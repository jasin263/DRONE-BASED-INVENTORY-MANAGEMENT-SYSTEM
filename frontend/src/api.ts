import type { paths } from "./generated/api";
import { getActiveAuthToken } from "./auth";

export type HealthApiResponse = paths["/health/ready"]["get"]["responses"][200]["content"]["application/json"];
export type HealthResponse = HealthApiResponse;

export type ApiProblem = {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
};

export class ApiError extends Error {
  readonly problem: ApiProblem;

  constructor(problem: ApiProblem, status: number) {
    super(problem.detail || problem.title || `Request failed with status ${status}`);
    this.name = "ApiError";
    this.problem = { ...problem, status };
  }
}

const apiUrl = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

export function getHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getActiveAuthToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = { ...getHeaders(), ...(options.headers || {}) };
  const url = endpoint.startsWith("http") ? endpoint : `${apiUrl}${endpoint}`;
  const response = await fetch(url, { ...options, headers });
  
  if (!response.ok) {
    let problem: ApiProblem;
    try {
      problem = (await response.json()) as ApiProblem;
    } catch {
      problem = { title: response.statusText, status: response.status };
    }
    throw new ApiError(problem, response.status);
  }
  
  if (response.status === 204) {
    return {} as T;
  }
  return (await response.json()) as T;
}

// ==========================================
// Health & Identity
// ==========================================

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiUrl.replace(/\/api$/, "")}/health/ready`);
  const body = (await response.json()) as HealthApiResponse;
  if (!response.ok) {
    throw new ApiError(body as unknown as ApiProblem, response.status);
  }
  return body;
}

export async function getMe() {
  return request<{ subject: string; username: string; roles: string[]; site_ids: string[] }>("/v1/me");
}

export async function getSites() {
  return request<Array<{ id: number; code: string; name: string; description?: string }>>("/v1/sites");
}

// ==========================================
// Dashboard KPIs
// ==========================================

export interface DashboardKPIs {
  ira_pct: number;
  coverage_pct: number;
  open_cases: number;
  total_cases: number;
  total_variance_value: number;
  total_bins_evaluated: number;
  outcomes: Record<string, number>;
  zones: Array<{ zone: string; label: string; accuracy: number; openCases: number; bins: number }>;
  recent_missions: Array<{
    id: number;
    mission_id: string;
    site_code: string;
    drone_serial: string;
    status: string;
    coverage_pct: number;
    total_scans: number;
    total_bins_visited: number;
    started_at: string | null;
  }>;
  system_status: string;
}

export async function getDashboardKPIs(siteId?: string): Promise<DashboardKPIs> {
  const q = siteId ? `?site_id=${encodeURIComponent(siteId)}` : "";
  return request<DashboardKPIs>(`/v1/dashboard/kpis${q}`);
}

// ==========================================
// Missions
// ==========================================

export interface MissionItem {
  id: number;
  mission_id: string;
  site_id: number;
  site_code?: string;
  drone_id: number;
  drone_serial?: string;
  status: "RECEIVING" | "PROCESSING" | "RECONCILED" | "FAILED";
  coverage_pct: number;
  total_scans: number;
  total_bins_visited: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  outcomes?: Record<string, number>;
}

export async function getMissions(): Promise<MissionItem[]> {
  return request<MissionItem[]>("/v1/missions");
}

export async function getMissionDetail(missionId: string): Promise<MissionItem> {
  return request<MissionItem>(`/v1/missions/${encodeURIComponent(missionId)}`);
}

export async function reprocessMission(missionId: string): Promise<{ mission_id: string; status: string; queued: boolean }> {
  return request<{ mission_id: string; status: string; queued: boolean }>(
    `/v1/missions/${encodeURIComponent(missionId)}/reprocess`,
    { method: "POST" }
  );
}

export async function getMissionBins(missionId: string, page = 1, pageSize = 50) {
  return request<{
    total: number;
    page: number;
    page_size: number;
    bins: Array<{
      id: number;
      location_id: string;
      label_code: string;
      zone: string;
      aisle: string;
      rack: string;
      level: string;
      count: number;
      confidence: number;
      method: string;
      coverage: number;
    }>;
  }>(`/v1/missions/${encodeURIComponent(missionId)}/bins?page=${page}&page_size=${pageSize}`);
}

export async function getMissionReconResults(missionId: string, outcome?: string, page = 1, pageSize = 50) {
  const qOutcome = outcome ? `&outcome=${encodeURIComponent(outcome)}` : "";
  return request<{
    total: number;
    page: number;
    page_size: number;
    results: Array<{
      id: number;
      location_code: string;
      label_code: string;
      sku_description: string;
      sku_gtin: string;
      unit_value: number;
      lot: string;
      outcome: string;
      variance: number;
      confidence: number;
      counted_qty: number;
      book_qty: number;
    }>;
  }>(`/v1/missions/${encodeURIComponent(missionId)}/recon-results?page=${page}&page_size=${pageSize}${qOutcome}`);
}

// ==========================================
// Discrepancies & Adjustments
// ==========================================

export interface DiscrepancyItem {
  id: number;
  mission_id: number;
  location_id: number;
  location_code: string;
  label_code: string;
  zone: string;
  aisle: string;
  rack: string;
  level: string;
  sku_id: number;
  sku_description: string;
  sku_gtin: string;
  unit_value: number;
  lot: string;
  outcome: string;
  status: string;
  variance_value: number;
  threshold_value: number;
  assigned_to: number | null;
  created_at: string | null;
}

export async function getDiscrepancies(params?: {
  status?: string;
  outcome?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<DiscrepancyItem[]> {
  const p = new URLSearchParams();
  if (params?.status) p.append("status", params.status);
  if (params?.outcome) p.append("outcome", params.outcome);
  if (params?.search) p.append("search", params.search);
  if (params?.page) p.append("page", String(params.page));
  if (params?.page_size) p.append("page_size", String(params.page_size));
  const queryStr = p.toString() ? `?${p.toString()}` : "";
  return request<DiscrepancyItem[]>(`/v1/discrepancies${queryStr}`);
}

export async function getDiscrepancyDetail(caseId: number) {
  return request<DiscrepancyItem & { comments: Array<{ id: number; comment: string; user_id: number; created_at: string }> }>(
    `/v1/discrepancies/${caseId}`
  );
}

export async function approveDiscrepancy(caseId: number) {
  return request<{ id: number; status: string; adjustment_id?: number }>(`/v1/discrepancies/${caseId}/approve`, {
    method: "POST",
  });
}

export async function rejectDiscrepancy(caseId: number) {
  return request<{ id: number; status: string }>(`/v1/discrepancies/${caseId}/reject`, {
    method: "POST",
  });
}

export async function addDiscrepancyComment(caseId: number, comment: string) {
  return request<{ id: number; comment: string }>(`/v1/discrepancies/${caseId}/comments`, {
    method: "POST",
    body: JSON.stringify({ comment }),
  });
}

export interface AdjustmentItem {
  id: number;
  case_id: number;
  sku_description: string;
  sku_gtin: string;
  location_code: string;
  label_code: string;
  adjustment_type: string;
  quantity: number;
  reason: string;
  status: string;
  posted_to_erp: boolean;
  created_at: string | null;
}

export async function getAdjustments(): Promise<AdjustmentItem[]> {
  return request<AdjustmentItem[]>("/v1/adjustments");
}

export async function postAdjustmentToERP(adjId: number) {
  return request<{ id: number; status: string; posted_to_erp: boolean; erp_reference?: string }>(
    `/v1/adjustments/${adjId}/post`,
    { method: "POST" }
  );
}

// ==========================================
// Warehouse Map & Bin History
// ==========================================

export interface BinMapItem {
  id: number;
  bin_code: string;
  label_code: string;
  site_id: number;
  zone: string;
  aisle: string;
  rack: string;
  level: string;
  count: number;
  confidence: number;
  method: string;
  outcome: string;
  variance: number;
}

export async function getInventoryMap(params?: { site_id?: string; zone?: string; aisle?: string }) {
  const p = new URLSearchParams();
  if (params?.site_id) p.append("site_id", params.site_id);
  if (params?.zone) p.append("zone", params.zone);
  if (params?.aisle) p.append("aisle", params.aisle);
  const q = p.toString() ? `?${p.toString()}` : "";
  return request<{ bins: BinMapItem[]; total_bins: number; source: string }>(`/v1/inventory-map${q}`);
}

export async function getBinHistory(locationId: number) {
  return request<{
    location_id: number;
    bin_code: string;
    label_code: string;
    zone: string;
    aisle: string;
    rack: string;
    level: string;
    history: Array<{ mission_id: string; count: number; confidence: number; method: string; date: string }>;
  }>(`/v1/bins/${locationId}/history`);
}

// ==========================================
// Master Data & Drones
// ==========================================

export async function getMasterLocations(zone?: string, aisle?: string, page = 1, pageSize = 50) {
  const p = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (zone) p.append("zone", zone);
  if (aisle) p.append("aisle", aisle);
  return request<{
    total: number;
    page: number;
    page_size: number;
    locations: Array<{
      id: number;
      bin_code: string;
      label_code: string;
      zone: string;
      aisle: string;
      rack: string;
      level: string;
    }>;
  }>(`/v1/master-data/locations?${p.toString()}`);
}

export async function getMasterSkus(search?: string, page = 1, pageSize = 50) {
  const p = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (search) p.append("search", search);
  return request<{
    total: number;
    page: number;
    page_size: number;
    skus: Array<{
      id: number;
      gtin: string;
      epc_prefix: string;
      description: string;
      uom: string;
      unit_value: number;
    }>;
  }>(`/v1/master-data/skus?${p.toString()}`);
}

export async function getDrones() {
  return request<Array<{
    id: number;
    serial_number: string;
    model: string;
    firmware_version: string;
    status: string;
    battery_pct: number;
  }>>("/v1/drones");
}

// ==========================================
// Reports
// ==========================================

export async function getReportData(reportType = "cycle_count") {
  return request<{ report: string; generated_at: string; data?: any[] }>(`/v1/reports?report_type=${reportType}`);
}

export async function createReportJob(payload: { type: string; format?: string }) {
  return request<{ job_id: string; type: string; status: string; download_url: string }>("/v1/reports", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ==========================================
// Admin & Settings
// ==========================================

export async function getSettings() {
  return request<Array<{ key: string; value: any; description: string }>>("/v1/settings");
}

export async function updateSetting(key: string, value: any, description?: string) {
  return request<{ key: string; value: any }>("/v1/settings", {
    method: "PUT",
    body: JSON.stringify({ key, value, description }),
  });
}

export async function getUsers() {
  return request<Array<{ id: number; username: string; email: string; role: string; is_active: boolean }>>("/v1/users");
}

export async function createUser(data: { username: string; email?: string; role: string; site_id?: number }) {
  return request<{ id: number; username: string; role: string }>("/v1/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateUser(userId: number, patch: { role?: string; is_active?: boolean }) {
  return request<{ id: number; role: string; is_active: boolean }>(`/v1/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function deleteUser(userId: number) {
  return request<void>(`/v1/users/${userId}`, { method: "DELETE" });
}

export async function getAuditLog() {
  return request<Array<{
    id: number;
    action: string;
    table_name: string;
    record_id: number;
    old_values: any;
    new_values: any;
    created_at: string;
  }>>("/v1/audit-log");
}

export async function getNotifications() {
  return request<Array<{
    id: string;
    type: string;
    title: string;
    message: string;
    time: string;
    unread: boolean;
  }>>("/v1/notifications");
}
