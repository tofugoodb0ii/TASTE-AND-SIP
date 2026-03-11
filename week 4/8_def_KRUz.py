cart = []
def Nike() :
    while True :
        if option == '1' :
            print('\n{0:-<74}\n{1:^74}\n{2:-<74}'.format('','-+ Nike +-',''))
            print('[1] Nike Air Force 1 - 4700 baht \n[2] Nike Air Jordan 1 Mid SE - 5300 baht \n[3] Nike Dunk Low Retro - 3700 baht \n[X] Return to main menu') 
            choice = str(input('Select Nike shoe : ')).upper() #.upper() = change all input to uppercase
            if choice == '1':
                cart.append(['Air Force 1', 4700]) #index [0] is model of shoe , index[1] is a price of shoe
            elif choice == '2':
                cart.append(['Air Jordan 1 Mid SE', 5300]) #append model and price in cart
            elif choice == '3':
                cart.append(['Dunk Low', 3700]) 
            elif choice == 'X':
                break
            else :
                print('error , pls try again') #if input another option

def Adidas() :
    while True :
        if option == '2' :
            print('\n{0:-<74}\n{1:^74}\n{2:-<74}'.format('','-+ Adidas +-',''))
            print('[1] Stan Smith Shoes - 2300 baht \n[2] Stan Smith CS - 2600 baht \n[3] Stan Smith 80s - 5500 baht \n[X] Return to main menu') 
            choice = str(input('Select Adidas shoe : ')).upper() #.upper() = change all input to uppercase
            if choice == '1':
                cart.append(['Stan Smith Shoes', 2300])
            elif choice == '2':
                cart.append(['Stan Smith CS', 2600]) 
            elif choice == '3':
                cart.append(['Stan Smith 80s', 5500]) 
            elif choice == 'X':
                break
            else :
                print('error , pls try again') #if input another option       

def Vans() :
    while True :
        if option == '3' :
            print('\n{0:-<74}\n{1:^74}\n{2:-<74}'.format('','-+ Vans +-',''))
            print('[1] Old Skool Classic - 3200 baht \n[2] Old Skool Low Pro - 2700 baht \n[3] Sk8-Hi - 2790 baht \n[X] Return to main menu') 
            choice = str(input('Select Vans shoe : ')).upper()
            if choice == '1':
                cart.append(['Old Skool Classic', 3200])
            elif choice == '2':
                cart.append(['Old Skool Low Pro', 2700]) #
            elif choice == '3':
                cart.append(['Sk8-Hi', 2790]) #
            elif choice == 'X':
                break
            else :
                print('error , pls try again') #if input another option       

def Converse() :
    while True :
        if option == '4' :
            print('\n{0:-<74}\n{1:^74}\n{2:-<74}'.format('','-+ Converse +-',''))
            print('[1] Chuck Taylor All Star Malden Street - 1680 baht \n[2] Chuck Taylor All Star Hi - 2300 baht \n[3] Chuck 70 High De Luxe - 3000 baht \n[X] Return to main menu') 
            choice = str(input('Select Converse shoe : ')).upper()
            if choice == '1':
                cart.append(['Chuck Taylor All Star Malden Street', 1680])
            elif choice == '2':
                cart.append(['Chuck Taylor All Star Hi', 2300]) #
            elif choice == '3':
                cart.append(['Chuck 70 High De Luxe', 3000]) #
            elif choice == 'X':
                break
            else :
                print('error , pls try again') #if input another option     

def New_Balance() :
    while True :
        if option == '5' :
            print('\n{0:-<74}\n{1:^74}\n{2:-<74}'.format('','-+ New Balance +-',''))
            print('[1] New Balance 990v5 - 8990 baht \n[2] New Balance 990v6 - 11200 baht \n[3] New Balance 1500 - 10800 baht \n[X] Return to main menu') 
            choice = str(input('Select New Balance shoe : ')).upper() #.upper() = change all input to uppercase
            if choice == '1':
                cart.append(['New Balance 990v5', 8990])
            elif choice == '2':
                cart.append(['New Balance 990v6', 11200]) #
            elif choice == '3':
                cart.append(['New Balance 1500', 10800]) #
            elif choice == 'X':
                break
            else :
                print('error , pls try again') #if input another option
     
def cart_list() :
        no = 1
        total_price = 0
        total_discount = 0
        total_discount_price = 0
        print('\n{0:=<74}\n{1:^74}\n{2:=<74}'.format('','KRUz shoes  store - receipt',''))
        print('{0:<5}{1:<35}{2:<10}{3:<10}{4:<10}'.format('No.', 'Model', 'Price', 'Discount', 'Discount Price'))
        print('{0:=<74}'.format('')) #use 74 characters because it’s long enough for discount price (index[4])
        for i in cart:
            model = i[0] #index 0 is model of shoe in cart that appended
            price = i[1] #index 1 is price in cart that appended
            discount = price * 0.20 #discount 20%
            discount_price = price - discount 
            total_price += price #price + price ......
            total_discount += discount #discount + discount ......
            total_discount_price += discount_price #discount_price + discount_price ......
            print('{0:<5}{1:<35}{2:<10.2f}{3:<10.2f}{4:<10.2f}'.format(no, model, price, discount, discount_price))
            no = no + 1
        print('{0:=<74}'.format(''))
        print('{0:<5}{1:<35}{2:<10.2f}{3:<10.2f}{4:<10.2f}'.format('', 'Total', total_price, total_discount, total_discount_price))
        print('{0:=<74}\n{1:^74}\n{2:=<74}'.format('','-+ THANK YOU +-',''))
    
while True :
    print('\n{0:-<74}'.format(''))
    print('{0:^74}'.format('KRUz shoes store')) #use ^ to set the text in the middle
    print('{0:-<74}'.format(''))
    print('{0:^74}'.format('MAIN MENU')) #use ^ to set the text in the middle
    print('{0:>32}\n{1:>34}\n{2:>32}\n{3:>36}\n{4:>39}\n{5:>38}\n{6:>32}'.format('[1] Nike','[2] Adidas','[3] Vans','[4] Converse','[5] New Balance','[S] Show chart','[X] Exit'))
    option = str(input('\nselect an option : ')).upper() #.upper() = change all input to uppercase
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
        print('{0:-<70}\n{1:^70}\n{2:-<70}'.format('','-+ Thaks For Your Order +-','')) #added thank you customer
        break      
    else :
        print('error , pls try again') #if input another option