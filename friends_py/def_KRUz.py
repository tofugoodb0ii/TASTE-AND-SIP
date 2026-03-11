cart = []
def Nike() :
    while True :
        if option == '1' :
            print('\n{0:-<70}'.format(''))
            print('{0:^70}'.format('-+ Nike +-'))
            print('\n{0:-<70}'.format(''))
            print('[1] Nike Air Force 1 - 4700 baht') 
            print('[2] Nike Air Jordan 1 Mid SE - 5300 baht') 
            print('[3] Nike Dunk Low Retro - 3700 baht') 
            print('[X] Exit to menu')
            choice = str(input("Select Nike shoe : ")).upper()
            if choice == '1':
                cart.append(['Air Force 1', 4700])
            elif choice == '2':
                cart.append(['Air Jordan 1 Mid SE', 5300]) #
            elif choice == '3':
                cart.append(['Dunk Low', 3700]) #
            elif option == 'X':
                break
            else :
                print('error , pls try again') #if input another option

def Adidas() :
    while True :
        if option == '2' :
            print('\n{0:-<70}'.format(''))
            print('{0:^70}'.format('-+ Adidas +-'))
            print('\n{0:-<70}'.format(''))
            print('[1] Stan Smith Shoes - 2300 baht') 
            print('[2] Stan Smith CS - 2600 baht') 
            print('[3] Stan Smith 80s - 5500 baht') 
            print('[X] Exit to menu')
            choice = str(input("Select Adidas shoe : ")).upper()
            if choice == '1':
                cart.append(['Stan Smith Shoes', 2300])
            elif choice == '2':
                cart.append(['Stan Smith CS', 2600]) #
            elif choice == '3':
                cart.append(['Stan Smith 80s', 5500]) #
            elif option == 'X':
                break
            else :
                print('error , pls try again') #if input another option       

def Vans() :
    while True :
        if option == '3' :
            print('\n{0:-<70}'.format(''))
            print('{0:^70}'.format('-+ Vans +-'))
            print('\n{0:-<70}'.format(''))
            print('[1] Old Skool Classic - 3200 baht') 
            print('[2] Old Skool Low Pro - 2700 baht') 
            print('[3] Stan Smith 80s - 2790 baht') 
            print('[X] Exit to menu')
            choice = str(input("Select Vans shoe : ")).upper()
            if choice == '1':
                cart.append(['Old Skool Classic', 3200])
            elif choice == '2':
                cart.append(['Old Skool Low Pro', 2700]) #
            elif choice == '3':
                cart.append(['Sk8-Hi', 2790]) #
            elif option == 'X':
                break
            else :
                print('error , pls try again') #if input another option       

def Converse() :
    while True :
        if option == '4' :
            print('\n{0:-<70}'.format(''))
            print('{0:^70}'.format('-+ Converse +-'))
            print('\n{0:-<70}'.format(''))
            print('[1] Chuck Taylor All Star Malden Street - 1680 baht') 
            print('[2] Chuck Taylor All Star Hi - 2300 baht') 
            print('[3] Chuck 70 High De Luxe - 3000 baht') 
            print('[X] Exit to menu')
            choice = str(input("Select Converse shoe : ")).upper()
            if choice == '1':
                cart.append(['Chuck Taylor All Star Malden Street', 1680])
            elif choice == '2':
                cart.append(['Chuck Taylor All Star Hi', 2300]) #
            elif choice == '3':
                cart.append(['Chuck 70 High De Luxe', 3000]) #
            elif option == 'X':
                break
            else :
                print('error , pls try again') #if input another option     

def New_Balance() :
    while True :
        if option == '5' :
            print('\n{0:-<70}'.format(''))
            print('{0:^70}'.format('-+ New Balance +-'))
            print('\n{0:-<70}'.format(''))
            print('[1] Chuck Taylor All Star Malden Street - 1680 baht') 
            print('[2] Chuck Taylor All Star Hi - 2300 baht') 
            print('[3] Chuck 70 High De Luxe - 3000 baht') 
            print('[X] Exit to menu')
            choice = str(input("Select New Balance shoe : ")).upper()
            if choice == '1':
                cart.append(['New Balance 990v5', 8990])
            elif choice == '2':
                cart.append(['New Balance 990v6', 11200]) #
            elif choice == '3':
                cart.append(['New Balance 1500', 10800]) #
            elif option == 'X':
                break
            else :
                print('error , pls try again') #if input another option
     
def cart_list() :
    while True :
        if option == 'S' :
            print('\n{0:-<70}'.format(''))
            print('{0:^70}'.format('-+ Shopping Cart Summary +-'))
            print('\n{0:-<70}'.format(''))
     

while True :
    print('{0:-<70}'.format(''))
    print('{0:^70}'.format('KRUz shoes store')) #use ^ to set the text in the middle
    print('{0:-<70}'.format(''))
    print('{0:^70}'.format('MAIN MENU')) #use ^ to set the text in the middle
    print('{0:>32}\n{1:>34}\n{2:>32}\n{3:>36}\n{4:>39}\n{5:>38}\n{6:>32}'.format('[1] Nike','[2] Adidas','[3] Vans','[4] Converse','[5] New Balance','[S] Show chart','[X] Exit'))
    option = input('\nselect an option : ').upper() #.upper() = change all input to uppercase
    if option == '1' :
        Nike() #function of Nike use while loop in this function
    elif option == '2' :
        Adidas() #function of Adidas use while loop in this function
    elif option == '3' :
        Vans() #function of VAns use while loop in this function
    elif option == '4' :
        Converse() #function of Converse use while loop in this function
    elif option == '5' :
        New_Balance() #function of New_Balance use while loop in this function
    elif option == 'S' :
        cart_list() #function of chart_list show all goods in customer's chart and show the price (receipt)
    elif option == 'X' :
        print('{0:-<70}\n{1:^70}\n{0:-<70}'.format('','-+ Thaks For Your Order +-')) #added thank you customer
        break      
    else :
        print('error , pls try again') #if input another option