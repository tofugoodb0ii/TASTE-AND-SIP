cart = []
def show_item():
    print('\n[1] Inhaler - 39 baht','\n[2] Drinking water - 25 baht','\n[3] Instant noodles - 55 baht','\n[4] Soap - 59 baht','\n[5] Toothbrush - 79 baht')

def add_item():
    while True:
        print('\n[1] Inhaler - 39 baht','\n[2] Drinking water - 25 baht','\n[3] Instant noodles - 55 baht','\n[4] Soap - 59 baht','\n[5] Toothbrush - 79 baht','\n[X] Exit')
        choice = input("\nSelect Item : ").upper()
        if choice == '1':
            item_name, item_price = 'Inhaler', 39
        elif choice == '2':
            item_name, item_price = 'Drinking water', 25
        elif choice == '3':
            item_name, item_price = 'Instant noodles', 55
        elif choice == '4':
            item_name, item_price = 'Soap', 59
        elif choice == '5':
            item_name, item_price = 'Toothbrush', 79
        elif choice == 'X':
            break
        else:
            print('error, please try again!')

        found = False 
        for item in cart :
            if item[0] == item_name :
                item[2] += 1
                found = True
                break
        if not found :
            cart.append([item_name , item_price , 1])

def Show_item_list():
    no , total , total_qty = 1, 0, 0
    print('\n{0:=<74}\n{1:^74}\n{0:=<74}'.format('', 'PP Mi-Ni mart - Receipt')) 
    print('{0:<5}{1:<25}{2:<10}{3:<15}'.format('No.', 'Item', 'Quantity', 'Price'))
    print('{0:=<74}'.format(''))
    for item in cart:
        name, price, qty = item
        total_price = price * qty
        total_qty += qty
        print('{0:<5}{1:<25}{2:^10}{3:<15.2f}'.format(no, name, qty , total_price))
        total += total_price
        no += 1
    print('{0:=<74}'.format(''))
    print('{0:<5}{1:<25}{2:^10}{3:<15.2f}'.format('', 'Total', total_qty, total))
    print('{0:=<74}\n{1:^74}\n{0:=<74}'.format('', '-+ THANK YOU FOR YOUR ORDER +-'))

def remove_item() :
    while True :
        Show_item_list() #use function for show item list
        choice = input("Enter item number to remove (or X to exit) : ").upper()
        if choice.isdigit() and 1 <= int(choice) <= len(cart):
            i = int(choice) - 1
            cart[i][2] -= 1    
            print(f"Removed 1 {cart[i][0]}")
            if cart[i][2] == 0: #index 2 is quantity
                removed = cart.pop(i)
                print(f'remove {removed[0]} from cart')
        elif choice == 'X':
            break
        else:
            print('error , pls try again')

while True :
    print('\n{0:-<74}'.format(''))
    print('{0:^74}'.format('PP Mi-Ni mart'))
    print('{0:-<74}'.format(''))
    print('{0:^74}'.format('MAIN MENU'))
    print('[1] Show Item','\n[2] Add Item','\n[3] Show Item list','\n[4] Remove Item','\n[5] Exit')
    option = input('\nselect an option : ')
    if option == '1':
        show_item()
    elif option == '2':
        add_item()
    elif option == '3':
        Show_item_list()
    elif option == '4':
        remove_item()
    elif option == '5':
        print('{0:-<70}\n{1:^70}\n{2:-<70}'.format('', '-+ Thank You +-',''))
        break
    else:
        print('error, please try again')