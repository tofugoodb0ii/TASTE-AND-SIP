#tuple

thistuple = ("Com" , "ED" , "KKU") # ไม่สามารถแก้ไขข้อมูลได้
#print(thistuple)

#การเข้าถึงข้อมูลใน tuple
thistuple = ("Com" , "ED" , "KKU") 
#print(thistuple[1])
thistuple = ("Com" , "ED" , "KKU") 
#print(thistuple[-1])
thistuple = ("Com" , "ED" , "KKU") 
#print(thistuple[0:1])

#การเปลี่ยนข้อมูลใน tuple
x = ("Com" , "ED" , "KKU")
y = list(x) # เป็นการเปลี่ยนจาก tuple เป็น list
y[0] = "COmED"
x = tuple(y)
#print(x)
#print(y)

#การลบข้อมูล
x = ("Com" , "ED" , "KKU")
del x 
print(x) # run แล้วจะเกิด error