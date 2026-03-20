import { createSignal, createResource, For, Show } from "solid-js"
import { useAuth } from "../store/auth"

export default function Dashboard() {
  const auth = useAuth()

  const [metrics, { refetch: refetchMetrics }] = createResource(() => auth.api("/metrics"))
  const [water, { refetch: refetchWater }] = createResource(() =>
    auth.api<{ logs: any[]; totalMl: number; goal: number }>("/water"),
  )
  const [activities, { refetch: refetchActivities }] = createResource(() => auth.api("/activities"))
  const [appointments, { refetch: refetchAppointments }] = createResource(() => auth.api("/appointments"))

  const [showWaterModal, setShowWaterModal] = createSignal(false)
  const [showActivityModal, setShowActivityModal] = createSignal(false)
  const [showMetricModal, setShowMetricModal] = createSignal(false)
  const [showAptModal, setShowAptModal] = createSignal(false)
  const [toast, setToast] = createSignal("")

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(""), 3000)
  }

  const logWater = async (ml: number) => {
    try {
      await auth.api("/water", { method: "POST", body: JSON.stringify({ amount_ml: ml }) })
      setShowWaterModal(false)
      refetchWater()
      refetchMetrics()
      showToast(`${ml}mL of water logged`)
    } catch (e: any) {
      showToast(e.message)
    }
  }

  const [actTitle, setActTitle] = createSignal("")
  const [actDuration, setActDuration] = createSignal("")
  const [actCalories, setActCalories] = createSignal("")
  const [actType, setActType] = createSignal("exercise")
  const logActivity = async () => {
    if (!actTitle() || !actDuration()) return
    try {
      await auth.api("/activities", {
        method: "POST",
        body: JSON.stringify({
          title: actTitle(),
          duration_minutes: parseInt(actDuration()),
          calories_burned: parseInt(actCalories()) || 0,
          type: actType(),
        }),
      })
      setShowActivityModal(false)
      setActTitle("")
      setActDuration("")
      setActCalories("")
      refetchActivities()
      refetchMetrics()
      showToast("Activity logged")
    } catch (e: any) {
      showToast(e.message)
    }
  }

  const [metricHR, setMetricHR] = createSignal("")
  const [metricSteps, setMetricSteps] = createSignal("")
  const [metricCal, setMetricCal] = createSignal("")
  const [metricSleep, setMetricSleep] = createSignal("")
  const logMetrics = async () => {
    try {
      await auth.api("/metrics", {
        method: "POST",
        body: JSON.stringify({
          heart_rate: parseInt(metricHR()) || undefined,
          steps: parseInt(metricSteps()) || undefined,
          calories: parseInt(metricCal()) || undefined,
          sleep_hours: parseFloat(metricSleep()) || undefined,
        }),
      })
      setShowMetricModal(false)
      refetchMetrics()
      showToast("Metrics updated")
    } catch (e: any) {
      showToast(e.message)
    }
  }

  const [aptTitle, setAptTitle] = createSignal("")
  const [aptType, setAptType] = createSignal("Checkup")
  const [aptDate, setAptDate] = createSignal("")
  const [aptTime, setAptTime] = createSignal("")
  const [aptLocation, setAptLocation] = createSignal("")
  const logAppointment = async () => {
    if (!aptTitle() || !aptDate() || !aptTime()) return
    try {
      await auth.api("/appointments", {
        method: "POST",
        body: JSON.stringify({
          title: aptTitle(),
          appointment_type: aptType(),
          appointment_date: new Date(aptDate()).getTime(),
          appointment_time: aptTime(),
          location: aptLocation(),
        }),
      })
      setShowAptModal(false)
      setAptTitle("")
      setAptDate("")
      setAptTime("")
      setAptLocation("")
      refetchAppointments()
      showToast("Appointment scheduled")
    } catch (e: any) {
      showToast(e.message)
    }
  }

  const waterPct = () => {
    const w = water()
    if (!w) return 0
    return Math.min(100, Math.round((w.totalMl / w.goal) * 100))
  }

  const iconMap: any = {
    heart: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
      </svg>
    ),
    flame: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
        <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
      </svg>
    ),
    droplet: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
        <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
      </svg>
    ),
    moon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
    ),
    activity: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
    walk: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
        <circle cx="12" cy="4" r="2" />
        <path d="M15 22v-4l-3-5-1 2-2-4-2 4-3 5v4" />
      </svg>
    ),
  }

  const metricIcons: any = {
    "Heart Rate": "heart",
    Calories: "flame",
    Hydration: "droplet",
    Sleep: "moon",
    Steps: "activity",
  }

  return (
    <div>
      <Show when={toast()}>
        <div class="apple-toast">{toast()}</div>
      </Show>

      <div class="mb-10">
        <h1 class="apple-page-title">Good morning, {auth.state().user?.name?.split(" ")[0] || "there"}.</h1>
        <p class="apple-page-subtitle">Here's your health overview for today.</p>
      </div>

      <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-8">
        <Show
          when={metrics()}
          fallback={
            <For each={[1, 2, 3, 4, 5]}>
              {() => (
                <div class="metric-card animate-pulse">
                  <div class="h-7 w-7 rounded-md mb-3" style="background: var(--color-divider)" />
                  <div class="h-9 w-16 rounded mb-1" style="background: var(--color-divider)" />
                  <div class="h-3 w-12 rounded" style="background: var(--color-divider)" />
                </div>
              )}
            </For>
          }
        >
          <For each={metrics()}>
            {(metric: any) => (
              <div class="metric-card">
                <div class="flex items-center justify-between mb-3">
                  <span class="metric-label">{metric.label}</span>
                  <span style={`color: ${metric.color}`}>{iconMap[metricIcons[metric.label]] || iconMap.activity}</span>
                </div>
                <div class="metric-value" style={`color: ${metric.color}`}>
                  {metric.value}
                  <span class="text-base font-normal" style="color: var(--color-text-secondary)">
                    {" "}
                    {metric.unit}
                  </span>
                </div>
                <div class={`metric-trend ${metric.trend}`}>
                  <Show when={metric.trend === "up"}>
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <polyline points="18 15 12 9 6 15" />
                    </svg>
                  </Show>
                  <Show when={metric.trend === "down"}>
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </Show>
                  {metric.trendValue}
                </div>
              </div>
            )}
          </For>
        </Show>
      </div>

      <div class="flex gap-3 mb-8">
        <button class="btn btn-secondary" onClick={() => setShowMetricModal(true)}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
          Log Metrics
        </button>
        <button class="btn btn-primary" onClick={() => setShowWaterModal(true)}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
          </svg>
          Log Water
        </button>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
        <div class="lg:col-span-2 apple-card">
          <div class="flex items-center justify-between mb-8">
            <h2 class="text-xl font-semibold tracking-tight">Activity</h2>
            <button class="btn btn-secondary text-sm py-2" onClick={() => setShowActivityModal(true)}>
              + Log
            </button>
          </div>
          <div class="flex items-end gap-2 h-44 mb-6">
            <For each={["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}>
              {(day, i) => {
                const heights = [65, 80, 45, 90, 70, 55, 75]
                return (
                  <div class="flex-1 flex flex-col items-center gap-2">
                    <div
                      class="w-full rounded-sm"
                      style={`height: ${heights[i()]}%; background: var(--color-accent); opacity: 0.85`}
                    />
                    <span class="text-xs" style="color: var(--color-text-tertiary)">
                      {day}
                    </span>
                  </div>
                )
              }}
            </For>
          </div>
          <div class="grid grid-cols-4 gap-4 pt-5" style="border-top: 1px solid var(--color-divider)">
            <div>
              <p class="text-2xl font-semibold tracking-tight" style="color: var(--color-text)">
                {metrics()?.[1]?.value || "—"}
              </p>
              <p class="text-xs mt-0.5" style="color: var(--color-text-tertiary)">
                Calories
              </p>
            </div>
            <div>
              <p class="text-2xl font-semibold tracking-tight" style="color: var(--color-text)">
                {activities()?.length || 0}
              </p>
              <p class="text-xs mt-0.5" style="color: var(--color-text-tertiary)">
                Activities
              </p>
            </div>
            <div>
              <p class="text-2xl font-semibold tracking-tight" style="color: var(--color-text)">
                {activities()?.reduce((s: number, a: any) => s + (a.duration_minutes || 0), 0) || 0}
              </p>
              <p class="text-xs mt-0.5" style="color: var(--color-text-tertiary)">
                Active min
              </p>
            </div>
            <div>
              <p class="text-2xl font-semibold tracking-tight" style="color: var(--color-text)">
                {metrics()?.[4]?.value || "—"}
              </p>
              <p class="text-xs mt-0.5" style="color: var(--color-text-tertiary)">
                Steps
              </p>
            </div>
          </div>
        </div>

        <div class="apple-card">
          <h2 class="text-xl font-semibold tracking-tight mb-5">Today's Activity</h2>
          <Show
            when={activities()?.length}
            fallback={
              <div class="text-center py-10">
                <p class="text-sm mb-4" style="color: var(--color-text-tertiary)">
                  No activities logged today
                </p>
                <button class="btn btn-secondary text-sm" onClick={() => setShowActivityModal(true)}>
                  Log Activity
                </button>
              </div>
            }
          >
            <div class="flex flex-col gap-2">
              <For each={activities()?.slice(0, 5)}>
                {(activity: any) => (
                  <div class="flex items-center gap-3 p-3 rounded-lg" style="background: var(--color-bg-subtle)">
                    <div
                      class="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                      style={`background: ${activity.color || "#0071e3"}15; color: ${activity.color || "#0071e3"}`}
                    >
                      {iconMap[activity.type === "yoga" ? "moon" : activity.type === "walk" ? "walk" : "activity"]}
                    </div>
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-medium truncate" style="color: var(--color-text)">
                        {activity.title}
                      </p>
                      <p class="text-xs" style="color: var(--color-text-tertiary)">
                        {activity.time} · {activity.duration}
                      </p>
                    </div>
                    <Show when={activity.calories_burned}>
                      <span class="tag tag-neutral text-xs">{activity.calories_burned} cal</span>
                    </Show>
                  </div>
                )}
              </For>
            </div>
          </Show>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div class="apple-card">
          <div class="flex items-center justify-between mb-5">
            <h2 class="text-xl font-semibold tracking-tight">Hydration</h2>
            <button class="btn btn-ghost text-sm py-1.5 px-3" onClick={() => setShowWaterModal(true)}>
              + Add
            </button>
          </div>
          <div class="flex items-center gap-6">
            <div class="relative w-28 h-28 shrink-0">
              <svg width="112" height="112" viewBox="0 0 112 112">
                <circle cx="56" cy="56" r="48" fill="none" stroke="var(--color-divider)" stroke-width="8" />
                <circle
                  cx="56"
                  cy="56"
                  r="48"
                  fill="none"
                  stroke="var(--color-accent)"
                  stroke-width="8"
                  stroke-linecap="round"
                  stroke-dasharray={`${2 * Math.PI * 48}`}
                  stroke-dashoffset={`${2 * Math.PI * 48 * (1 - waterPct() / 100)}`}
                  transform="rotate(-90 56 56)"
                  style="transition: stroke-dashoffset 800ms cubic-bezier(0.25, 0.1, 0.25, 1)"
                />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-2xl font-semibold tracking-tight" style="color: var(--color-text)">
                  {water()?.totalMl || 0}
                </span>
                <span class="text-xs" style="color: var(--color-text-tertiary)">
                  of {water()?.goal || 2500}mL
                </span>
              </div>
            </div>
            <div class="flex-1 flex flex-col gap-3">
              <div>
                <div class="flex justify-between text-sm mb-1.5">
                  <span style="color: var(--color-text-secondary)">Daily goal</span>
                  <span class="font-medium" style="color: var(--color-text)">
                    {waterPct()}%
                  </span>
                </div>
                <div class="progress-bar">
                  <div class="progress-fill" style={`width: ${waterPct()}%`} />
                </div>
              </div>
              <p class="text-sm" style="color: var(--color-text-tertiary)">
                {water()?.logs?.length || 0} {water()?.logs?.length === 1 ? "entry" : "entries"} today
              </p>
              <div class="flex gap-2">
                <For each={[200, 300, 500]}>
                  {(ml) => (
                    <button class="btn btn-secondary text-sm flex-1 justify-center py-2" onClick={() => logWater(ml)}>
                      +{ml}mL
                    </button>
                  )}
                </For>
              </div>
            </div>
          </div>
        </div>

        <div class="apple-card">
          <div class="flex items-center justify-between mb-5">
            <h2 class="text-xl font-semibold tracking-tight">Appointments</h2>
            <button class="btn btn-ghost text-sm py-1.5 px-3" onClick={() => setShowAptModal(true)}>
              + Schedule
            </button>
          </div>
          <Show
            when={appointments()?.length}
            fallback={
              <div class="text-center py-10">
                <p class="text-sm mb-4" style="color: var(--color-text-tertiary)">
                  No upcoming appointments
                </p>
                <button class="btn btn-primary text-sm" onClick={() => setShowAptModal(true)}>
                  Schedule
                </button>
              </div>
            }
          >
            <div class="flex flex-col gap-2">
              <For each={appointments()?.slice(0, 3)}>
                {(apt: any) => (
                  <div class="flex items-center gap-3 p-3 rounded-lg" style="background: var(--color-bg-subtle)">
                    <div
                      class="w-11 h-11 rounded-lg flex flex-col items-center justify-center shrink-0"
                      style="background: rgba(0, 113, 227, 0.08)"
                    >
                      <span class="text-sm font-semibold leading-none" style="color: var(--color-accent)">
                        {apt.day}
                      </span>
                      <span class="text-xs leading-none mt-0.5" style="color: var(--color-text-tertiary)">
                        {apt.month}
                      </span>
                    </div>
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-medium truncate" style="color: var(--color-text)">
                        {apt.title}
                      </p>
                      <p class="text-xs" style="color: var(--color-text-tertiary)">
                        {apt.time}
                        {apt.location ? ` · ${apt.location}` : ""}
                      </p>
                    </div>
                    <span class="tag tag-neutral text-xs">{apt.type}</span>
                  </div>
                )}
              </For>
            </div>
          </Show>
        </div>
      </div>

      <Show when={showWaterModal()}>
        <AppleModal title="Log Water" onClose={() => setShowWaterModal(false)}>
          <div class="flex flex-col gap-5">
            <div class="grid grid-cols-3 gap-2">
              <For each={[200, 300, 500, 350, 400, 600]}>
                {(ml) => (
                  <button
                    class="btn btn-secondary justify-center py-3 text-sm"
                    onClick={() => setShowWaterModal(false) || logWater(ml)}
                  >
                    {ml}mL
                  </button>
                )}
              </For>
            </div>
            <div class="apple-divider" />
            <div>
              <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                Custom amount
              </label>
              <div class="flex gap-2">
                <input
                  type="number"
                  class="apple-input"
                  placeholder="250"
                  value={waterAmount()}
                  onInput={(e) => setWaterAmount(parseInt(e.currentTarget.value) || 0)}
                />
                <button class="btn btn-primary px-5 shrink-0" onClick={() => logWater(waterAmount())}>
                  Log
                </button>
              </div>
            </div>
          </div>
        </AppleModal>
      </Show>

      <Show when={showActivityModal()}>
        <AppleModal title="Log Activity" onClose={() => setShowActivityModal(false)}>
          <div class="flex flex-col gap-4">
            <div>
              <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                Activity name
              </label>
              <input
                class="apple-input"
                placeholder="Morning Yoga"
                value={actTitle()}
                onInput={(e) => setActTitle(e.currentTarget.value)}
              />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                  Duration (min)
                </label>
                <input
                  type="number"
                  class="apple-input"
                  placeholder="30"
                  value={actDuration()}
                  onInput={(e) => setActDuration(e.currentTarget.value)}
                />
              </div>
              <div>
                <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                  Calories
                </label>
                <input
                  type="number"
                  class="apple-input"
                  placeholder="150"
                  value={actCalories()}
                  onInput={(e) => setActCalories(e.currentTarget.value)}
                />
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                Type
              </label>
              <select class="apple-select" value={actType()} onChange={(e) => setActType(e.currentTarget.value)}>
                <option value="exercise">Exercise</option>
                <option value="yoga">Yoga</option>
                <option value="walk">Walk</option>
                <option value="swimming">Swimming</option>
                <option value="cycling">Cycling</option>
                <option value="strength">Strength Training</option>
                <option value="other">Other</option>
              </select>
            </div>
            <button class="btn btn-primary w-full justify-center py-3" onClick={logActivity}>
              Log Activity
            </button>
          </div>
        </AppleModal>
      </Show>

      <Show when={showMetricModal()}>
        <AppleModal title="Log Metrics" onClose={() => setShowMetricModal(false)}>
          <div class="flex flex-col gap-4">
            <div>
              <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                Heart rate (bpm)
              </label>
              <input
                type="number"
                class="apple-input"
                placeholder="72"
                value={metricHR()}
                onInput={(e) => setMetricHR(e.currentTarget.value)}
              />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                  Steps
                </label>
                <input
                  type="number"
                  class="apple-input"
                  placeholder="5000"
                  value={metricSteps()}
                  onInput={(e) => setMetricSteps(e.currentTarget.value)}
                />
              </div>
              <div>
                <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                  Calories
                </label>
                <input
                  type="number"
                  class="apple-input"
                  placeholder="1800"
                  value={metricCal()}
                  onInput={(e) => setMetricCal(e.currentTarget.value)}
                />
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                Sleep (hours)
              </label>
              <input
                type="number"
                step="0.5"
                class="apple-input"
                placeholder="7.5"
                value={metricSleep()}
                onInput={(e) => setMetricSleep(e.currentTarget.value)}
              />
            </div>
            <button class="btn btn-primary w-full justify-center py-3" onClick={logMetrics}>
              Save
            </button>
          </div>
        </AppleModal>
      </Show>

      <Show when={showAptModal()}>
        <AppleModal title="Schedule Appointment" onClose={() => setShowAptModal(false)}>
          <div class="flex flex-col gap-4">
            <div>
              <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                Title
              </label>
              <input
                class="apple-input"
                placeholder="Annual Physical Exam"
                value={aptTitle()}
                onInput={(e) => setAptTitle(e.currentTarget.value)}
              />
            </div>
            <div>
              <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                Type
              </label>
              <select class="apple-select" value={aptType()} onChange={(e) => setAptType(e.currentTarget.value)}>
                <option>Checkup</option>
                <option>Dental</option>
                <option>Specialist</option>
                <option>Lab Work</option>
                <option>Vaccination</option>
                <option>Other</option>
              </select>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                  Date
                </label>
                <input
                  type="date"
                  class="apple-input"
                  value={aptDate()}
                  onInput={(e) => setAptDate(e.currentTarget.value)}
                />
              </div>
              <div>
                <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                  Time
                </label>
                <input
                  type="time"
                  class="apple-input"
                  value={aptTime()}
                  onInput={(e) => setAptTime(e.currentTarget.value)}
                />
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                Location
              </label>
              <input
                class="apple-input"
                placeholder="Downtown Medical Center"
                value={aptLocation()}
                onInput={(e) => setAptLocation(e.currentTarget.value)}
              />
            </div>
            <button class="btn btn-primary w-full justify-center py-3" onClick={logAppointment}>
              Schedule
            </button>
          </div>
        </AppleModal>
      </Show>
    </div>
  )
}

function AppleModal(props: { title: string; onClose: () => void; children: any }) {
  return (
    <div class="apple-modal-backdrop" onClick={(e) => e.target === e.currentTarget && props.onClose()}>
      <div class="apple-modal">
        <div class="flex items-center justify-between mb-5">
          <h2 class="text-lg font-semibold tracking-tight" style="color: var(--color-text)">
            {props.title}
          </h2>
          <button class="btn btn-ghost p-2" onClick={props.onClose}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        {props.children}
      </div>
    </div>
  )
}
