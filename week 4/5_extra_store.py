#store no.2
pplist = []
while True :
    print('-----------------------\n      P. the mhee \n----------------------- ')
    print("\n add data : press A \n show customer data : press B \n log out : press C \n")
    x = input("select an obtion : ").upper()
    if x == "A" :
        print('\nwe will receive your information')
        t = input('code : name : province =  ')
        pplist.append(t)
        print('\n----------------------------------------------\n           your data have been saved \n---------------------------------------------- ')
    elif x == "B" :
        print("{0:-<30}".format(""))
        print("{0:-<6} {1:-<10} {2:-<10}".format("code","name","province"))
        print("{0:-<30}".format(""))
        for y in pplist :
            e = y.split(":")
            print("{0[0]:<6} {0[1]:<10} {0[2]:<10}".format(e))
    elif x == "C" :
        confirmation = input("do you want to log out (y/n) : ").lower()
        if confirmation == 'y' :
            print('\n----------------------------------------------\n           you have been logged out \n---------------------------------------------- ')
            break
        elif confirmation == 'n':
            continue