import sqlite3

def init_db():
    conn = sqlite3.connect("detections.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        detected_class TEXT NOT NULL,
        confidence REAL NOT NULL,
        detection_datetime TEXT NOT NULL,
        sent_to_1c INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()
    print("База данных успешно создана или уже существует.")

if __name__ == "__main__":
    init_db()
