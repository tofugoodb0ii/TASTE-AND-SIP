import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
c = conn.cursor()
try :
    data = ('ABC','XYZ','ABC@gmailcom','13') #select row in last index
    c.execute('''UPDATE users SET fname = ? , lname = ? , email = ? WHERE id = ?''',data) 
    conn.commit()
    c.close()
except sqlite3.Error as e :
    print(e)
finally :
    if conn :
        conn.close()