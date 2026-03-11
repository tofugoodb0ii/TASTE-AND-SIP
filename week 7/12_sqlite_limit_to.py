import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
c = conn.cursor()
try :
    c.execute('SELECT * FROM users LIMIT 5 OFFSET 2 ') # 5 start by 2
    result = c.fetchall()
    for x in result :
        print(x)
    c.close()
except sqlite3.Error as e :
    print(e)
finally :
    if conn :
        conn.close()