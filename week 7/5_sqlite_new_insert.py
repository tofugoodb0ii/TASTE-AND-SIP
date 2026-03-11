import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
c = conn.cursor() 
try :
    data = ('kittikorn','kingwichit','nnemail'),('rapirat','wangdongbang','jjemail'),('maysa','maysa','maysa')
    c.executemany('INSERT INTO users (fname,lname,email) VALUES (?,?,?)',data)
    conn.commit()
    c.close()
except sqlite3.Error as e :
    print(e)
finally :
    if conn :
        conn.close()
