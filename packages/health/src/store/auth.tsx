import { createSignal, createContext, useContext } from "solid-js"
import type { JSX } from "solid-js"

interface User {
  id: string
  name: string
  email: string
}

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  error: string | null
}

type Props = { children: JSX.Element }

const AuthContext = createContext<{
  state: () => AuthState
  login: (email: string, password: string) => Promise<boolean>
  register: (name: string, email: string, password: string) => Promise<boolean>
  logout: () => Promise<void>
  api: <T = unknown>(path: string, options?: RequestInit) => Promise<T>
}>(null as any)

const API_BASE = "/api"

export function AuthProvider(props: Props) {
  const [state, setState] = createSignal<AuthState>({
    user: null,
    token: null,
    loading: true,
    error: null,
  })

  async function loadFromStorage() {
    const token = localStorage.getItem("health_token")
    if (!token) {
      setState((s) => ({ ...s, loading: false }))
      return
    }
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = (await res.json()) as { user: User }
        setState({ user: data.user, token, loading: false, error: null })
      } else {
        localStorage.removeItem("health_token")
        setState({ user: null, token: null, loading: false, error: null })
      }
    } catch {
      localStorage.removeItem("health_token")
      setState((s) => ({ ...s, loading: false }))
    }
  }

  loadFromStorage()

  async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
    const token = state().token || localStorage.getItem("health_token")
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    }
    if (token) headers["Authorization"] = `Bearer ${token}`
    if (options.headers) {
      const h = options.headers as Record<string, string>
      Object.assign(headers, h)
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      credentials: "include",
    })

    if (res.status === 401) {
      localStorage.removeItem("health_token")
      setState({ user: null, token: null, loading: false, error: "Session expired" })
      throw new Error("Unauthorized")
    }

    if (!res.ok) {
      const body = (await res.json().catch(() => ({ error: "Request failed" }))) as { error: string }
      throw new Error(body.error || `HTTP ${res.status}`)
    }

    return res.json() as Promise<T>
  }

  async function login(email: string, password: string): Promise<boolean> {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await api<{ token: string; user: User }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      })
      localStorage.setItem("health_token", data.token)
      setState({ user: data.user, token: data.token, loading: false, error: null })
      return true
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Login failed"
      setState((s) => ({ ...s, loading: false, error: msg }))
      return false
    }
  }

  async function register(name: string, email: string, password: string): Promise<boolean> {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await api<{ token: string; user: User }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      })
      localStorage.setItem("health_token", data.token)
      setState({ user: data.user, token: data.token, loading: false, error: null })
      return true
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Registration failed"
      setState((s) => ({ ...s, loading: false, error: msg }))
      return false
    }
  }

  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" })
    } catch {}
    localStorage.removeItem("health_token")
    setState({ user: null, token: null, loading: false, error: null })
  }

  return <AuthContext.Provider value={{ state, login, register, logout, api }}>{props.children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
