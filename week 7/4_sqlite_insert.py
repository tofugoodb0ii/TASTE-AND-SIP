import sqlite3
def insertTousers(fname, lname, email):
    try :
        conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
        c = conn.cursor()

        sql = '''INSERT INTO users (fname, lname, email) VALUES (?, ?, ?)'''
        data = (fname, lname, email)
        c.execute(sql, data)

        conn.commit()
        print("Insert success:", fname, lname, email)
        
    except sqlite3.Error as e:
        print('Failed to insert:', e)
    finally :
        if conn :
            conn.close()
insertTousers('Guido', 'Rossum', 'python@gmail.com')
insertTousers('Dennis', 'Ritchie', 'abc@gmail.com')
