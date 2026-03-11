basket = []

def show_products():
    while True:
        print("\nกรุณาเลือกรายการ")
        print('[1] ยาดม - 15 บาท')
        print('[2] น้ำเปล่า - 10 บาท')
        print('[3] มาม่า - 20 บาท')
        print('[4] สบู่ - 30 บาท')
        print('[5] แปรงสีฟัน - 60 บาท')
        print('[X] กลับเมนูหลัก')
        x = input("เลือกหยิบสินค้าหมายเลข : ").lower()

        if x == "1":
            basket.append(["ยาดม", 1, 15])
        elif x == "2":
            basket.append(["น้ำเปล่า", 1, 10])
        elif x == "3":
            basket.append(["มาม่า", 1, 20])
        elif x == "4":
            basket.append(["สบู่", 1, 30])
        elif x == "5":
            basket.append(["แปรงสีฟัน", 1, 60])
        elif x == "x":
            break
        else:
            print("กรุณาใส่หมายเลขที่ถูกต้อง")

def show_basket():
    if len(basket) == 0:
        print("\nยังไม่มีสินค้าที่หยิบ")
    else:
        print("\nสินค้าที่คุณหยิบมีดังนี้")
        print("{:<3} {:<15} {:>8} {:>8}".format("No", "สินค้า", "จำนวน", "ราคา"))
        total = 0
        for i in range(len(basket)):
            item = basket[i]
            print("{:<3} {:<15} {:>8} {:>8}".format(i+1, item[0], item[1], item[2]))
            total += item[1] * item[2]
        print("-" * 40)
        print("{:<20} {:>10} {:>8}".format("รวมทั้งหมด", "", total))

def remove_item():
    if len(basket) == 0:
        print("\nยังไม่มีสินค้าในตะกร้า")
        return
    while True:
        print("\nรายการสินค้าในตะกร้า")
        for i in range(len(basket)):
            print(f"[{i+1}] {basket[i][0]} - {basket[i][2]} บาท")
        print("[X] กลับเมนูหลัก")
        choice = input("กรุณาเลือกสินค้าที่ต้องการลบ : ").lower()
        if choice == "x":
            break
        elif choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(basket):
                removed = basket.pop(index)
                print(f"ลบ {removed[0]} ออกจากตะกร้าแล้ว")
            else:
                print("หมายเลขไม่ถูกต้อง")
        else:
            print("กรุณากรอกหมายเลขหรือ x เพื่อกลับ")

# เมนูหลัก
while True:
    print("\nโปรแกรมร้านค้าออนไลน์")
    print("----------------------")
    print("[1] แสดงรายการสินค้า")
    print("[2] หยิบสินค้าเข้าตะกร้า")
    print("[3] แสดงสินค้าที่หยิบ")
    print("[4] ลบสินค้าออกจากตะกร้า")
    print("[5] ออกจากโปรแกรม")
    select = input("เลือกเมนู : ")

    if select == "1":
        show_products()
    elif select == "2":
        show_products()
    elif select == "3":
        show_basket()
    elif select == "4":
        remove_item()
    elif select == "5":
        confirm = input("คุณต้องการออกจากโปรแกรมหรือไม่ (y/n) : ").lower()
        if confirm == "y":
            print("ขอบคุณที่ใช้บริการ")
            break
    else:
        print("กรุณาเลือกเมนูให้ถูกต้อง")
