import { Hono } from "hono"
import { cors } from "hono/cors"
import { getCookie, setCookie, deleteCookie } from "hono/cookie"
import { createHmac, timingSafeEqual } from "crypto"
import { queryAll, queryOne, run } from "./db/index"

function hashPassword(password: string): string {
  return createHmac("sha256", "health-hub-secret-2024").update(password).digest("hex")
}

function verifyPassword(password: string, hash: string): boolean {
  const inputHash = hashPassword(password)
  return timingSafeEqual(Buffer.from(inputHash), Buffer.from(hash))
}

function generateToken(): string {
  return createHmac("sha256", "health-hub-token-secret")
    .update(Date.now().toString() + Math.random().toString())
    .digest("hex")
}

const TOKEN_COOKIE = "health_token"
const TOKEN_EXPIRY = 7 * 24 * 60 * 60 * 1000

const tokens = new Map<string, { userId: string; expires: number }>()

function getUserIdFromToken(token: string): string | null {
  const stored = tokens.get(token)
  if (!stored) return null
  if (stored.expires < Date.now()) {
    tokens.delete(token)
    return null
  }
  return stored.userId
}

export function createApp() {
  const app = new Hono()

  app.use(
    cors({
      origin: "http://localhost:3001",
      credentials: true,
    }),
  )

  // Auth middleware
  app.use("/*", async (c, next) => {
    const path = c.req.path
    const publicPaths = ["/api/auth/login", "/api/auth/register", "/api/articles"]
    if (publicPaths.some((p) => path.startsWith(p))) return next()

    const token = getCookie(c, TOKEN_COOKIE) || c.req.header("Authorization")?.replace("Bearer ", "")
    if (!token) return c.json({ error: "Unauthorized" }, 401)
    const userId = getUserIdFromToken(token)
    if (!userId) return c.json({ error: "Invalid or expired token" }, 401)
    c.set("userId", userId)
    return next()
  })

  // Register
  app.post("/api/auth/register", async (c) => {
    const { name, email, password } = await c.req.json()
    if (!name || !email || !password) return c.json({ error: "All fields are required" }, 400)
    if (password.length < 6) return c.json({ error: "Password must be at least 6 characters" }, 400)

    const existing = queryOne<{ id: string }>("SELECT id FROM health_user WHERE email = ?", [email])
    if (existing) return c.json({ error: "Email already registered" }, 409)

    const id = crypto.randomUUID()
    const now = Date.now()
    run(
      "INSERT INTO health_user (id, name, email, password_hash, time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?)",
      [id, name, email, hashPassword(password), now, now],
    )

    const token = generateToken()
    tokens.set(token, { userId: id, expires: Date.now() + TOKEN_EXPIRY })
    setCookie(c, TOKEN_COOKIE, token, { httpOnly: true, maxAge: TOKEN_EXPIRY / 1000, path: "/", sameSite: "Lax" })
    return c.json({ token, user: { id, name, email } })
  })

  // Login
  app.post("/api/auth/login", async (c) => {
    const { email, password } = await c.req.json()
    if (!email || !password) return c.json({ error: "Email and password are required" }, 400)

    const user = queryOne<{ id: string; name: string; email: string; password_hash: string }>(
      "SELECT * FROM health_user WHERE email = ?",
      [email],
    )
    if (!user || !verifyPassword(password, user.password_hash)) {
      return c.json({ error: "Invalid email or password" }, 401)
    }

    const token = generateToken()
    tokens.set(token, { userId: user.id, expires: Date.now() + TOKEN_EXPIRY })
    setCookie(c, TOKEN_COOKIE, token, { httpOnly: true, maxAge: TOKEN_EXPIRY / 1000, path: "/", sameSite: "Lax" })
    return c.json({ token, user: { id: user.id, name: user.name, email: user.email } })
  })

  // Logout
  app.post("/api/auth/logout", (c) => {
    const token = getCookie(c, TOKEN_COOKIE)
    if (token) {
      tokens.delete(token)
      deleteCookie(c, TOKEN_COOKIE)
    }
    return c.json({ success: true })
  })

  // Me
  app.get("/api/auth/me", (c) => {
    const userId = c.get("userId")
    const user = queryOne<{ id: string; name: string; email: string }>(
      "SELECT id, name, email FROM health_user WHERE id = ?",
      [userId],
    )
    if (!user) return c.json({ error: "User not found" }, 404)
    return c.json({ user })
  })

  // Metrics
  app.get("/api/metrics", (c) => {
    const userId = c.get("userId")
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayStart = today.getTime()
    const todayEnd = todayStart + 86400000 - 1

    const metrics = queryAll<any>("SELECT * FROM health_metric WHERE user_id = ? AND date >= ? AND date <= ? LIMIT 1", [
      userId,
      todayStart,
      todayEnd,
    ])

    if (metrics.length === 0) {
      return c.json([
        {
          label: "Heart Rate",
          value: "72",
          unit: "bpm",
          trend: "neutral",
          trendValue: "Normal range",
          color: "#DC2626",
        },
        { label: "Calories", value: "0", unit: "kcal", trend: "up", trendValue: "No data yet", color: "#D97706" },
        { label: "Hydration", value: "0", unit: "mL", trend: "up", trendValue: "0 of 2500mL", color: "#0891B2" },
        { label: "Sleep", value: "7.5", unit: "hrs", trend: "up", trendValue: "Good sleep", color: "#8B5CF6" },
        { label: "Steps", value: "0", unit: "steps", trend: "down", trendValue: "No data yet", color: "#059669" },
      ])
    }

    const m = metrics[0]
    return c.json([
      {
        label: "Heart Rate",
        value: m.heart_rate?.toString() || "—",
        unit: "bpm",
        trend: "neutral",
        trendValue: "Normal range",
        color: "#DC2626",
      },
      {
        label: "Calories",
        value: m.calories?.toString() || "0",
        unit: "kcal",
        trend: "up",
        trendValue: "Today",
        color: "#D97706",
      },
      {
        label: "Hydration",
        value: m.hydration_ml?.toString() || "0",
        unit: "mL",
        trend: "up",
        trendValue: `${m.hydration_ml || 0} of 2500mL`,
        color: "#0891B2",
      },
      {
        label: "Sleep",
        value: m.sleep_hours?.toString() || "—",
        unit: "hrs",
        trend: "up",
        trendValue: "Last night",
        color: "#8B5CF6",
      },
      {
        label: "Steps",
        value: m.steps?.toString() || "0",
        unit: "steps",
        trend: "down",
        trendValue: "No data yet",
        color: "#059669",
      },
    ])
  })

  app.post("/api/metrics", async (c) => {
    const userId = c.get("userId")
    const body = await c.req.json()
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayStart = today.getTime()
    const now = Date.now()

    const existing = queryOne<{ id: string }>("SELECT id FROM health_metric WHERE user_id = ? AND date = ?", [
      userId,
      todayStart,
    ])

    if (existing) {
      const updates: string[] = []
      const vals: any[] = []
      if (body.heart_rate !== undefined) {
        updates.push("heart_rate = ?")
        vals.push(body.heart_rate)
      }
      if (body.calories !== undefined) {
        updates.push("calories = ?")
        vals.push(body.calories)
      }
      if (body.steps !== undefined) {
        updates.push("steps = ?")
        vals.push(body.steps)
      }
      if (body.sleep_hours !== undefined) {
        updates.push("sleep_hours = ?")
        vals.push(body.sleep_hours)
      }
      if (body.hydration_ml !== undefined) {
        updates.push("hydration_ml = ?")
        vals.push(body.hydration_ml)
      }
      updates.push("time_updated = ?")
      vals.push(now)
      vals.push(existing.id)
      run(`UPDATE health_metric SET ${updates.join(", ")} WHERE id = ?`, vals)
    } else {
      const id = crypto.randomUUID()
      run(
        "INSERT INTO health_metric (id, user_id, date, heart_rate, calories, steps, sleep_hours, hydration_ml, time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
          id,
          userId,
          todayStart,
          body.heart_rate || null,
          body.calories || null,
          body.steps || null,
          body.sleep_hours || null,
          body.hydration_ml || null,
          now,
          now,
        ],
      )
    }
    return c.json({ success: true })
  })

  // Water
  app.get("/api/water", (c) => {
    const userId = c.get("userId")
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayStart = today.getTime()
    const logs = queryAll<any>(
      "SELECT * FROM health_water_log WHERE user_id = ? AND logged_at >= ? ORDER BY logged_at DESC",
      [userId, todayStart],
    )
    const totalMl = logs.reduce((sum, l) => sum + (l.amount_ml || 0), 0)
    return c.json({ logs, totalMl, goal: 2500 })
  })

  app.post("/api/water", async (c) => {
    const userId = c.get("userId")
    const { amount_ml } = await c.req.json()
    if (!amount_ml || amount_ml <= 0) return c.json({ error: "Invalid amount" }, 400)
    const id = crypto.randomUUID()
    const now = Date.now()
    run(
      "INSERT INTO health_water_log (id, user_id, amount_ml, logged_at, time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?)",
      [id, userId, amount_ml, now, now, now],
    )
    return c.json({ success: true, id, logged_at: now })
  })

  // Activities
  app.get("/api/activities", (c) => {
    const userId = c.get("userId")
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayStart = today.getTime()
    const activities = queryAll<any>(
      "SELECT * FROM health_activity WHERE user_id = ? AND logged_at >= ? ORDER BY logged_at DESC",
      [userId, todayStart],
    )
    return c.json(
      activities.map((a) => ({
        id: a.id,
        title: a.title,
        time: new Date(a.logged_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
        duration: `${a.duration_minutes} min`,
        tagType: "tag-green",
        icon: "activity",
        color: "#059669",
        type: a.type,
        calories_burned: a.calories_burned,
      })),
    )
  })

  app.post("/api/activities", async (c) => {
    const userId = c.get("userId")
    const { title, duration_minutes, calories_burned, type } = await c.req.json()
    if (!title || !duration_minutes) return c.json({ error: "Title and duration required" }, 400)
    const id = crypto.randomUUID()
    const now = Date.now()
    run(
      "INSERT INTO health_activity (id, user_id, title, duration_minutes, calories_burned, type, logged_at, time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
      [id, userId, title, duration_minutes, calories_burned || null, type || "exercise", now, now, now],
    )
    return c.json({ success: true, id })
  })

  app.delete("/api/activities/:id", (c) => {
    const userId = c.get("userId")
    const { id } = c.req.param()
    run("DELETE FROM health_activity WHERE id = ? AND user_id = ?", [id, userId])
    return c.json({ success: true })
  })

  // Meals
  app.get("/api/meals", (c) => {
    const userId = c.get("userId")
    const day = c.req.query("day")
    const date = day ? new Date(day).setHours(0, 0, 0, 0) : new Date().setHours(0, 0, 0, 0)
    const meals = queryAll<any>(
      "SELECT * FROM health_meal_plan WHERE user_id = ? AND logged_at = ? ORDER BY time_created ASC",
      [userId, date],
    )
    return c.json(
      meals.map((m) => ({
        id: m.id,
        name: m.name,
        calories: m.calories,
        protein: m.protein_g,
        carbs: m.carbs_g,
        fat: m.fat_g,
        type: m.meal_type,
        emoji: m.emoji,
        time: new Date(m.logged_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
        notes: m.notes,
      })),
    )
  })

  app.post("/api/meals", async (c) => {
    const userId = c.get("userId")
    const body = await c.req.json()
    if (!body.name || body.calories === undefined || !body.meal_type)
      return c.json({ error: "Missing required fields" }, 400)
    const id = crypto.randomUUID()
    const now = Date.now()
    run(
      "INSERT INTO health_meal_plan (id, user_id, name, calories, protein_g, carbs_g, fat_g, meal_type, emoji, notes, logged_at, time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
      [
        id,
        userId,
        body.name,
        body.calories,
        body.protein_g || 0,
        body.carbs_g || 0,
        body.fat_g || 0,
        body.meal_type,
        body.emoji || "🍽️",
        body.notes || null,
        body.logged_at || now,
        now,
        now,
      ],
    )
    return c.json({ success: true, id })
  })

  app.delete("/api/meals/:id", (c) => {
    const userId = c.get("userId")
    const { id } = c.req.param()
    run("DELETE FROM health_meal_plan WHERE id = ? AND user_id = ?", [id, userId])
    return c.json({ success: true })
  })

  app.put("/api/meals/:id", async (c) => {
    const userId = c.get("userId")
    const { id } = c.req.param()
    const body = await c.req.json()
    run(
      "UPDATE health_meal_plan SET name = ?, calories = ?, protein_g = ?, carbs_g = ?, fat_g = ?, meal_type = ?, emoji = ?, notes = ?, time_updated = ? WHERE id = ? AND user_id = ?",
      [
        body.name,
        body.calories,
        body.protein_g || 0,
        body.carbs_g || 0,
        body.fat_g || 0,
        body.meal_type,
        body.emoji,
        body.notes,
        Date.now(),
        id,
        userId,
      ],
    )
    return c.json({ success: true })
  })

  // Symptoms
  app.get("/api/symptoms", (c) => {
    const userId = c.get("userId")
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayStart = today.getTime()
    const symptoms = queryAll<any>(
      "SELECT * FROM health_symptom_log WHERE user_id = ? AND logged_at >= ? ORDER BY logged_at DESC",
      [userId, todayStart],
    )
    return c.json(
      symptoms.map((s) => ({
        id: s.id,
        symptom_name: s.symptom_name,
        severity: s.severity,
        duration: s.duration,
        notes: s.notes,
        logged_at: s.logged_at,
        possibleCauses: symptomCauses[s.symptom_name.toLowerCase()]?.causes || [],
        recommendation:
          symptomCauses[s.symptom_name.toLowerCase()]?.recommendation || "Consult a healthcare professional.",
        urgency: symptomCauses[s.symptom_name.toLowerCase()]?.urgency || "medium",
      })),
    )
  })

  app.post("/api/symptoms", async (c) => {
    const userId = c.get("userId")
    const { symptom_name, severity, duration, notes } = await c.req.json()
    if (!symptom_name || !severity) return c.json({ error: "Name and severity required" }, 400)
    const id = crypto.randomUUID()
    const now = Date.now()
    run(
      "INSERT INTO health_symptom_log (id, user_id, symptom_name, severity, duration, notes, logged_at, time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
      [id, userId, symptom_name, severity, duration || null, notes || null, now, now, now],
    )
    return c.json({ success: true, id })
  })

  app.delete("/api/symptoms/:id", (c) => {
    const userId = c.get("userId")
    const { id } = c.req.param()
    run("DELETE FROM health_symptom_log WHERE id = ? AND user_id = ?", [id, userId])
    return c.json({ success: true })
  })

  // Appointments
  app.get("/api/appointments", (c) => {
    const userId = c.get("userId")
    const now = Date.now()
    const cutoff = now - 7 * 86400000
    const appointments = queryAll<any>(
      "SELECT * FROM health_appointment WHERE user_id = ? AND appointment_date >= ? ORDER BY appointment_date ASC",
      [userId, cutoff],
    )
    return c.json(
      appointments.map((a) => {
        const d = new Date(a.appointment_date)
        return {
          id: a.id,
          title: a.title,
          day: d.getDate().toString(),
          month: d.toLocaleString("en-US", { month: "short" }),
          time: a.appointment_time,
          location: a.location,
          type: a.appointment_type,
          doctor: a.doctor,
          notes: a.notes,
          completed: a.completed === 1,
        }
      }),
    )
  })

  app.post("/api/appointments", async (c) => {
    const userId = c.get("userId")
    const { title, doctor, location, appointment_type, appointment_date, appointment_time, notes } = await c.req.json()
    if (!title || !appointment_type || !appointment_date || !appointment_time)
      return c.json({ error: "Required fields missing" }, 400)
    const id = crypto.randomUUID()
    const now = Date.now()
    run(
      "INSERT INTO health_appointment (id, user_id, title, doctor, location, appointment_type, appointment_date, appointment_time, notes, completed, time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
      [
        id,
        userId,
        title,
        doctor || null,
        location || null,
        appointment_type,
        appointment_date,
        appointment_time,
        notes || null,
        now,
        now,
      ],
    )
    return c.json({ success: true, id })
  })

  app.delete("/api/appointments/:id", (c) => {
    const userId = c.get("userId")
    const { id } = c.req.param()
    run("DELETE FROM health_appointment WHERE id = ? AND user_id = ?", [id, userId])
    return c.json({ success: true })
  })

  app.put("/api/appointments/:id", async (c) => {
    const userId = c.get("userId")
    const { id } = c.req.param()
    const { completed } = await c.req.json()
    run("UPDATE health_appointment SET completed = ?, time_updated = ? WHERE id = ? AND user_id = ?", [
      completed ? 1 : 0,
      Date.now(),
      id,
      userId,
    ])
    return c.json({ success: true })
  })

  // Bookmarks
  app.get("/api/bookmarks", (c) => {
    const userId = c.get("userId")
    const bookmarks = queryAll<{ article_id: string }>("SELECT article_id FROM health_bookmark WHERE user_id = ?", [
      userId,
    ])
    return c.json(bookmarks.map((b) => b.article_id))
  })

  app.post("/api/bookmarks/:articleId", (c) => {
    const userId = c.get("userId")
    const { articleId } = c.req.param()
    const existing = queryOne("SELECT id FROM health_bookmark WHERE user_id = ? AND article_id = ?", [
      userId,
      articleId,
    ])
    if (existing) return c.json({ success: true, bookmarked: true })
    const id = crypto.randomUUID()
    const now = Date.now()
    run("INSERT INTO health_bookmark (id, user_id, article_id, time_created, time_updated) VALUES (?, ?, ?, ?, ?)", [
      id,
      userId,
      articleId,
      now,
      now,
    ])
    return c.json({ success: true, bookmarked: true })
  })

  app.delete("/api/bookmarks/:articleId", (c) => {
    const userId = c.get("userId")
    const { articleId } = c.req.param()
    run("DELETE FROM health_bookmark WHERE user_id = ? AND article_id = ?", [userId, articleId])
    return c.json({ success: true, bookmarked: false })
  })

  return app
}

const server = createApp()
export default server

const symptomCauses: Record<string, { causes: string[]; recommendation: string; urgency: string }> = {
  headache: {
    causes: ["Dehydration", "Stress", "Lack of sleep", "Eye strain"],
    recommendation: "Drink water, rest in a quiet room.",
    urgency: "low",
  },
  fatigue: {
    causes: ["Anemia", "Thyroid issues", "Poor sleep"],
    recommendation: "Consider blood tests. Ensure 7-9 hours sleep.",
    urgency: "medium",
  },
  "chest pain": {
    causes: ["Anxiety", "Heart conditions", "Acid reflux"],
    recommendation: "Seek immediate care if with shortness of breath.",
    urgency: "high",
  },
  "joint pain": {
    causes: ["Arthritis", "Overuse", "Vitamin D deficiency"],
    recommendation: "Apply warm compress. Consult doctor if persistent.",
    urgency: "low",
  },
  "sore throat": {
    causes: ["Viral infection", "Bacterial infection", "Allergies"],
    recommendation: "Gargle salt water. See doctor if fever over 48h.",
    urgency: "low",
  },
  nausea: {
    causes: ["Food poisoning", "Pregnancy", "Migraine"],
    recommendation: "Stay hydrated with small sips.",
    urgency: "medium",
  },
  dizziness: {
    causes: ["Low blood sugar", "Dehydration", "Low BP"],
    recommendation: "Sit down. Drink water. Seek care if fainting.",
    urgency: "medium",
  },
  fever: {
    causes: ["Viral infection", "Bacterial infection"],
    recommendation: "Rest, hydrate. Seek care if over 39.5°C.",
    urgency: "medium",
  },
  cough: {
    causes: ["Cold/flu", "Allergies", "Asthma"],
    recommendation: "Hydrate. See doctor if over 3 weeks.",
    urgency: "low",
  },
  "back pain": {
    causes: ["Muscle strain", "Poor posture", "Disc issues"],
    recommendation: "Ice/heat. Stretch. Seek care if radiating pain.",
    urgency: "medium",
  },
}
