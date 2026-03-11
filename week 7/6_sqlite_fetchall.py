import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
c = conn.cursor()

c.execute('''SELECT * FROM users''')

result = c.fetchall()
for x in result :
    print(x)