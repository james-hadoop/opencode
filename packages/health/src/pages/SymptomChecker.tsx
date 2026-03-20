import { createSignal, createResource, For, Show } from "solid-js"
import { useAuth } from "../store/auth"

const symptomTemplates = [
  {
    name: "Headache",
    severity: "mild",
    possibleCauses: ["Dehydration", "Stress", "Lack of sleep", "Eye strain"],
    recommendation: "Drink water, rest in a quiet room. Consider over-the-counter pain relief if needed.",
    urgency: "low",
  },
  {
    name: "Fatigue",
    severity: "moderate",
    possibleCauses: ["Anemia", "Thyroid issues", "Poor sleep quality", "Depression"],
    recommendation: "Consider blood tests for thyroid and iron levels. Ensure 7-9 hours of sleep.",
    urgency: "medium",
  },
  {
    name: "Chest Pain",
    severity: "severe",
    possibleCauses: ["Anxiety", "Acid reflux", "Heart conditions", "Muscle strain"],
    recommendation: "Seek immediate medical attention if accompanied by shortness of breath or arm pain.",
    urgency: "high",
  },
  {
    name: "Joint Pain",
    severity: "mild",
    possibleCauses: ["Arthritis", "Overuse", "Weather changes", "Vitamin D deficiency"],
    recommendation: "Apply warm compress, consider omega-3 supplements. Consult rheumatologist if persistent.",
    urgency: "low",
  },
  {
    name: "Sore Throat",
    severity: "mild",
    possibleCauses: ["Viral infection", "Bacterial infection", "Allergies", "Dry air"],
    recommendation: "Gargle with warm salt water, stay hydrated. See doctor if fever persists over 48 hours.",
    urgency: "low",
  },
  {
    name: "Nausea",
    severity: "moderate",
    possibleCauses: ["Food poisoning", "Pregnancy", "Migraine", "Motion sickness"],
    recommendation: "Stay hydrated with small sips. Avoid solid food until nausea subsides.",
    urgency: "medium",
  },
  {
    name: "Dizziness",
    severity: "moderate",
    possibleCauses: ["Low blood sugar", "Dehydration", "Inner ear issues", "Low blood pressure"],
    recommendation: "Sit or lie down immediately. Drink water and eat something. Seek care if accompanied by fainting.",
    urgency: "medium",
  },
  {
    name: "Fever",
    severity: "moderate",
    possibleCauses: ["Viral infection", "Bacterial infection", "Inflammation", "Heat exhaustion"],
    recommendation: "Rest and stay hydrated. Take fever reducers if above 38.5C. Seek care if exceeds 39.5C.",
    urgency: "medium",
  },
  {
    name: "Cough",
    severity: "mild",
    possibleCauses: ["Cold/flu", "Allergies", "Asthma", "GERD"],
    recommendation: "Stay hydrated, use honey for soothing. See doctor if cough lasts over 3 weeks.",
    urgency: "low",
  },
  {
    name: "Back Pain",
    severity: "moderate",
    possibleCauses: ["Muscle strain", "Poor posture", "Herniated disc", "Kidney issues"],
    recommendation: "Apply ice/heat, gentle stretching. See doctor if pain radiates down legs.",
    urgency: "medium",
  },
]

