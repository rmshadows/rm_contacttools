-- ContactTools SQLite schema（LibreOffice Base 通过 JDBC 连接此库）

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS contacts (
    id          TEXT PRIMARY KEY,
    fn          TEXT NOT NULL,
    fn_pinyin   TEXT,
    n_family    TEXT,
    n_given     TEXT NOT NULL,
    org         TEXT,
    title       TEXT,
    note        TEXT,
    url         TEXT,
    photo       BLOB,
    source      TEXT,
    imported_at TEXT,
    updated_at  TEXT
);

CREATE TABLE IF NOT EXISTS phones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id   TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    number       TEXT NOT NULL,
    types        TEXT NOT NULL DEFAULT 'CELL',
    pref         INTEGER NOT NULL DEFAULT 0,
    sort_order   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_phones_number ON phones(number);
CREATE INDEX IF NOT EXISTS idx_phones_contact ON phones(contact_id);

CREATE TABLE IF NOT EXISTS emails (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id   TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    address      TEXT NOT NULL,
    types        TEXT NOT NULL DEFAULT 'HOME',
    sort_order   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS import_batches (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filename     TEXT NOT NULL,
    imported_at  TEXT NOT NULL,
    contact_count INTEGER NOT NULL,
    mode         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS merge_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    kept_id         TEXT NOT NULL,
    merged_id       TEXT NOT NULL,
    merged_snapshot TEXT NOT NULL,
    merged_at       TEXT NOT NULL
);

-- 视图定义见 views.sql（init_schema 时由 database._migrate_views 创建）
