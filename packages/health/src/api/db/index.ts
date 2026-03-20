import { Database } from "bun:sqlite"
import { join } from "path"

const dbPath = join(process.cwd(), "health.db")
export const db = new Database(dbPath)

db.exec("PRAGMA journal_mode=WAL;")
db.exec("PRAGMA foreign_keys=ON;")

db.exec(`
  CREATE TABLE IF NOT EXISTS health_user (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    time_created INTEGER NOT NULL,
    time_updated INTEGER NOT NULL
  );

  CREATE TABLE IF NOT EXISTS health_metric (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    date INTEGER NOT NULL,
    heart_rate INTEGER,
    calories INTEGER,
    steps INTEGER,
    sleep_hours INTEGER,
    hydration_ml INTEGER,
    weight_kg INTEGER,
    blood_pressure_systolic INTEGER,
    blood_pressure_diastolic INTEGER,
    time_created INTEGER NOT NULL,
    time_updated INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES health_user(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS health_water_log (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    amount_ml INTEGER NOT NULL,
    logged_at INTEGER NOT NULL,
    time_created INTEGER NOT NULL,
    time_updated INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES health_user(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS health_activity (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    calories_burned INTEGER,
    type TEXT NOT NULL,
    logged_at INTEGER NOT NULL,
    time_created INTEGER NOT NULL,
    time_updated INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES health_user(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS health_meal_plan (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    calories INTEGER NOT NULL,
    protein_g INTEGER NOT NULL,
    carbs_g INTEGER NOT NULL,
    fat_g INTEGER NOT NULL,
    meal_type TEXT NOT NULL,
    emoji TEXT NOT NULL,
    notes TEXT,
    logged_at INTEGER NOT NULL,
    time_created INTEGER NOT NULL,
    time_updated INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES health_user(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS health_symptom_log (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    symptom_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    duration TEXT,
    notes TEXT,
    logged_at INTEGER NOT NULL,
    time_created INTEGER NOT NULL,
    time_updated INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES health_user(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS health_appointment (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    doctor TEXT,
    location TEXT,
    appointment_type TEXT NOT NULL,
    appointment_date INTEGER NOT NULL,
    appointment_time TEXT NOT NULL,
    notes TEXT,
    completed INTEGER NOT NULL DEFAULT 0,
    time_created INTEGER NOT NULL,
    time_updated INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES health_user(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS health_bookmark (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    article_id TEXT NOT NULL,
    time_created INTEGER NOT NULL,
    time_updated INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES health_user(id) ON DELETE CASCADE
  );

  CREATE INDEX IF NOT EXISTS user_email_idx ON health_user(email);
  CREATE INDEX IF NOT EXISTS metric_user_date_idx ON health_metric(user_id, date);
  CREATE INDEX IF NOT EXISTS water_user_date_idx ON health_water_log(user_id, logged_at);
  CREATE INDEX IF NOT EXISTS activity_user_date_idx ON health_activity(user_id, logged_at);
  CREATE INDEX IF NOT EXISTS meal_user_date_idx ON health_meal_plan(user_id, logged_at);
  CREATE INDEX IF NOT EXISTS symptom_user_date_idx ON health_symptom_log(user_id, logged_at);
  CREATE INDEX IF NOT EXISTS apt_user_date_idx ON health_appointment(user_id, appointment_date);
  CREATE INDEX IF NOT EXISTS bookmark_user_idx ON health_bookmark(user_id);
`)

// Helper query functions
export function queryAll<T = any>(sql: string, params: any[] = []): T[] {
  const stmt = db.query(sql)
  return stmt.all(...params) as T[]
}

export function queryOne<T = any>(sql: string, params: any[] = []): T | undefined {
  const stmt = db.query(sql)
  return stmt.get(...params) as T | undefined
}

export function run(sql: string, params: any[] = []): void {
  const stmt = db.query(sql)
  stmt.run(...params)
}
