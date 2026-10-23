CREATE TABLE IF NOT EXISTS runs (          
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started TEXT DEFAULT (datetime('now','localtime')),
    episodes INTEGER, alpha REAL, gamma REAL,
    result TEXT);
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES runs(id),
    episode INTEGER, steps INTEGER, reward REAL, reached INTEGER);