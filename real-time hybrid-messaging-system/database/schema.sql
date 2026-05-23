CREATE TABLE IF NOT EXISTS clients(
    client_id TEXT PRIMARY KEY,
    ip TEXT,
    port TEXT
);

CREATE TABLE IF NOT EXISTS Messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT,
    receiver TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);