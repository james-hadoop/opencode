import { sqliteTable, text, integer, index } from "drizzle-orm/sqlite-core"

export const Timestamps = {
  time_created: integer()
    .notNull()
    .$default(() => Date.now()),
  time_updated: integer()
    .notNull()
    .$onUpdate(() => Date.now()),
}

// Users
export const UserTable = sqliteTable(
  "health_user",
  {
    id: text().primaryKey(),
    name: text().notNull(),
    email: text().notNull().unique(),
    password_hash: text().notNull(),
    ...Timestamps,
  },
  (table) => [index("user_email_idx").on(table.email)],
)

// Health Metrics (daily snapshots)
export const MetricTable = sqliteTable(
  "health_metric",
  {
    id: text().primaryKey(),
    user_id: text()
      .notNull()
      .references(() => UserTable.id, { onDelete: "cascade" }),
    date: integer().notNull(),
    heart_rate: integer(),
    calories: integer(),
    steps: integer(),
    sleep_hours: integer(),
    hydration_ml: integer(),
    weight_kg: integer(),
    blood_pressure_systolic: integer(),
    blood_pressure_diastolic: integer(),
    ...Timestamps,
  },
  (table) => [index("metric_user_idx").on(table.user_id), index("metric_user_date_idx").on(table.user_id, table.date)],
)

// Water intake logs
export const WaterLogTable = sqliteTable(
  "health_water_log",
  {
    id: text().primaryKey(),
    user_id: text()
      .notNull()
      .references(() => UserTable.id, { onDelete: "cascade" }),
    amount_ml: integer().notNull(),
    logged_at: integer().notNull(),
    ...Timestamps,
  },
  (table) => [
    index("water_user_idx").on(table.user_id),
    index("water_user_date_idx").on(table.user_id, table.logged_at),
  ],
)

// Activities
export const ActivityTable = sqliteTable(
  "health_activity",
  {
    id: text().primaryKey(),
    user_id: text()
      .notNull()
      .references(() => UserTable.id, { onDelete: "cascade" }),
    title: text().notNull(),
    duration_minutes: integer().notNull(),
    calories_burned: integer(),
    type: text().notNull(),
    logged_at: integer().notNull(),
    ...Timestamps,
  },
  (table) => [
    index("activity_user_idx").on(table.user_id),
    index("activity_user_date_idx").on(table.user_id, table.logged_at),
  ],
)

// Meal plans
export const MealPlanTable = sqliteTable(
  "health_meal_plan",
  {
    id: text().primaryKey(),
    user_id: text()
      .notNull()
      .references(() => UserTable.id, { onDelete: "cascade" }),
    name: text().notNull(),
    calories: integer().notNull(),
    protein_g: integer().notNull(),
    carbs_g: integer().notNull(),
    fat_g: integer().notNull(),
    meal_type: text().notNull(),
    emoji: text().notNull(),
    notes: text(),
    logged_at: integer().notNull(),
    ...Timestamps,
  },
  (table) => [index("meal_user_idx").on(table.user_id), index("meal_user_date_idx").on(table.user_id, table.logged_at)],
)

// Symptom logs
export const SymptomTable = sqliteTable(
  "health_symptom_log",
  {
    id: text().primaryKey(),
    user_id: text()
      .notNull()
      .references(() => UserTable.id, { onDelete: "cascade" }),
    symptom_name: text().notNull(),
    severity: text().notNull(),
    duration: text(),
    notes: text(),
    logged_at: integer().notNull(),
    ...Timestamps,
  },
  (table) => [
    index("symptom_user_idx").on(table.user_id),
    index("symptom_user_date_idx").on(table.user_id, table.logged_at),
  ],
)

// Appointments
export const AppointmentTable = sqliteTable(
  "health_appointment",
  {
    id: text().primaryKey(),
    user_id: text()
      .notNull()
      .references(() => UserTable.id, { onDelete: "cascade" }),
    title: text().notNull(),
    doctor: text(),
    location: text(),
    appointment_type: text().notNull(),
    appointment_date: integer().notNull(),
    appointment_time: text().notNull(),
    notes: text(),
    completed: integer()
      .notNull()
      .$default(() => 0),
    ...Timestamps,
  },
  (table) => [
    index("apt_user_idx").on(table.user_id),
    index("apt_user_date_idx").on(table.user_id, table.appointment_date),
  ],
)

// Article bookmarks
export const BookmarkTable = sqliteTable(
  "health_bookmark",
  {
    id: text().primaryKey(),
    user_id: text()
      .notNull()
      .references(() => UserTable.id, { onDelete: "cascade" }),
    article_id: text().notNull(),
    ...Timestamps,
  },
  (table) => [index("bookmark_user_idx").on(table.user_id)],
)
