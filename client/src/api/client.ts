import type { Absence, Assignment, Employee, GenerateResult, ScheduleResponse, ShiftType, ValidationResult } from './types'

const BASE = '/api'

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
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

export function fetchSchedule(year: number, month: number): Promise<ScheduleResponse> {
  return fetchJson(`/schedules/${year}/${month}`)
}

export async function createSchedule(year: number, month: number): Promise<void> {
  await fetch(`${BASE}/schedules/${year}/${month}`, { method: 'POST' })
}

export async function saveAssignments(
  year: number,
  month: number,
  assignments: Assignment[],
): Promise<void> {
  const res = await fetch(`${BASE}/schedules/${year}/${month}/assignments`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assignments }),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
}

export async function validateSchedule(year: number, month: number): Promise<ValidationResult> {
  const res = await fetch(`${BASE}/schedules/${year}/${month}/validate`, { method: 'POST' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function generateSchedule(year: number, month: number): Promise<GenerateResult> {
  const res = await fetch(`${BASE}/schedules/${year}/${month}/generate`, { method: 'POST' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export function fetchAbsences(year: number, month: number): Promise<Absence[]> {
  return fetchJson(`/absences?year=${year}&month=${month}`)
}

export async function createAbsence(data: Omit<Absence, 'id' | 'created_at'>): Promise<Absence> {
  const res = await fetch(`${BASE}/absences`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function deleteAbsence(id: number): Promise<void> {
  const res = await fetch(`${BASE}/absences/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
}

export async function createEmployee(data: Omit<Employee, 'id' | 'created_at'>): Promise<Employee> {
  const res = await fetch(`${BASE}/employees`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function updateEmployee(id: number, data: Partial<Omit<Employee, 'id' | 'created_at'>>): Promise<Employee> {
  const res = await fetch(`${BASE}/employees/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function deleteEmployee(id: number): Promise<void> {
  const res = await fetch(`${BASE}/employees/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
}
