import sqlite3

# 1. Connect to SQLite DB (creates file if it doesn't exist)
conn = sqlite3.connect("network_monitor.db")
cursor = conn.cursor()

# 2. Create Device Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS Device (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    location TEXT,
    status TEXT CHECK(status IN ('online', 'offline', 'warning')) NOT NULL,
    last_checked DATETIME,
    notes TEXT
);
""")

# 3. Create Metrics Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS Metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    cpu_usage REAL,
    memory_usage REAL,
    bandwidth REAL,
    ping_latency REAL,
    packet_loss REAL,
    uptime INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES Device(id) ON DELETE CASCADE
);
""")

# 4. Create User Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS User (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin', 'viewer')) NOT NULL
);
""")

# 5. Commit and close connection
conn.commit()
conn.close()

print("✅ Database & Tables created successfully.")
