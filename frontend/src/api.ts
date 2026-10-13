import type { paths } from "./generated/api";

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

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiUrl.replace(/\/api$/, "")}/health/ready`);
  const body = (await response.json()) as HealthApiResponse;
  if (!response.ok) {
    throw new ApiError(body as unknown as ApiProblem, response.status);
  }
  return body;
}