export default function SymptomChecker() {
  const auth = useAuth()
  const [selectedSymptoms, setSelectedSymptoms] = createSignal<string[]>([])
  const [searchQuery, setSearchQuery] = createSignal("")
  const [showResults, setShowResults] = createSignal(false)
  const [showModal, setShowModal] = createSignal(false)
  const [activeSymptom, setActiveSymptom] = createSignal<any>(null)
  const [showLogForm, setShowLogForm] = createSignal(false)
  const [logSeverity, setLogSeverity] = createSignal("mild")
  const [logDuration, setLogDuration] = createSignal("")
  const [logNotes, setLogNotes] = createSignal("")
  const [toast, setToast] = createSignal("")

  const [savedSymptoms, { refetch: refetchSymptoms }] = createResource(() => auth.api("/symptoms"))

  const filteredSymptoms = () =>
    symptomTemplates.filter((s) => s.name.toLowerCase().includes(searchQuery().toLowerCase()))

  const toggleSymptom = (name: string) => {
    setSelectedSymptoms((prev) => (prev.includes(name) ? prev.filter((s) => s !== name) : [...prev, name]))
  }

  const analyzeSymptoms = () => {
    if (selectedSymptoms().length === 0) return
    setShowResults(true)
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "mild":
        return "var(--color-success)"
      case "moderate":
        return "var(--color-warning)"
      case "severe":
        return "var(--color-error)"
      default:
        return "var(--color-text-tertiary)"
    }
  }

  const logSymptom = async (name: string) => {
    const tmpl = symptomTemplates.find((s) => s.name === name)
    if (!tmpl) return
    try {
      await auth.api("/symptoms", {
        method: "POST",
        body: JSON.stringify({
          symptom_name: name,
          severity: logSeverity(),
          duration: logDuration(),
          notes: logNotes(),
        }),
      })
      setShowLogForm(false)
      setLogSeverity("mild")
      setLogDuration("")
      setLogNotes("")
      refetchSymptoms()
      showToast(`"${name}" logged`)
    } catch (e: any) {
      showToast(e.message)
    }
  }

  const deleteSymptom = async (id: string) => {
    try {
      await auth.api(`/symptoms/${id}`, { method: "DELETE" })
      refetchSymptoms()
      showToast("Symptom removed")
    } catch (e: any) {
      showToast(e.message)
    }
  }

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(""), 3000)
  }

  return (
    <div>
      <Show when={toast()}>
        <div class="apple-toast">{toast()}</div>
      </Show>

      <div class="mb-10">
        <h1 class="apple-page-title">Symptom Checker</h1>
        <p class="apple-page-subtitle">Select symptoms to analyze and optionally log them to your health record.</p>
      </div>

      <Show when={savedSymptoms()?.length}>
        <div class="apple-card mb-6" style="border: 1px solid var(--color-divider)">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-base font-semibold" style="color: var(--color-text)">
              Your Logged Symptoms Today
            </h2>
            <span class="tag tag-success">{savedSymptoms()?.length} logged</span>
          </div>
          <div class="flex flex-wrap gap-2">
            <For each={savedSymptoms()}>
              {(symptom: any) => (
                <div
                  class="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm"
                  style="background: var(--color-bg-subtle)"
                >
                  <span style={`color: ${getSeverityColor(symptom.severity)}`} class="font-medium">
                    {symptom.symptom_name}
                  </span>
                  <button class="cursor-pointer opacity-50 hover:opacity-100" onClick={() => deleteSymptom(symptom.id)}>
                    <svg
                      width="11"
                      height="11"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="var(--color-error)"
                      stroke-width="2.5"
                    >
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              )}
            </For>
          </div>
        </div>
      </Show>

      <div class="apple-card mb-5">
        <div class="relative mb-4">
          <input
            type="text"
            placeholder="Search symptoms..."
            class="apple-input pl-10"
            value={searchQuery()}
            onInput={(e) => setSearchQuery(e.currentTarget.value)}
          />
          <svg
            class="absolute left-3.5 top-1/2 -translate-y-1/2"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-text-tertiary)"
            stroke-width="2"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </div>

        <div class="flex flex-wrap gap-2">
          <For each={filteredSymptoms()}>
            {(symptom) => (
              <button
                class="px-4 py-2 text-sm font-medium rounded-full transition-all cursor-pointer"
                style={
                  selectedSymptoms().includes(symptom.name)
                    ? "background: var(--color-text); color: white"
                    : "background: var(--color-bg-subtle); color: var(--color-text); border: 1px solid var(--color-divider)"
                }
                onClick={() => toggleSymptom(symptom.name)}
              >
                {symptom.name}
              </button>
            )}
          </For>
        </div>

        <div class="flex items-center justify-between mt-4 pt-4" style="border-top: 1px solid var(--color-divider)">
          <p class="text-sm" style="color: var(--color-text-secondary)">
            {selectedSymptoms().length > 0 ? `${selectedSymptoms().length} selected` : "Select symptoms"}
          </p>
          <div class="flex gap-2">
            <button
              class="btn btn-secondary text-sm"
              onClick={analyzeSymptoms}
              disabled={selectedSymptoms().length === 0}
            >
              Analyze
            </button>
            <button
              class="btn btn-primary text-sm"
              onClick={() => setShowLogForm(true)}
              disabled={selectedSymptoms().length === 0}
            >
              Log to Record
            </button>
          </div>
        </div>
      </div>

      <div
        class="flex items-start gap-3 p-4 rounded-xl mb-6"
        style="background: rgba(255, 149, 0, 0.07); border: 1px solid rgba(255, 149, 0, 0.2)"
      >
        <svg
          width="17"
          height="17"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--color-warning)"
          stroke-width="2"
          class="shrink-0 mt-0.5"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <p class="text-sm leading-relaxed" style="color: #92400e">
          <strong>Disclaimer:</strong> This tool provides general health info, not medical advice. Always consult a
          healthcare professional.
        </p>
      </div>

      <Show when={showResults()}>
        <h2 class="text-xl font-semibold tracking-tight mb-4" style="color: var(--color-text)">
          Analysis Results
        </h2>
        <div class="flex flex-col gap-4">
          <For each={symptomTemplates.filter((s) => selectedSymptoms().includes(s.name))}>
            {(symptom) => (
              <div
                class="apple-card cursor-pointer"
                onClick={() => {
                  setActiveSymptom(symptom)
                  setShowModal(true)
                }}
              >
                <div class="flex items-start justify-between">
                  <div class="flex items-center gap-3">
                    <div
                      class="w-10 h-10 rounded-lg flex items-center justify-center"
                      style={`background: ${getSeverityColor(symptom.severity)}15`}
                    >
                      <svg
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke={getSeverityColor(symptom.severity)}
                        stroke-width="1.75"
                      >
                        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                      </svg>
                    </div>
                    <div>
                      <h3 class="font-semibold" style="color: var(--color-text)">
                        {symptom.name}
                      </h3>
                      <p class="text-sm" style="color: var(--color-text-secondary)">
                        Severity:{" "}
                        <span style={`color: ${getSeverityColor(symptom.severity)}; font-weight: 600`}>
                          {symptom.severity}
                        </span>
                      </p>
                    </div>
                  </div>
                  <span
                    class="tag text-xs"
                    style={
                      symptom.urgency === "high"
                        ? "background: rgba(255,59,48,0.1); color: var(--color-error)"
                        : symptom.urgency === "medium"
                          ? "background: rgba(255,149,0,0.1); color: var(--color-warning)"
                          : "background: rgba(52,199,89,0.1); color: var(--color-success)"
                    }
                  >
                    {symptom.urgency === "high"
                      ? "Seek Care"
                      : symptom.urgency === "medium"
                        ? "Medium Priority"
                        : "Low Priority"}
                  </span>
                </div>
                <p class="text-sm mt-3 leading-relaxed" style="color: var(--color-text-secondary)">
                  {symptom.recommendation}
                </p>
                <div class="flex flex-wrap gap-1.5 mt-3">
                  <For each={symptom.possibleCauses}>{(cause) => <span class="tag tag-neutral">{cause}</span>}</For>
                </div>
              </div>
            )}
          </For>
        </div>
      </Show>

      <Show when={showLogForm()}>
        <div class="apple-modal-backdrop" onClick={(e) => e.target === e.currentTarget && setShowLogForm(false)}>
          <div class="apple-modal">
            <div class="flex items-center justify-between mb-5">
              <h2 class="text-lg font-semibold tracking-tight" style="color: var(--color-text)">
                Log Symptom
              </h2>
              <button class="btn btn-ghost p-2" onClick={() => setShowLogForm(false)}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <p class="text-sm mb-5" style="color: var(--color-text-secondary)">
              Selected: <strong>{selectedSymptoms().join(", ")}</strong>
            </p>
            <div class="flex flex-col gap-4">
              <div>
                <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                  Severity
                </label>
                <select
                  class="apple-select"
                  value={logSeverity()}
                  onChange={(e) => setLogSeverity(e.currentTarget.value)}
                >
                  <option value="mild">Mild</option>
                  <option value="moderate">Moderate</option>
                  <option value="severe">Severe</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                  Duration
                </label>
                <input
                  class="apple-input"
                  placeholder="e.g., 2 days"
                  value={logDuration()}
                  onInput={(e) => setLogDuration(e.currentTarget.value)}
                />
              </div>
              <div>
                <label class="block text-sm font-medium mb-2" style="color: var(--color-text)">
                  Notes (optional)
                </label>
                <textarea
                  class="apple-input"
                  rows="3"
                  placeholder="Any additional details..."
                  value={logNotes()}
                  onInput={(e) => setLogNotes(e.currentTarget.value)}
                />
              </div>
              <button
                class="btn btn-primary w-full justify-center py-3"
                onClick={() => {
                  selectedSymptoms().forEach((s) => logSymptom(s))
                  setShowLogForm(false)
                  setSelectedSymptoms([])
                }}
              >
                Log All Selected
              </button>
            </div>
          </div>
        </div>
      </Show>

      <Show when={showModal() && activeSymptom()}>
        <div class="apple-modal-backdrop" onClick={(e) => e.target === e.currentTarget && setShowModal(false)}>
          <div class="apple-modal">
            <div class="flex items-center justify-between mb-5">
              <h2 class="text-lg font-semibold tracking-tight" style="color: var(--color-text)">
                {activeSymptom()?.name}
              </h2>
              <button class="btn btn-ghost p-2" onClick={() => setShowModal(false)}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div class="grid grid-cols-2 gap-3 mb-5">
              <div class="p-3 rounded-lg" style="background: var(--color-bg-subtle)">
                <p class="text-xs mb-1" style="color: var(--color-text-tertiary)">
                  Severity
                </p>
                <p class="font-semibold" style={`color: ${getSeverityColor(activeSymptom()?.severity)}`}>
                  {activeSymptom()?.severity}
                </p>
              </div>
              <div class="p-3 rounded-lg" style="background: var(--color-bg-subtle)">
                <p class="text-xs mb-1" style="color: var(--color-text-tertiary)">
                  Urgency
                </p>
                <p
                  class="font-semibold capitalize"
                  style={`color: ${activeSymptom()?.urgency === "high" ? "var(--color-error)" : activeSymptom()?.urgency === "medium" ? "var(--color-warning)" : "var(--color-success)"}`}
                >
                  {activeSymptom()?.urgency}
                </p>
              </div>
            </div>
            <div class="mb-4">
              <h3 class="text-sm font-semibold mb-2" style="color: var(--color-text)">
                Possible Causes
              </h3>
              <div class="flex flex-wrap gap-1.5">
                <For each={activeSymptom()?.possibleCauses}>
                  {(cause: string) => <span class="tag tag-neutral">{cause}</span>}
                </For>
              </div>
            </div>
            <div>
              <h3 class="text-sm font-semibold mb-2" style="color: var(--color-text)">
                Recommendation
              </h3>
              <p class="text-sm leading-relaxed" style="color: var(--color-text-secondary)">
                {activeSymptom()?.recommendation}
              </p>
            </div>
            <div class="flex gap-3 mt-5">
              <button class="btn btn-secondary flex-1 justify-center">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.15 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.07 1.2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 8.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21 16.92z" />
                </svg>
                Call Doctor
              </button>
              <button
                class="btn btn-primary flex-1 justify-center"
                onClick={() => {
                  setShowModal(false)
                  setShowLogForm(true)
                }}
              >
                Log Symptom
              </button>
            </div>
          </div>
        </div>
      </Show>
    </div>
  )
}
