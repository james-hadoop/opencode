import { createSignal, createResource, For, Show } from "solid-js"
import { useAuth } from "../store/auth"

const mealTemplates = [
  { name: "Greek Yogurt Parfait", calories: 320, protein: 18, carbs: 42, fat: 8, type: "breakfast" },
  { name: "Avocado Toast with Eggs", calories: 450, protein: 22, carbs: 35, fat: 24, type: "breakfast" },
  { name: "Overnight Oats", calories: 380, protein: 14, carbs: 58, fat: 10, type: "breakfast" },
  { name: "Smoothie Bowl", calories: 340, protein: 12, carbs: 55, fat: 9, type: "breakfast" },
  { name: "Grilled Salmon Bowl", calories: 520, protein: 42, carbs: 45, fat: 18, type: "lunch" },
  { name: "Mediterranean Salad", calories: 380, protein: 16, carbs: 30, fat: 22, type: "lunch" },
  { name: "Chicken Stir-Fry", calories: 480, protein: 38, carbs: 42, fat: 14, type: "lunch" },
  { name: "Quinoa Buddha Bowl", calories: 420, protein: 18, carbs: 55, fat: 16, type: "lunch" },
  { name: "Baked Cod with Veggies", calories: 420, protein: 36, carbs: 28, fat: 16, type: "dinner" },
  { name: "Turkey Meatballs", calories: 380, protein: 34, carbs: 22, fat: 18, type: "dinner" },
  { name: "Vegetable Curry", calories: 350, protein: 12, carbs: 48, fat: 14, type: "dinner" },
  { name: "Grilled Chicken Breast", calories: 310, protein: 45, carbs: 5, fat: 10, type: "dinner" },
  { name: "Mixed Nuts & Berries", calories: 180, protein: 5, carbs: 16, fat: 12, type: "snack" },
  { name: "Protein Smoothie", calories: 240, protein: 22, carbs: 28, fat: 6, type: "snack" },
  { name: "Apple with Almond Butter", calories: 220, protein: 6, carbs: 26, fat: 12, type: "snack" },
  { name: "Rice Cakes with Avocado", calories: 190, protein: 4, carbs: 22, fat: 10, type: "snack" },
]

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
const mealTypes = ["breakfast", "lunch", "dinner", "snack"] as const

const mealTypeMeta: Record<string, { color: string; bg: string }> = {
  breakfast: { color: "#1d1d1f", bg: "rgba(0,0,0,0.04)" },
  lunch: { color: "#1d1d1f", bg: "rgba(0,0,0,0.04)" },
  dinner: { color: "#1d1d1f", bg: "rgba(0,0,0,0.04)" },
  snack: { color: "#1d1d1f", bg: "rgba(0,0,0,0.04)" },
}

