import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fname VARCHAR(30) NOT NULL,
                lname VARCHAR(30) NOT NULL,
                email VARCHAR(30) NOT NULL
            )''')
conn.commit()
conn.close()