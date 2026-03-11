import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
c = conn.cursor()
try :
    c.execute('DELETE FROM users WHERE id = 1')
    conn.commit()
    c.close()
except sqlite3.Error as e :
    print(e)
finally :
    if conn :
        conn.close()