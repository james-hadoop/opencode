import { Router, Route } from "@solidjs/router"
import { Suspense, Show } from "solid-js"
import { AuthProvider, useAuth } from "./store/auth"
import Sidebar from "./components/Sidebar"
import Dashboard from "./pages/Dashboard"
import SymptomChecker from "./pages/SymptomChecker"
import MealPlanner from "./pages/MealPlanner"
import Articles from "./pages/Articles"
import Login from "./pages/Login"
import Profile from "./pages/Profile"

function Layout(props: { children?: any }) {
  const auth = useAuth()

  return (
    <Show
      when={!auth.state().loading}
      fallback={
        <div class="min-h-screen flex items-center justify-center" style="background: var(--color-bg-subtle)">
          <div class="text-center">
            <div
              class="w-10 h-10 rounded-full mx-auto mb-4 flex items-center justify-center animate-spin"
              style="border: 2px solid var(--color-border-strong); border-top-color: var(--color-text); border-right-color: transparent"
            />
            <p style="color: var(--color-text-secondary); font-size: 0.9375rem">Loading HealthHub...</p>
          </div>
        </div>
      }
    >
      <Show when={auth.state().user} fallback={<Login />}>
        <div class="flex min-h-screen" style="background: var(--color-bg-subtle)">
          <Sidebar />
          <main class="flex-1 p-8 overflow-y-auto">
            <div class="max-w-5xl mx-auto">
              <Suspense
                fallback={
                  <div class="flex items-center justify-center h-64">
                    <div
                      class="w-6 h-6 rounded-full animate-spin"
                      style="border: 2px solid var(--color-border-strong); border-top-color: var(--color-text)"
                    />
                  </div>
                }
              >
                {props.children}
              </Suspense>
            </div>
          </main>
        </div>
      </Show>
    </Show>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Router root={Layout}>
        <Route path="/" component={Dashboard} />
        <Route path="/symptoms" component={SymptomChecker} />
        <Route path="/meals" component={MealPlanner} />
        <Route path="/articles" component={Articles} />
        <Route path="/profile" component={Profile} />
        <Route path="/login" component={Login} />
      </Router>
    </AuthProvider>
  )
}
