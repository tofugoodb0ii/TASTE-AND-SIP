#order by desc (id)
import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
c = conn.cursor()
try :
    c.execute('SELECT * FROM users ORDER BY id DESC ') #sort id by max to min
    conn.commit()
    result = c.fetchall()
    for x in result :
        print(x)
except sqlite3.Error as e :
    print(e)
finally :
    if conn :
        conn.close()

#order by asc (id)
import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
c = conn.cursor()
try :
    c.execute('SELECT * FROM users ORDER BY id ASC ') #sort id by min to max
    conn.commit()
    result = c.fetchall()
    for x in result :
        print(x)
except sqlite3.Error as e :
    print(e)
finally :
    if conn :
        conn.close()


#order by asc (fname)
import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
c = conn.cursor()
try :
    c.execute('SELECT * FROM users ORDER BY fname ASC ') #sort first name (fname) by min to max
    conn.commit()
    result = c.fetchall()
    for x in result :
        print(x)
except sqlite3.Error as e :
    print(e)
finally :
    if conn :
        conn.close()

