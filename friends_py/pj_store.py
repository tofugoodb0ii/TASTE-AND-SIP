basket = []

while True:
    print("{0:-<70}".format(""))
    print("{0:^70}".format("Computer Hardware Store - Main Menu"))
    print("{0:-<70}".format(""))
    print("[1] CPU \n[2] Graphics Card \n[3] Mainboard \n[4] Storage \n[5] Power Supply \n[S] Show Basket \n[X] Exit")
    choice = input("Select Menu : ").upper()

    if choice == '1':  # CPU menu
        while True:
            print("\n{0:-<70}".format(""))
            print("{0:^70}".format("Central Processing Unit Models"))
            print("{0:-<70}".format(""))
            print("{0:<4}{1:<20}".format("[1]","AMD"))
            print("{0:<4}{1:<20}".format("[2]","Intel"))
            print("{0:<4}{1:<20}".format("[X]","Exit to menu",""))
            cpu_choice = input("Select CPU : ").upper()
            if cpu_choice == '1':  # AMD CPU
                while True:
                    print("\n{0:-<70}".format(""))
                    print("{0:^70}".format("AMD CPU Models"))
                    print("{0:-<70}".format(""))
                    print("{0:<4}{1:<60}{2:<20}".format("[1]","Ryzen 5 5800X3D","13290 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[2]","Ryzen 7 9800X3D","18890 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[3]","Ryzen 9 9950X3D","27490 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
                    amd_choice = input("Select AMD CPU : ").upper()
                    if amd_choice == '1':
                        basket.append(["Ryzen 5 5800X3D", 13290])
                    elif amd_choice == '2':
                        basket.append(["Ryzen 7 9800X3D", 18890])
                    elif amd_choice == '3':
                        basket.append(["Ryzen 9 9950X3D", 27490])
                    elif amd_choice == 'X':
                        break
            elif cpu_choice == '2':  # Intel CPU
                while True:
                    print("\n{0:-<70}".format(""))
                    print("{0:^70}".format("Intel CPU Models"))
                    print("{0:-<70}".format(""))
                    print("{0:<4}{1:<60}{2:<20}".format("[1]","Core i5-14600K","8890  baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[2]","Core i7-14700K","12090 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[3]","Core i9-14900K","17900 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
                    intel_choice = input("Select Intel CPU : ").upper()
                    if intel_choice == '1':
                        basket.append(["Core i5-14600K",8890])
                    elif intel_choice == '2':
                        basket.append(["Core i7-14700K",12090])
                    elif intel_choice == '3':
                        basket.append(["Core i9-14900K",17900])
                    elif intel_choice == 'X':
                        break
            elif cpu_choice == 'X':
                break

    elif choice == '2':  # Graphics Card menu
        while True:
            print("\n{0:-<70}".format(""))
            print("{0:^70}".format("Graphics Card Models"))
            print("{0:-<70}".format(""))
            print("{0:<4}{1:<20}".format("[1]","AMD"))
            print("{0:<4}{1:<20}".format("[2]","Nvidia"))
            print("{0:<4}{1:<20}".format("[X]","Exit to menu",""))
            gpu_choice = input("Select GPU : ").upper()
            if gpu_choice == '1':  # AMD GPU
                while True:
                    print("\n{0:-<70}".format(""))
                    print("{0:^70}".format("AMD GPU Models"))
                    print("{0:-<70}".format(""))
                    print("{0:<4}{1:<60}{2:<20}".format("[1]","Radeon RX 9060 XT 8GB","11990 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[2]","Radeon RX 9060 XT 16GB","14500 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[3]","Radeon RX 9070 16GB","22400 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[4]","Radeon RX 9070 XT 16GB","26900 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
                    amd_gpu_choice = input("Select AMD GPU : ").upper()
                    if amd_gpu_choice == '1':
                        basket.append(["Radeon RX 9060 XT 8GB", 11990])
                    elif amd_gpu_choice == '2':
                        basket.append(["Radeon RX 9060 XT 16GB", 14500])
                    elif amd_gpu_choice == '3':
                        basket.append(["Radeon RX 9070 16GB", 22400])
                    elif amd_gpu_choice == '4':
                        basket.append(["Radeon RX 9070 XT 16GB", 26900])
                    elif amd_gpu_choice == 'X':
                        break
            elif gpu_choice == '2':  # Nvidia GPU
                while True:
                    print("\n{0:-<70}".format(""))
                    print("{0:^70}".format("Nvidia GPU Models"))
                    print("{0:-<70}".format(""))
                    print("{0:<4}{1:<60}{2:<20}".format("[1]","GeForce RTX 5060 8GB","11900 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[2]","GeForce RTX 5070 12GB","17900 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[3]","GeForce RTX 5080 16GB","33900 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[4]","GeForce RTX 5090 24GB","66900 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
                    nvidia_choice = input("Select Nvidia GPU : ").upper()
                    if nvidia_choice == '1':
                        basket.append(["GeForce RTX 5060 8GB", 10900])
                    elif nvidia_choice == '2':
                        basket.append(["GeForce RTX 5070 12GB", 17900])
                    elif nvidia_choice == '3':
                        basket.append(["GeForce RTX 5080 16GB", 33900])
                    elif nvidia_choice == '4':
                        basket.append(["GeForce RTX 5090 24GB", 66900])
                    elif nvidia_choice == 'X':
                        break
            elif gpu_choice == 'X':
                break

    elif choice == '3':  # Mainboard menu
        while True:
            print("\n{0:-<70}".format(""))
            print("{0:^70}".format("Mainboard Shoes Models"))
            print("{0:-<70}".format(""))
            print("{0:<4}{1:<20}".format("[1]","AMD"))
            print("{0:<4}{1:<20}".format("[2]","Intel"))
            print("{0:<4}{1:<20}".format("[X]","Exit to menu",""))
            mb_choice = input("Select Reebox Shoes : ").upper()
            if mb_choice == '1':  # AMD Mainboard
                while True:
                    print("\n{0:-<70}".format(""))
                    print("{0:^70}".format("AMD Mainboard Models"))
                    print("{0:-<70}".format(""))
                    print("{0:<4}{1:<60}{2:<20}".format("[1]","Gigabyte B650M DS3H","5990  baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[2]","Asus PRIME A620M-A","3990  baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[3]","MSI PRO A620M-E","3490  baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[4]","Gigabyte X670 AORUS ELITE AX","11990 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
                    amd_mb_choice = input("Select AMD Mainboard : ").upper()
                    if amd_mb_choice == '1':
                        basket.append(["Gigabyte B650M DS3H", 5990])
                    elif amd_mb_choice == '2':
                        basket.append(["Asus PRIME A620M-A", 3990])
                    elif amd_mb_choice == '3':
                        basket.append(["MSI PRO A620M-E", 3490])
                    elif amd_mb_choice == '4':
                        basket.append(["Gigabyte X670 AORUS ELITE AX", 11990])
                    elif amd_mb_choice == 'X':
                        break
            elif mb_choice == '2':  # Intel Mainboard
                while True:
                    print("\n{0:-<70}".format(""))
                    print("{0:^70}".format("Intel Mainboard Models"))
                    print("{0:-<70}".format(""))
                    print("{0:<4}{1:<60}{2:<20}".format("[1]","Asus PRIME B760M-A","4990  baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[2]","Gigabyte H610M","2990  baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[3]","MSI PRO B760M-E","3490  baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[4]","Asus ROG STRIX Z790-E GAMING WIFI","15990 baht"))
                    print("{0:<4}{1:<60}{2:<20}".format("[X]","Exit to menu",""))
                    intel_mb_choice = input("Select Intel Mainboard : ").upper()
                    if intel_mb_choice == '1':
                        basket.append(["Asus PRIME B760M-A", 4990])
                    elif intel_mb_choice == '2':
                        basket.append(["Gigabyte H610M", 2990])
                    elif intel_mb_choice == '3':
                        basket.append(["MSI PRO B760M-E", 3490])
                    elif intel_mb_choice == '4':
                        basket.append(["Asus ROG STRIX Z790-E GAMING WIFI", 15990])
                    elif intel_mb_choice == 'X':
                        break
            elif mb_choice == 'X':
                break

    elif choice == '4':  # Storage menu
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
            storage_choice = input("Select Storage : ").upper()
            if storage_choice == '1':
                basket.append(["Samsung 970 EVO Plus 500GB", 1990])
            elif storage_choice == '2':
                basket.append(["Western Digital Blue SN570 1TB", 2990])
            elif storage_choice == '3':
                basket.append(["Crucial P3 Plus 2TB", 4990])
            elif storage_choice == '4':
                basket.append(["Kingston NV2 1TB", 2590])
            elif storage_choice == '5':
                basket.append(["Seagate FireCuda 530 1TB", 5990])
            elif storage_choice == 'X':
                break

    elif choice == '5':  # Power Supply menu
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
            psu_choice = input("Select Power Supply : ").upper()
            if psu_choice == '1':
                basket.append(["Corsair CV550 550W", 1990])
            elif psu_choice == '2':
                basket.append(["Cooler Master MWE 650W", 2490])
            elif psu_choice == '3':
                basket.append(["Thermaltake Toughpower GF1 750W", 3990])
            elif psu_choice == '4':
                basket.append(["Seasonic FOCUS GX-850 850W", 4990])
            elif psu_choice == '5':
                basket.append(["ASUS ROG Thor 1000W Platinum II", 9990])
            elif psu_choice == 'X':
                break
        while True:
            print("{0:-<70}".format(""))
            print("{0:^70}".format("Computer Hardware Store - Main Menu"))
            print("{0:-<70}".format(""))
            print("[1] CPU \n[2] Graphics Card \n[3] Mainboard \n[4] Storage \n[5] Power Supply \n[6] Case \n[S] Show Basket \n[X] Exit")
            choice = input("Select Menu : ").upper()

            if choice == 'S':
                # แสดงตะกร้าสินค้า
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
                    print("{0:<5}{1:<35}{2:<10}{3:<10}{4:<10}".format(b, name, price, round(discount,2), round(price_after_discount,2)))
                    b += 1
                print("{0:-<70}".format(""))
                print("{0:<5}{1:<35}{2:<10}{3:<10}{4:<10}".format('', 'Total Price', total, round(discount_total,2), round(total_price_discount,2)))
                print("{0:-<70}".format(""))

            elif choice == 'X':
                print("Thank you for shopping with us!")
                break
