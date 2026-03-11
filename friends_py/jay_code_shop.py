class store:
    def __init__(self):
        self.product = [("CPU",12000),("GPU",15000),("RAM",5000),("Motherboard",8000),("Storage",3000)]
    def show_product(self):
        n = 1
        print("{0:-<70}".format(""))
        print("{0:^70}".format("Product List"))
        print("{0:-<70}".format(""))
        print("{0:<5}{1:<20}{2:<7}{3:<5}".format("No.","Product Name","Price",""))
        for item in self.product:
            print("{0:<5}{1:<20}{2:<7}{3:<5}".format(n, item[0], item[1], "Baht"))
            n += 1
    def add_product(self):
        print("{0:#<70}".format(""))
        print("{0:^70}".format("Add Product"))
        print("{0:#<70}".format(""))
        while True:
            product_name = input("Enter product name: ")
            product_price = int(input("Enter product price: "))
            self.product.append((product_name, product_price))
            print("Product added successfully!")
            choice = input("Do you want to add more product? (Y/N): ").upper()
            if choice == 'N':
                print("Exiting the add product menu.")
                break
    def remove_product(self):
        print("{0:#<70}".format(""))
        print("{0:^70}".format("Remove Product"))
        print("{0:#<70}".format("\n"))
        product_name = input("Enter product name to remove: ")
        for item in self.product:
            if item[0] == product_name:
                self.product.remove(item)
                print("Product removed successfully!")
                return
        print("Product not found!")
    def menu(self):
        while True:
            print("\n{0:#<70}".format(""))
            print("{0:^70}".format("Welcome to PC Components Store"))  
            print("{0:#<70}".format(""))
            print("{0:<4}{1:<20}".format("[A]","Show Product"))
            print("{0:<4}{1:<20}".format("[S]","Add Product"))
            print("{0:<4}{1:<20}".format("[R]","Remove Product"))
            print("{0:<4}{1:<20}".format("[X]","Exit"))
            choice = input("Select an option : ").upper()
            if choice == 'A':
                self.show_product()
            elif choice == 'S':
                self.add_product()
            elif choice == 'R':
                self.remove_product()
            elif choice == 'X':
                print("Exiting the store. Goodbye!")
                break
my_store = store()
my_store.menu()