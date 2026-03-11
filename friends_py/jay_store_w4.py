basket = []
def AMD():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("AMD CPU Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<60}{2:<20}".format("[1]","Ryzen 5 5800X3D","13290 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[2]","Ryzen 7 9800X3D","18890 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[3]","Ryzen 9 9950X3D","27490 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
        choice = input("Select AMD CPU : ").upper()
        if choice == '1':
            basket.append(["Ryzen 5 5800X3D", 13290])
        elif choice == '2':
            basket.append(["Ryzen 7 9800X3D", 18890])
        elif choice == '3':
            basket.append(["Ryzen 9 9950X3D", 27490])
        elif choice == 'X':
            break
def Intel():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("Intel CPU Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<60}{2:<20}".format("[1]","Core i5-14600K","8890  baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[2]","Core i7-14700K","12090 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[3]","Core i9-14900K","17900 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
        choice = input("Select Intel CPU : ").upper()
        if choice == '1':
            basket.append(["Core i5-14600K",8890])
        elif choice == '2':
            basket.append(["Core i7-14700K",12090])
        elif choice == '3':
            basket.append(["Core i9-14900K",17900])
        elif choice == 'X':
            break
def CPU():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("Central Processing Unit Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<20}".format("[1]","AMD"))
        print("{0:<4}{1:<20}".format("[2]","Intel"))
        print("{0:<4}{1:<20}".format("[X]","Exit to menu",""))
        choice = input("Select CPU : ").upper()
        if choice == '1':
            AMD()
        elif choice == '2':
            Intel()
        elif choice == 'X':
                break
def Nvidia():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("Nvidia GPU Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<60}{2:<20}".format("[1]","GeForce RTX 5060 8GB","11900 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[2]","GeForce RTX 5070 12GB","17900 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[3]","GeForce RTX 5080 16GB","33900 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[4]","GeForce RTX 5090 24GB","66900 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
        choice = input("Select Nvidia GPU : ").upper()
        if choice == '1':
            basket.append(["GeForce RTX 5060 8GB", 10900])
        elif choice == '2':
            basket.append(["GeForce RTX 5070 12GB", 17900])
        elif choice == '3':
            basket.append(["GeForce RTX 5080 16GB", 33900])
        elif choice == '4':
            basket.append(["GeForce RTX 5090 24GB", 66900])
        elif choice == 'X':
            break
def AMD_GPU():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("AMD GPU Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<60}{2:<20}".format("[1]","Radeon RX 9060 XT 8GB","11990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[2]","Radeon RX 9060 XT 16GB","14500 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[3]","Radeon RX 9070 16GB","22400 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[4]","Radeon RX 9070 XT 16GB","26900 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
        choice = input("Select AMD GPU : ").upper()
        if choice == '1':
            basket.append(["Radeon RX 9060 XT 8GB", 11990])
        elif choice == '2':
            basket.append(["Radeon RX 9060 XT 16GB", 14500])
        elif choice == '3':
            basket.append(["Radeon RX 9070 16GB", 22400])
        elif choice == '4':
            basket.append(["Radeon RX 9070 XT 16GB", 26900])
        elif choice == 'X':
            break
def GPU():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("Graphics Card Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<20}".format("[1]","AMD"))
        print("{0:<4}{1:<20}".format("[2]","Nvidia"))
        print("{0:<4}{1:<20}".format("[X]","Exit to menu",""))
        choice = input("Select GPU : ").upper()
        if choice == '1':
            AMD_GPU()
        elif choice == '2':
            Nvidia()
        elif choice == 'X':
            break
def AMD_Mainboard():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("AMD Mainboard Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<60}{2:<20}".format("[1]","Gigabyte B650M DS3H","5990  baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[2]","Asus PRIME A620M-A","3990  baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[3]","MSI PRO A620M-E","3490  baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[4]","Gigabyte X670 AORUS ELITE AX","11990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
        choice = input("Select AMD Mainboard : ").upper()
        if choice == '1':
            basket.append(["Gigabyte B650M DS3H", 5990])
        elif choice == '2':
            basket.append(["Asus PRIME A620M-A", 3990])
        elif choice == '3':
            basket.append(["MSI PRO A620M-E", 3490])
        elif choice == '4':
            basket.append(["Gigabyte X670 AORUS ELITE AX", 11990])
        elif choice == 'X':
            break
def Intel_Mainboard():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("Intel Mainboard Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<60}{2:<20}".format("[1]","Asus PRIME B760M-A","4990  baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[2]","Gigabyte H610M","2990  baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[3]","MSI PRO B760M-E","3490  baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[4]","Asus ROG STRIX Z790-E GAMING WIFI","15990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
        choice = input("Select Intel Mainboard : ").upper()
        if choice == '1':
            basket.append(["Asus PRIME B760M-A", 4990])
        elif choice == '2':
            basket.append(["Gigabyte H610M", 2990])
        elif choice == '3':
            basket.append(["MSI PRO B760M-E", 3490])
        elif choice == '4':
            basket.append(["Asus ROG STRIX Z790-E GAMING WIFI", 15990])
        elif choice == 'X':
            break
def Mainboard():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("Mainboard Shoes Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<20}".format("[1]","AMD"))
        print("{0:<4}{1:<20}".format("[2]","Intel"))
        print("{0:<4}{1:<20}".format("[X]","Exit to menu",""))
        choice = input("Select Reebox Shoes : ").upper()
        if choice == '1':
            AMD_Mainboard()
        elif choice == '2':
            Intel_Mainboard()
        elif choice == 'X':
            break
def SSD():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("Storage Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<60}{2:<20}".format("[1]","Samsung 970 EVO Plus 500GB","1990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[2]","Western Digital Blue SN570 1TB","2990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[3]","Crucial P3 Plus 2TB","4990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[4]","Kingston NV2 1TB","2590 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[5]","Seagate FireCuda 530 1TB","5990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
        choice = input("Select Storage : ").upper()
        if choice == '1':
            basket.append(["Samsung 970 EVO Plus 500GB", 1990])
        elif choice == '2':
            basket.append(["Western Digital Blue SN570 1TB", 2990])
        elif choice == '3':
            basket.append(["Crucial P3 Plus 2TB", 4990])
        elif choice == '4':
            basket.append(["Kingston NV2 1TB", 2590])
        elif choice == '5':
            basket.append(["Seagate FireCuda 530 1TB", 5990])
        elif choice == 'X':
            break
def PSU():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("Power Supply Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<60}{2:<20}".format("[1]","Corsair CV550 550W","1990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[2]","Cooler Master MWE 650W","2490 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[3]","Thermaltake Toughpower GF1 750W","3990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[4]","Seasonic FOCUS GX-850 850W","4990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[5]","ASUS ROG Thor 1000W Platinum II","9990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
        choice = input("Select Power Supply : ").upper()
        if choice == '1':
            basket.append(["Corsair CV550 550W", 1990])
        elif choice == '2':
            basket.append(["Cooler Master MWE 650W", 2490])
        elif choice == '3':
            basket.append(["Thermaltake Toughpower GF1 750W", 3990])
        elif choice == '4':
            basket.append(["Seasonic FOCUS GX-850 850W", 4990])
        elif choice == '5':
            basket.append(["ASUS ROG Thor 1000W Platinum II", 9990])
        elif choice == 'X':
            break
def case():
    while True:
        print("\n{0:-<70}".format(""))
        print("{0:^70}".format("Case Models"))
        print("{0:-<70}".format(""))
        print("{0:<4}{1:<60}{2:<20}".format("[1]","Cooler Master MasterBox Q300L","1990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[2]","NZXT H510","2490 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[3]","Fractal Design Meshify C","2990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[4]","Corsair 4000D Airflow","3490 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[5]","Lian Li PC-O11 Dynamic","4990 baht"))
        print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
        choice = input("Select Case : ").upper()
        if choice == '1':
            basket.append(["Cooler Master MasterBox Q300L", 1990])
        elif choice == '2':
            basket.append(["NZXT H510", 2490])
        elif choice == '3':
            basket.append(["Fractal Design Meshify C", 2990])
        elif choice == '4':
            basket.append(["Corsair 4000D Airflow", 3490])
        elif choice == '5':
            basket.append(["Lian Li PC-O11 Dynamic", 4990])
        elif choice == 'X':
            break
def cart():
    print("{0:^70}".format("Computer Hardware Store - Shopping List"))
    print("{0:-<70}".format(""))
    print("{0:<5}{1:<35}{2:<10}{3:<10}{4:<10}".format("No.","Name","Price","Discount","Discount Price"))
    print("{0:-<70}".format(""))
    b = 1
    total = 0
    discount_total = 0
    total_price_discount = 0
    for item in basket:
        name = item[0]
        price = item[1]
        discount = price * 0.2
        price_after_discount = price - discount
        discount_total += discount
        total_price_discount += price_after_discount
        total += price
        print("{0:<5}{1:<35}{2:<10}{3:<10}{4:<10}".format(b, name, price, discount, price_after_discount))
        b += 1
    print("{0:-<70}".format(""))
    print("{0:<5}{1:<35}{2:<10}{3:<10}{4:<10}".format('', 'Total Price', total, discount_total, total_price_discount))
    print("{0:-<70}".format(""))
while True:
    print("{0:-<70}".format(""))
    print("{0:^70}".format("Computer Hardware Store - Main Menu"))
    print("{0:-<70}".format(""))
    print("[1] CPU \n[2] Graphics Card \n[3] Mainboard \n[4] Storage \n[5] Power Supply \n[6] Case \n[S] Show Basket \n[X] Exit")
    choice = input("Select Menu : ").upper()
    if choice == '1':
        CPU()
    elif choice == '2':
        GPU()
    elif choice == '3':
        Mainboard()
    elif choice == '4':
        SSD()
    elif choice == '5':
        PSU()
    elif choice == '6':
        case()
    elif choice == 'S':
        cart()
    elif choice == 'X':
        break