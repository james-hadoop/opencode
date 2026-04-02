import { createSignal, Show } from "solid-js"
import { useNavigate } from "@solidjs/router"
import { useAuth } from "../store/auth"

export default function Login() {
  const auth = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = createSignal<"login" | "register">("login")
  const [name, setName] = createSignal("")
  const [email, setEmail] = createSignal("")
  const [password, setPassword] = createSignal("")
  const [error, setError] = createSignal("")
  const [loading, setLoading] = createSignal(false)

  const handleSubmit = async (e: Event) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      let success = false
      if (mode() === "login") {
        success = await auth.login(email(), password())
      } else {
        if (!name()) {
          setError("Name is required")
          setLoading(false)
          return
        }
        success = await auth.register(name(), email(), password())
      }

      if (success) {
        navigate("/")
      } else {
        setError(auth.state().error || "Authentication failed")
      }
    } catch (err: any) {
      setError(err.message || "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div class="min-h-screen flex" style="background: #ffffff">
      <div class="hidden lg:flex lg:w-1/2 flex-col justify-between p-16" style="background: #f5f5f7">
        <div>
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-lg flex items-center justify-center" style="background: #000000">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
            <span class="text-lg font-semibold tracking-tight" style="color: var(--color-text)">
              HealthHub
            </span>
          </div>
        </div>

        <div>
          <h2
            class="text-5xl font-bold leading-tight tracking-tight mb-6"
            style="color: var(--color-text); font-size: clamp(2.5rem, 4vw, 3.5rem)"
          >
            Your health.
            <br />
            In perfect balance.
          </h2>
          <p class="text-lg leading-relaxed" style="color: var(--color-text-secondary); max-width: 400px">
            Track your wellness journey with precision. Log metrics, plan meals, and understand your body — all in one
            beautifully designed space.
          </p>
          <div class="flex gap-8 mt-12">
            <div>
              <p class="text-3xl font-semibold tracking-tight" style="color: var(--color-text)">
                8+
              </p>
              <p class="text-sm mt-1" style="color: var(--color-text-tertiary)">
                Health metrics tracked
              </p>
            </div>
            <div>
              <p class="text-3xl font-semibold tracking-tight" style="color: var(--color-text)">
                100%
              </p>
              <p class="text-sm mt-1" style="color: var(--color-text-tertiary)">
                Private & secure
              </p>
            </div>
            <div>
              <p class="text-3xl font-semibold tracking-tight" style="color: var(--color-text)">
                7
              </p>
              <p class="text-sm mt-1" style="color: var(--color-text-tertiary)">
                Day meal planning
              </p>
            </div>
          </div>
        </div>

        <p class="text-sm" style="color: var(--color-text-tertiary)">
          By continuing, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>

      <div class="flex-1 flex items-center justify-center p-8">
        <div class="w-full max-w-sm">
          <div class="lg:hidden mb-10">
            <div class="flex items-center gap-2.5 mb-2">
              <div class="w-9 h-9 rounded-lg flex items-center justify-center" style="background: #000000">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
              <span class="text-xl font-semibold tracking-tight" style="color: var(--color-text)">
                HealthHub
              </span>
            </div>
          </div>

          <h1 class="text-2xl font-semibold tracking-tight mb-1" style="color: var(--color-text)">
            {mode() === "login" ? "Sign in" : "Create account"}
          </h1>
          <p class="text-sm mb-8" style="color: var(--color-text-secondary)">
            {mode() === "login" ? "Welcome back. Sign in to continue." : "Start your wellness journey today."}
          </p>

          <Show when={error()}>
            <div
              class="flex items-center gap-2.5 p-3.5 rounded-xl mb-5"
              style="background: rgba(255, 59, 48, 0.06); border: 1px solid rgba(255, 59, 48, 0.2)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff3b30" stroke-width="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span class="text-sm font-medium" style="color: #ff3b30">
                {error()}
              </span>
            </div>
          </Show>

          <form onSubmit={handleSubmit} class="flex flex-col gap-4">
            <Show when={mode() === "register"}>
              <div>
                <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                  Full name
                </label>
                <input
                  type="text"
                  class="apple-input"
                  placeholder="Jane Doe"
                  value={name()}
                  onInput={(e) => setName(e.currentTarget.value)}
                  required
                />
              </div>
            </Show>

            <div>
              <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                Email
              </label>
              <input
                type="email"
                class="apple-input"
                placeholder="jane@example.com"
                value={email()}
                onInput={(e) => setEmail(e.currentTarget.value)}
                required
              />
            </div>

            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="block text-sm font-medium" style="color: var(--color-text)">
                  Password
                </label>
                <Show when={mode() === "login"}>
                  <button type="button" class="text-sm" style="color: var(--color-accent)">
                    Forgot?
                  </button>
                </Show>
              </div>
              <input
                type="password"
                class="apple-input"
                placeholder={mode() === "register" ? "At least 6 characters" : "••••••••"}
                value={password()}
                onInput={(e) => setPassword(e.currentTarget.value)}
                required
                minLength={6}
              />
            </div>

            <button type="submit" class="btn btn-primary w-full justify-center py-3 mt-2" disabled={loading()}>
              <Show when={loading()} fallback={<span>{mode() === "login" ? "Sign in" : "Create account"}</span>}>
                <span class="flex items-center gap-2">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    class="animate-spin"
                  >
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                  {mode() === "login" ? "Signing in..." : "Creating account..."}
                </span>
              </Show>
            </button>
          </form>

          <div class="apple-divider mt-8" />

          <p class="text-center text-sm" style="color: var(--color-text-secondary)">
            {mode() === "login" ? "Don't have an account?" : "Already have an account?"}{" "}
            <button
              class="font-semibold"
              style="color: var(--color-accent)"
              onClick={() => {
                setMode(mode() === "login" ? "register" : "login")
                setError("")
              }}
            >
              {mode() === "login" ? "Sign up" : "Sign in"}
            </button>
          </p>

          <p class="text-center text-xs mt-6 lg:hidden" style="color: var(--color-text-tertiary)">
            By continuing, you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </div>
    </div>
  )
}