export default function MealPlanner() {
  const auth = useAuth()
  const [activeDay, setActiveDay] = createSignal("Monday")
  const [showMealPicker, setShowMealPicker] = createSignal(false)
  const [pickerMealType, setPickerMealType] = createSignal<string>("breakfast")
  const [searchQuery, setSearchQuery] = createSignal("")
  const [toast, setToast] = createSignal("")
  const [showCustomMeal, setShowCustomMeal] = createSignal(false)
  const [customName, setCustomName] = createSignal("")
  const [customCal, setCustomCal] = createSignal("")
  const [customPro, setCustomPro] = createSignal("")
  const [customCarbs, setCustomCarbs] = createSignal("")
  const [customFat, setCustomFat] = createSignal("")

  const getDayDate = (day: string) => {
    const today = new Date()
    const dayIdx = days.indexOf(day)
    const diff = dayIdx - today.getDay() + 1
    const d = new Date(today)
    d.setDate(today.getDate() + diff)
    return d.toISOString().split("T")[0]
  }

  const [meals, { refetch: refetchMeals }] = createResource(
    () => activeDay(),
    async (day) => {
      const date = new Date(getDayDate(day))
      date.setHours(0, 0, 0, 0)
      const res = await auth.api(`/meals?day=${date.toISOString()}`)
      return res as any[]
    },
  )

  const totalCalories = () => (meals() || []).reduce((sum: number, m: any) => sum + (m.calories || 0), 0)
  const totalProtein = () => (meals() || []).reduce((sum: number, m: any) => sum + (m.protein || 0), 0)
  const totalCarbs = () => (meals() || []).reduce((sum: number, m: any) => sum + (m.carbs || 0), 0)
  const totalFat = () => (meals() || []).reduce((sum: number, m: any) => sum + (m.fat || 0), 0)

  const openMealPicker = (type: string) => {
    setPickerMealType(type)
    setShowMealPicker(true)
  }

  const addMeal = async (meal: any) => {
    try {
      const date = new Date(getDayDate(activeDay() as string))
      date.setHours(0, 0, 0, 0)
      await auth.api("/meals", {
        method: "POST",
        body: JSON.stringify({ ...meal, meal_type: pickerMealType(), logged_at: date.getTime() }),
      })
      setShowMealPicker(false)
      refetchMeals()
      showToast(`"${meal.name}" added`)
    } catch (e: any) {
      showToast(e.message)
    }
  }

  const addCustomMeal = async () => {
    if (!customName() || !customCal()) return
    try {
      const date = new Date(getDayDate(activeDay()))
      date.setHours(0, 0, 0, 0)
      await auth.api("/meals", {
        method: "POST",
        body: JSON.stringify({
          name: customName(),
          calories: parseInt(customCal()),
          protein_g: parseInt(customPro()) || 0,
          carbs_g: parseInt(customCarbs()) || 0,
          fat_g: parseInt(customFat()) || 0,
          meal_type: pickerMealType(),
          logged_at: date.getTime(),
        }),
      })
      setShowCustomMeal(false)
      setShowMealPicker(false)
      setCustomName("")
      setCustomCal("")
      setCustomPro("")
      setCustomCarbs("")
      setCustomFat("")
      refetchMeals()
      showToast("Custom meal added")
    } catch (e: any) {
      showToast(e.message)
    }
  }

  const removeMeal = async (id: string) => {
    try {
      await auth.api(`/meals/${id}`, { method: "DELETE" })
      refetchMeals()
      showToast("Meal removed")
    } catch (e: any) {
      showToast(e.message)
    }
  }

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(""), 3000)
  }

  const filteredMeals = () =>
    mealTemplates.filter(
      (m) => m.type === pickerMealType() && m.name.toLowerCase().includes(searchQuery().toLowerCase()),
    )
  const mealsOfType = (type: string) => (meals() || []).filter((m: any) => m.type === type)

  const getMealTypeLabel = (type: string) => type.charAt(0).toUpperCase() + type.slice(1)

  return (
    <div class="max-w-5xl mx-auto">
      <Show when={toast()}>
        <div class="apple-toast">{toast()}</div>
      </Show>

      <h1 class="apple-page-title">Meal Planner</h1>
      <p class="apple-page-subtitle">Plan your daily meals for balanced nutrition</p>

      {/* Day selector */}
      <div class="apple-card mt-6">
        <div class="flex items-center gap-1.5 overflow-x-auto pb-1">
          <For each={days}>
            {(day) => (
              <button
                class="px-4 py-2 text-sm font-medium whitespace-nowrap shrink-0 transition-all cursor-pointer"
                style={`border-radius: 980px; ${
                  activeDay() === day
                    ? "background: var(--color-text); color: #ffffff"
                    : "background: var(--color-bg-subtle); color: var(--color-text-secondary)"
                }`}
                onClick={() => setActiveDay(day)}
              >
                {day.slice(0, 3)}
              </button>
            )}
          </For>
        </div>
      </div>

      {/* Nutrition summary */}
      <div class="grid grid-cols-4 gap-4 mt-6">
        {[
          { label: "Calories", value: totalCalories(), unit: "kcal" },
          { label: "Protein", value: `${totalProtein()}g`, unit: "" },
          { label: "Carbs", value: `${totalCarbs()}g`, unit: "" },
          { label: "Fat", value: `${totalFat()}g`, unit: "" },
        ].map((m, i) => (
          <div class="metric-card text-center">
            <div class="metric-value tracking-tight">{m.value}</div>
            <div class="metric-label">{m.label}</div>
          </div>
        ))}
      </div>

      {/* Meal sections */}
      <div class="flex flex-col gap-4 mt-6">
        <For each={mealTypes}>
          {(type) => (
            <div class="apple-card">
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2.5">
                  <h3 class="text-base font-semibold tracking-tight" style="color: var(--color-text)">
                    {getMealTypeLabel(type)}
                  </h3>
                  <span class="tag tag-neutral" style="font-size: 0.6875rem">
                    {mealsOfType(type).length}
                  </span>
                </div>
                <button
                  class="btn btn-ghost text-sm py-1.5"
                  style="padding: 0.375rem 0.75rem"
                  onClick={() => openMealPicker(type)}
                >
                  + Add
                </button>
              </div>
              <Show
                when={mealsOfType(type).length > 0}
                fallback={
                  <div class="text-center py-3">
                    <p class="text-sm" style="color: var(--color-text-secondary)">
                      No {type} planned. Click "Add" to get started.
                    </p>
                  </div>
                }
              >
                <div class="flex flex-col gap-2">
                  <For each={mealsOfType(type)}>
                    {(meal: any) => (
                      <div class="flex items-center gap-3 p-3 rounded-xl" style="background: var(--color-bg-subtle)">
                        <div class="flex-1 min-w-0">
                          <p class="text-sm font-medium truncate tracking-tight" style="color: var(--color-text)">
                            {meal.name}
                          </p>
                          <p class="text-xs mt-0.5" style="color: var(--color-text-secondary)">
                            {meal.time}
                          </p>
                        </div>
                        <div
                          class="hidden sm:flex items-center gap-4 text-xs"
                          style="color: var(--color-text-secondary)"
                        >
                          <span>{meal.calories} cal</span>
                          <span>P: {meal.protein}g</span>
                          <span>C: {meal.carbs}g</span>
                          <span>F: {meal.fat}g</span>
                        </div>
                        <button
                          class="p-1.5 rounded-lg transition-colors cursor-pointer"
                          style="background: transparent"
                          onClick={() => removeMeal(meal.id)}
                          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,59,48,0.08)")}
                          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ff3b30" stroke-width="2">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </For>
                </div>
              </Show>
            </div>
          )}
        </For>
      </div>

      {/* Meal Picker Modal */}
      <Show when={showMealPicker()}>
        <div class="apple-modal-backdrop" onClick={() => setShowMealPicker(false)}>
          <div class="apple-modal" onClick={(e) => e.stopPropagation()} style="max-width: 520px">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-xl font-semibold tracking-tight" style="color: var(--color-text)">
                Add {getMealTypeLabel(pickerMealType())}
              </h2>
              <button class="btn btn-ghost p-1.5" style="padding: 0.375rem" onClick={() => setShowMealPicker(false)}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div class="relative mb-4">
              <input
                type="text"
                placeholder={`Search ${pickerMealType()} options`}
                class="apple-input pl-10"
                value={searchQuery()}
                onInput={(e) => setSearchQuery(e.currentTarget.value)}
              />
              <svg
                class="absolute left-3 top-1/2 -translate-y-1/2"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                style="color: var(--color-text-tertiary)"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </div>
            <div class="flex flex-col gap-2 mb-4 max-h-80 overflow-y-auto">
              <For each={filteredMeals()}>
                {(meal) => (
                  <button
                    class="flex items-center gap-3 p-3 rounded-xl text-left transition-all cursor-pointer"
                    style="background: var(--color-bg-subtle)"
                    onClick={() => addMeal(meal)}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0,0,0,0.04)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "var(--color-bg-subtle)")}
                  >
                    <div class="flex-1 min-w-0">
                      <p class="font-medium text-sm tracking-tight" style="color: var(--color-text)">
                        {meal.name}
                      </p>
                      <p class="text-xs mt-0.5" style="color: var(--color-text-secondary)">
                        {meal.calories} cal · P: {meal.protein}g · C: {meal.carbs}g · F: {meal.fat}g
                      </p>
                    </div>
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="var(--color-accent)"
                      stroke-width="2"
                    >
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                  </button>
                )}
              </For>
            </div>
            <button class="btn btn-secondary w-full justify-center" onClick={() => setShowCustomMeal(true)}>
              + Add Custom Meal
            </button>
          </div>
        </div>
      </Show>

      {/* Custom Meal Form */}
      <Show when={showCustomMeal()}>
        <div class="apple-modal-backdrop" onClick={() => setShowCustomMeal(false)}>
          <div class="apple-modal" onClick={(e) => e.stopPropagation()} style="max-width: 420px">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-lg font-semibold tracking-tight" style="color: var(--color-text)">
                Add Custom Meal
              </h2>
              <button class="btn btn-ghost p-1.5" style="padding: 0.375rem" onClick={() => setShowCustomMeal(false)}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div class="flex flex-col gap-4">
              <div>
                <label class="block text-sm font-medium mb-1.5" style="color: var(--color-text)">
                  Meal Name
                </label>
                <input
                  class="apple-input"
                  placeholder="My Custom Meal"
                  value={customName()}
                  onInput={(e) => setCustomName(e.currentTarget.value)}
                />
              </div>
              <div>
                <label class="block text-sm font-medium mb-1.5" style="color: var(--color-text)">
                  Calories
                </label>
                <input
                  type="number"
                  class="apple-input"
                  placeholder="400"
                  value={customCal()}
                  onInput={(e) => setCustomCal(e.currentTarget.value)}
                />
              </div>
              <div class="grid grid-cols-3 gap-3">
                <div>
                  <label class="block text-sm font-medium mb-1.5" style="color: var(--color-text)">
                    Protein (g)
                  </label>
                  <input
                    type="number"
                    class="apple-input"
                    placeholder="30"
                    value={customPro()}
                    onInput={(e) => setCustomPro(e.currentTarget.value)}
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium mb-1.5" style="color: var(--color-text)">
                    Carbs (g)
                  </label>
                  <input
                    type="number"
                    class="apple-input"
                    placeholder="40"
                    value={customCarbs()}
                    onInput={(e) => setCustomCarbs(e.currentTarget.value)}
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium mb-1.5" style="color: var(--color-text)">
                    Fat (g)
                  </label>
                  <input
                    type="number"
                    class="apple-input"
                    placeholder="15"
                    value={customFat()}
                    onInput={(e) => setCustomFat(e.currentTarget.value)}
                  />
                </div>
              </div>
              <button class="btn btn-primary w-full justify-center" onClick={addCustomMeal}>
                Add Meal
              </button>
            </div>
          </div>
        </div>
      </Show>
    </div>
  )
}
