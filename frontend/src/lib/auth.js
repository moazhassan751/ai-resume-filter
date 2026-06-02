const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export function getToken() {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('tl_token')
}

export async function loginRequest(email, password) {
  const fd = new FormData()
  fd.append('username', email)
  fd.append('password', password)
  const res = await fetch(`${API}/api/v1/auth/token`, { method: 'POST', body: fd })
  if (!res.ok) {
    const txt = await res.text()
    throw new Error(txt || 'Login failed')
  }
  const data = await res.json()
  if (typeof window !== 'undefined') localStorage.setItem('tl_token', data.access_token)
  return data.access_token
}

export async function registerRequest(email, password, fullName) {
  const res = await fetch(`${API}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  })
  if (!res.ok) {
    const txt = await res.text()
    throw new Error(txt || 'Registration failed')
  }
  return res.json()
}

export function logout() {
  if (typeof window !== 'undefined') localStorage.removeItem('tl_token')
}

export function isAuthenticated() {
  return !!getToken()
}

export async function apiFetch(path, options = {}) {
  const token = getToken()
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  const headers = { ...options.headers }
  if (!isFormData && !headers['Content-Type']) headers['Content-Type'] = 'application/json'
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${API}${path}`, { ...options, headers })
  if (res.status === 401) { logout(); throw new Error('Unauthorised') }
  return res
}