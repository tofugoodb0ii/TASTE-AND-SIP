import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\example.db")
c = conn.cursor()
c.execute('''INSERT INTO users (id,fname,lname,email) VALUES (NULL,"thatthep","thiaksom","p")''')
c.execute('''INSERT INTO users VALUES (NULL,"jay","jay","jay")''')
conn.commit()
conn.close()