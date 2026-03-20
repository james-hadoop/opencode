import { createSignal, For, Show } from "solid-js"
import { useNavigate } from "@solidjs/router"
import { useAuth } from "../store/auth"

const settingsItems = [
  { label: "Account Settings", desc: "Name, email, password" },
  { label: "Health Goals", desc: "Daily targets and preferences" },
  { label: "Notifications", desc: "Reminders and alerts" },
  { label: "Privacy & Security", desc: "Data and access controls" },
  { label: "Connected Devices", desc: "Wearables and apps" },
  { label: "Data Export", desc: "Download your health data" },
]

export default function Profile() {
  const auth = useAuth()
  const navigate = useNavigate()
  const [showLogoutConfirm, setShowLogoutConfirm] = createSignal(false)

  const user = () => auth.state().user

  const handleLogout = async () => {
    await auth.logout()
    navigate("/login")
  }

  return (
    <div class="max-w-2xl mx-auto">
      <h1 class="apple-page-title">Profile</h1>
      <p class="apple-page-subtitle">Manage your account and health preferences</p>

      {/* User Card */}
      <div class="apple-card mt-8">
        <div class="flex items-center gap-5 mb-6 pb-6" style="border-bottom: 1px solid var(--color-border)">
          <div
            class="w-20 h-20 rounded-2xl flex items-center justify-center text-white text-2xl font-bold shrink-0"
            style="background: #1d1d1f"
          >
            {user()
              ?.name?.split(" ")
              .map((n: string) => n[0])
              .join("")
              .slice(0, 2) || "U"}
          </div>
          <div>
            <h2 class="text-xl font-semibold tracking-tight" style="color: var(--color-text)">
              {user()?.name}
            </h2>
            <p class="text-sm mt-0.5" style="color: var(--color-text-secondary)">
              {user()?.email}
            </p>
            <span class="tag tag-accent mt-2">Premium Plan</span>
          </div>
        </div>

        {/* Settings list */}
        <div class="flex flex-col gap-2">
          <For each={settingsItems}>
            {(item) => (
              <button
                class="flex items-center gap-3 p-3 rounded-xl text-left transition-all cursor-pointer"
                style="background: var(--color-bg-subtle)"
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0,0,0,0.04)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "var(--color-bg-subtle)")}
              >
                <div class="flex-1">
                  <p class="text-sm font-medium" style="color: var(--color-text)">
                    {item.label}
                  </p>
                  <p class="text-xs mt-0.5" style="color: var(--color-text-secondary)">
                    {item.desc}
                  </p>
                </div>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  style="color: var(--color-text-secondary)"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            )}
          </For>
        </div>
      </div>

      {/* Danger Zone */}
      <div class="apple-card mt-6" style="border: 1px solid rgba(255,59,48,0.2)">
        <p
          class="apple-section-title"
          style="color: var(--color-error); text-transform: none; font-size: 0.875rem; letter-spacing: 0; margin-bottom: 0.75rem"
        >
          Account Actions
        </p>
        <button
          class="btn btn-secondary w-full justify-center"
          style="color: var(--color-error); border-color: rgba(255,59,48,0.3); background: rgba(255,59,48,0.04)"
          onClick={() => setShowLogoutConfirm(true)}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          Sign Out
        </button>
      </div>

      {/* Logout Confirm Modal */}
      <Show when={showLogoutConfirm()}>
        <div class="apple-modal-backdrop" onClick={() => setShowLogoutConfirm(false)}>
          <div class="apple-modal" onClick={(e) => e.stopPropagation()}>
            <h3 class="text-xl font-semibold tracking-tight mb-2" style="color: var(--color-text)">
              Sign Out?
            </h3>
            <p class="text-sm mb-6" style="color: var(--color-text-secondary)">
              Are you sure you want to sign out of your account?
            </p>
            <div class="flex gap-3">
              <button class="btn btn-secondary flex-1 justify-center" onClick={() => setShowLogoutConfirm(false)}>
                Cancel
              </button>
              <button class="btn btn-danger flex-1 justify-center" onClick={handleLogout}>
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </Show>
    </div>
  )
}
