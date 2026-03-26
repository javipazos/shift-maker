import type { Absence, Assignment, Employee, GenerateResult, Rule, ScheduleResponse, ShiftType, ValidationResult } from './types'

const BASE = '/api'

type TokenGetter = () => Promise<string | null>
let _getToken: TokenGetter | null = null

export function setTokenGetter(getter: TokenGetter) {
  _getToken = getter
}

async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const auth: Record<string, string> = {}
  if (_getToken) {
    const token = await _getToken()
    if (token) auth.Authorization = `Bearer ${token}`
  }
  return fetch(`${BASE}${url}`, {
    ...options,
    headers: { ...auth, ...options.headers },
  })
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await apiFetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await apiFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function putJson<T>(url: string, body: unknown): Promise<T> {
  const res = await apiFetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function del(url: string): Promise<void> {
  const res = await apiFetch(url, { method: 'DELETE' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
}

export function fetchEmployees(): Promise<Employee[]> {
  return fetchJson('/employees')
}

export function fetchAllEmployees(): Promise<Employee[]> {
  return fetchJson('/employees?status=all')
}

export function fetchShiftTypes(): Promise<ShiftType[]> {
  return fetchJson('/shift-types')
}

export function fetchAllShiftTypes(): Promise<ShiftType[]> {
  return fetchJson('/shift-types?status=all')
}

export function createShiftType(data: Omit<ShiftType, 'id' | 'created_at'>): Promise<ShiftType> {
  return postJson('/shift-types', data)
}

export function updateShiftType(id: number, data: Partial<Omit<ShiftType, 'id' | 'created_at'>>): Promise<ShiftType> {
  return putJson(`/shift-types/${id}`, data)
}

export function deleteShiftType(id: number): Promise<void> {
  return del(`/shift-types/${id}`)
}

export function fetchSchedule(year: number, month: number): Promise<ScheduleResponse> {
  return fetchJson(`/schedules/${year}/${month}`)
}

export async function createSchedule(year: number, month: number): Promise<void> {
  const res = await apiFetch(`/schedules/${year}/${month}`, { method: 'POST' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
}

export function saveAssignments(year: number, month: number, assignments: Assignment[]): Promise<unknown> {
  return putJson(`/schedules/${year}/${month}/assignments`, { assignments })
}

export async function validateSchedule(year: number, month: number): Promise<ValidationResult> {
  const res = await apiFetch(`/schedules/${year}/${month}/validate`, { method: 'POST' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export function generateSchedule(year: number, month: number, fixedAssignments?: Assignment[]): Promise<GenerateResult> {
  return postJson(`/schedules/${year}/${month}/generate`, { fixed_assignments: fixedAssignments ?? [] })
}

export function fetchAbsences(year: number, month: number): Promise<Absence[]> {
  return fetchJson(`/absences?year=${year}&month=${month}`)
}

export function createAbsence(data: Omit<Absence, 'id' | 'created_at'>): Promise<Absence> {
  return postJson('/absences', data)
}

export function deleteAbsence(id: number): Promise<void> {
  return del(`/absences/${id}`)
}

export function createEmployee(data: Omit<Employee, 'id' | 'created_at'>): Promise<Employee> {
  return postJson('/employees', data)
}

export function updateEmployee(id: number, data: Partial<Omit<Employee, 'id' | 'created_at'>>): Promise<Employee> {
  return putJson(`/employees/${id}`, data)
}

export function deleteEmployee(id: number): Promise<void> {
  return del(`/employees/${id}`)
}

export function fetchRules(): Promise<Rule[]> {
  return fetchJson('/rules')
}

export function updateRule(id: string, data: Partial<Pick<Rule, 'priority' | 'weight' | 'params' | 'active'>>): Promise<Rule> {
  return putJson(`/rules/${id}`, data)
}
