import sqlite3
def show_student():
    conn = sqlite3.connect(r"C:\Users\User\Desktop\VS Code\registrater_student.db")
    c = conn.cursor()
    c.execute('''SELECT * FROM users''')
    result = c.fetchall()
    for x in result :
        print("{0:-<100}".format(""))
        print("{0:^100}".format("Student Information"))
        print("{0:-<100}".format(""))
        print("{0:<5}{1:<20}{2:<20}{3:<30}{4:<10}{5:<5}{6:<5}".format("No","Firstname","Lastname","Email","Gender","Age","Grade"))
        print("{0:<5}{1:<20}{2:<20}{3:<30}{4:<10}{5:<5}{6:<5}".format(x[0],x[1],x[2],x[3],x[4],x[5],x[6]))
        print("{0:-<100}".format(""))
    conn.commit()
    conn.close()

def add_student():
    conn = sqlite3.connect(r"C:\Users\User\Desktop\VS Code\registrater_student.db")
    c =conn.cursor()
    while True:
        fname = input("Enter your firstname : ")
        lname = input("Enter your lastname : ")
        email = input("Enter your email : ")
        gender = input("Enter your gender : ")
        age = input("Enter your age : ")
        grade = input("Enter your grade : ")
        c.execute ('''INSERT INTO users (id,fname,lname,email,gender,age,grade) VALUES(NULL,?,?,?,?,?,?)''',(fname,lname,email,gender,age,grade))
        choice = input("Do you want to add more student information? (Y/N) : ").upper()
        if choice == 'Y':
            continue
        elif choice == 'N':
            break
    conn.commit()
    conn.close()

def del_student():
    conn = sqlite3.connect(r"C:\Users\User\Desktop\VS Code\registrater_student.db")
    c = conn.cursor()
    while True:
        choice = input("Enter your id that you want to delete : ")
        c.execute('DELETE FROM users WHERE id = ?',choice)
        choice = input("Do you want to remove more student information? (Y/N) : ").upper()
        if choice == 'Y':
            continue
        elif choice == 'N':
            break
    conn.commit()
    conn.close()

def update_student():
    conn = sqlite3.connect(r"C:\Users\User\Desktop\VS Code\registrater_student.db")
    c = conn.cursor()
    while True:
        fname = input("Enter your data to change your firstname : ")
        lname = input("Enter your data to change your lastname : ")
        email = input("Enter your data to change your email : ")
        gender = input("Enter your data to change your gender : ")
        age = input("Enter your data to change your age : ")
        grade = input("Enter your data to change your grade : ")
        c.execute('''UPDATE users SET fname = ?,lname = ?,email = ?,gender = ?,age = ?,grade = ?''',(fname,lname,email,gender,age,grade))
        choice = input("Do you want to update more student information? (Y/N) : ").upper()
        if choice == 'Y':
            continue
        elif choice == 'N':
            break
    conn.commit()
    conn.close()
while True:
    print("{0:-<100}".format(""))
    print("{0:^100}".format("Student Registration System"))
    print("{0:-<100}".format(""))
    print("{0:<28}{1:<4}".format("Add Student Information","[A]"))
    print("{0:<28}{1:<4}".format("Show Student Information","[S]"))
    print("{0:<28}{1:<4}".format("Update Student Information","[E]"))
    print("{0:<28}{1:<4}".format("Delete Student INformation","[D]"))
    print("{0:<28}{1:<4}".format("Exit from program","[X]"))
    choice = input("Plese Enter you menu : ").upper()
    if choice == 'A':
        add_student()
    elif choice == 'S':
        show_student()
    elif choice == 'E':
        update_student()
    elif choice == 'D':
        del_student()
    elif choice == 'X':
        print("Exiting form program.")
        break