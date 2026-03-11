basket=[]
def show_products():
    while True:
        print("กรุณาเลือกรายการ")
        print('{0:<5}{1:<15}{2:<10}'.format('[1]','ยาดม','15 บาท' ))
        print('{0:<5}{1:<15}{2:<10}'.format('[2]','น้ำเปล่า','  10 บาท' ))
        print('{0:<5}{1:<15}{2:<10}'.format('[3]','มาม่า',' 20 บาท' ))
        print('{0:<5}{1:<15}{2:<10}'.format('[4]','สบู่','  30 บาท'))
        print('{0:<5}{1:<15}{2:<10}'.format('[5]','แปรงสีฟัน','  60 บาท'))
        print('{0:<5}{1:<15}{2:<10}'.format('[x]','ออกจากฟังก์ชั่น',''))
        x=str(input("เลือกหยิบสินค้าหมายเลข : "))
        x = x.lower()
        if x == "1":    
            basket.append(["ยาดม",1,15])
        elif x == "2":                                      
            basket.append(["น้ำเปล่า",1,10]) 
        elif x == "3":
            basket.append(["มาม่า",1,20])  
        elif x == "4":      
            basket.append(["สบู่",1,30])
        elif x == "5":          
            basket.append(["แปรงสีฟัน",1,60])
        elif x == "x":      
            break
def show_basket():
    print("\n{0:<10}{1:>20}{2:>5}".format("","สินค้าที่คุณได้หยิบมีดังนี้",""))
    print("{0:<10}{1:>10}{2:>10}".format('สินค้า', 'จำนวน', 'ราคา'))
    total = 0
    sumquantity = 0
    for item in basket:
        name = item[0]
        quantity = item[1]
        price = item[2]
        total += price * quantity
        sumquantity += quantity
        print('{0:<10}{1:>10}{2:>10}'.format(name, quantity, price))
    print('{0:-<35}'.format("")) 
    print('{0:<10}{1:>10}{2:>10}'.format("รวม", sumquantity, total))
    print('{0:-<35}'.format("")) 
def Remove_item():
    while True:
        print("\n{0:<10}{1:>20}{2:>5}".format("","สินค้าที่คุณได้หยิบมีดังนี้",""))
        print("{0:<10}{1:>10}{2:>10}".format('สินค้า', 'จำนวน', 'ราคา'))
        total = 0
        sumquantity = 0
        
        for item in basket:
            name = item[0]
            quantity = item[1]
            price = item[2]
            total += price * quantity
            sumquantity += quantity
            print('{0:<10}{1:>10}{2:>10}'.format(name, quantity, price))
        print('{0:-<35}'.format("")) 
        print('{0:<10}{1:>10}{2:>10}'.format("รวม", sumquantity, total))
        print('{0:-<35}'.format("")) 
   
        remove_index = input("กรุณากรอกหมายเลขสินค้าที่ต้องการลบ (เริ่มจาก 1): ")
        print("x เพื่อออกจากการลบสินค้า")  
        if remove_index.lower() == "x":
            break
        if remove_index.isdigit():
            reindex = int(remove_index) - 1
            count = 0
            for i in basket:
                count += 1
            if 0 <= reindex < count:
                del basket[reindex]
                print("ลบสินค้าสำเร็จ")
        else:
            print("กรุณากรอกหมายเลขสินค้าหรือ x เพื่อออก")
while True:
    print("โปรแกรมร้านค้าออนไลน์\n------------------\n[1]แสดงรายการสินค้า\n[2]หยิบสินค้าเข้าตะกร้า\n[3]แสดงจำนวนและสินค้าที่หยิบ\n[4]หยิบสินค้าออกจากตะกร้า\n[5]ปิดโปรแกรม")
    select=str(input("select menu :"))
    if select == "1":
        show_products()
    elif select == "2":
        show_products()
    elif select == "3":
        show_basket()
    elif select == "4":
        Remove_item()
    elif select == "5":
        confirm = input("คุณต้องการออกจากระบบหรือไม่ (y/n) : ")
        if confirm == 'n':
            continue  
        elif confirm == 'y':
            print("ขอบคุณที่ใช้บริการ")
            break