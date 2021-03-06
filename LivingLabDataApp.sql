PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, username TEXT, password TEXT, register_date DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE CPCFiles(id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, username TEXT, start_date DATETIME, upload_date DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE OPCFiles(id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, location TEXT, upload_date DATETIME DEFAULT CURRENT_TIMESTAMP);
COMMIT;
