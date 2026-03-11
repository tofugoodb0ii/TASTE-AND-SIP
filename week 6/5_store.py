class MiniMart:
    def __init__(self):
        self.products = [("Croissant", 59), ("Donut", 19), ("Brownie", 29)]

    def show_products(self):
        print('\n{0:=<100}'.format(''))
        print('{0:^100}'.format(' -+ PP Bakery Product list +- '))
        print('{0:=<100}'.format(''))
        print("{0:<5}{1:<30}{2:>10}{3:>6}".format("No.", "Product Name", "Price", ""))
        print('{0:-<100}'.format(''))
        n = 1
        for item in self.products :
            print("{0:<5}{1:<30}{2:>7}{3:>6}".format(n, item[0], item[1], "Baht"))
            n += 1
        print('{0:=<100}'.format(''))

    def add_products(self):
        print("{0:=<100}".format(""))
        print("{0:^100}".format("-+ Add Product +-"))
        print("{0:=<100}".format(""))
        while True:
            product_name = input("\nEnter product name: ")
            product_price = int(input("Enter product price (THB): "))
            self.products.append((product_name, product_price))
            print("{0:-<100}".format(""))
            print("{0:^100}".format("-+ new product have been added +-"))
            print("{0:-<100}".format(""))
            choice = input("Do you want to add more product? (Y/N): ").upper()
            if choice == 'N':
                print("exit add product menu.")
                break
        print("{0:=<100}".format(""))

    def remove_products(self):
        self.show_products()
        if not self.products:
            return
        choice = int(input("enter product number to remove : "))
        removed = self.products.pop(choice - 1)
        print(f"Removed {removed[0]} {removed[1]} THB - from PP Bakery")

    def menu(self):
        while True :
            print('\n{0:=<100}'.format(''))
            print('{0:^100}'.format(' -+ PP Bakery +- '))
            print('{0:=<100}'.format(''))
            print('{0:^100}'.format('- MAIN MENU -'))
            print("[1] Show Products \n[2] Add Products \n[3] Remove Products \n[4] Exit")
            print('{0:=<100}'.format(''))
            option = input("\nSelect an option : ")
            if option == "1":
                self.show_products()
            elif option == "2":
                self.add_products()
            elif option == "3":
                self.remove_products()
            elif option == "4":
                print("Time to say goodbye!")
                break

shop = MiniMart()
shop.menu()