PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE OPCFiles(id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, string LOCATION, upload_date DATETIME DEFAULT CURRENT_TIMESTAMP);
COMMIT;