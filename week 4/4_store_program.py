#ให้นักศึกษาเขียนโปรแกรมร้านค้าโดยมีระบบการทำงานอยู่ 3 ส่วน

#store no.1
pplist = []
p = 0
while True :
    print('-----------------------\n      P. the mhee \n----------------------- ')
    print("\n add data : press A \n show customer data : press B \n log out : press C \n")
    x = input("select an option : ").upper()
    if x == "A" :
        print('\nwe will receive your information')
        t = input('code : name : province =  ')
        pplist.append(t) 
        print('\n----------------------------------------------\n           your data have been saved \n---------------------------------------------- ')
    elif x == "B" :
        for y in pplist :
            print(f'{p+1}.' , y)
            p += 1
    elif x == "C" :
        confirmation = input("do you want to log out (y/n) : ").lower()
        if confirmation == 'y' :
            print('\n----------------------------------------------\n           you have been logged out \n---------------------------------------------- ')
            break
        elif confirmation == 'n':
            continue