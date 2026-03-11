total = 0

while True :
    print('\n{0:=<74}'.format(''))
    print('{0:^74}'.format(' -+ Calculater Program +- '))
    print('{0:=<74}'.format(''))
    print('{0:^74}'.format('MAIN MENU'))
    print('[1] standard','\n[2] extra','\n[X] exit') # [1] แบบเหมา , [2] แบบจ่ายเพิ่ม
    print('{0:=<74}'.format(''))
    option = input('\nselect an option : ')
    distance = int(input('\nplease input distance : '))
    if option == '1':
        if distance <= 25 :
            total = 25
        elif distance > 25 :
            total = 55
        print('\nyou must pay = ',total)
    elif option == '2' :
        if distance <= 25 :
            total = 25
        elif distance > 25:
            total = 55 + 25
        print('\nyou must pay = ',total)
    elif option == 'X' :
        break
    else :
        print('error, please try again')
 