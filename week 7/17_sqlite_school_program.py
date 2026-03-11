import sqlite3
conn = sqlite3.connect(r"C:\Users\thatt\OneDrive\Desktop\python\kku_school.db")
c = conn.cursor()
i = 0 
c.execute('''CREATE TABLE IF NOT EXISTS users (
          id VARCHAR(50),
          fname VARCHAR(50) NOT NULL,
          lname VARCHAR(50) NOT NULL,
          email VARCHAR(30) NOT NULL ,
          gender VARCHAR(10) NOT NULL , 
          age VARCHAR(10) NOT NULL ,
          year VARCHAR(10) NOT NULL)''')
conn.commit()

def add_student_data() :
    num = int(input('\nplease input number of students : '))
    for i in range(num) :
        id = str(input("\nplease input student's id : "))
        fname = input("please input student's first name : ")
        lname = input("please input student's last name : ")
        email = input("please input student's email : ")
        gender = input("please input student's gender : ")
        age = str(input("please input student's age : "))
        year = str(input("please input student's year : "))
        c.execute('''INSERT INTO users (id,fname,lname,email,gender,age,year) VALUES (?,?,?,?,?,?,?)''',(id,fname,lname,email,gender,age,year))
        conn.commit()
    print('\n{0:^100}'.format('All student data inserted successfully!'))

def show_student_data() :
    print('{0:=<100}'.format(''))
    print('{0:^100}'.format("Student's Data"))         
    print('{0:=<100}'.format(''))
    print('{0:<10}{1:<12}{2:<12}{3:<25}{4:<10}{5:<8}{6:<10}'.format('ID', 'F-NAME', 'L-NAME', 'E-mail', 'GENDER', 'AGE', 'YEAR'))
    print('{0:=<100}'.format(''))
    #ใช้ .execute ดึงข้อมูลจากฐานข้อมูล
    c.execute("SELECT id, fname, lname, email, gender, age, year FROM users")
    result = c.fetchall()
    if not result :
        print("{0:^100}".format("No data"))
    else :
        for (id,fname,lname,email,gender,age,year) in result :
            print('{0:<10}{1:<12}{2:<12}{3:<25}{4:<10}{5:<8}{6:<10}'.format(id, fname, lname, email, gender, age, year))
    print('{0:=<100}'.format(''))

def edit_student_data() :
    while True :
        sid = input("Enter student id to update : ")
        fname = input("Enter new firstname : ")
        lname = input("Enter new lastname : ")
        email = input("Enter new email : ")
        gender = input("Enter new gender : ")
        age = input("Enter new age : ")
        year = input("Enter new grade : ")
        c.execute('''UPDATE users SET fname=?, lname=?, email=?, gender=?, age=?, year=? WHERE id=?''', (fname, lname, email, gender, age, year, sid))
        conn.commit()
        choice = input("Do you want to update more student information? (Y/N) : ").upper()
        if choice == 'N':
            break

def delete_student_data() :
    print('\n{0:=<100}'.format(''))
    print('{0:^100}'.format("Delete Student's Data"))         
    print('{0:=<100}'.format(''))
    sid = input("enter student's id to delete : ").strip()
    c.execute("SELECT 1 FROM users WHERE id = ?",(sid,))
    if not c.fetchone() :
        print("{0:^100}".format("data not found"))
        return
    confirm = input(f"are you sure to delete id '{sid}' (Y/N) : ").strip().upper()
    if confirm == 'Y' :
        c.execute("DELETE FROM users WHERE id = ?", (sid,))
        conn.commit()
        print('\n{0:^100}'.format('delete successfully!'))
    elif confirm == 'N' :
        print('\n{0:^100}'.format('canceled'))
    else :
        print('\n{0:^100}'.format('Error , please try again'))

def menu() :
        while True :
            print('\n{0:=<100}'.format(''))
            print('{0:^100}'.format(' -+ KKU SCHOOL +- '))
            print('{0:=<100}'.format(''))
            print('{0:^100}'.format('- MAIN MENU -'))
            print("[A] Add Student's Data \n[S] Show Student's Data \n[E] Edit Student's Data \n[D] Delete Stydent's Data \n[X] Exit Program")
            print('{0:=<100}'.format(''))
            option = input("\nSelect an option : ").upper()
            if option == "A" :
                add_student_data()
            elif option == "S" :
                show_student_data()
            elif option == "E" :
                edit_student_data()
            elif option == 'D' :
                delete_student_data()
            elif option == "X" :
                confirmation = input("\nDo you want to exit program (Y/N) : ").upper()
                if confirmation == 'N' :
                     continue
                elif confirmation == 'Y' :
                    print("\nTime to say goodbye!")
                    conn.close()
                    break
                else :
                    print('\nError , please try again')
menu()