#identity operators

x = ["ComED ", " KKU "] 
y = ["ComED ", " KKU "] 
z = x #ค่า z และ x เป็นค่าเดียวกัน (สืบทอดคุณสมบัติ)

print(x is z)
print(x is y) # มีค่าเหมือนกันแต่เป็นคนละตัวแปร คนละ object
print(x == y) # เปรียบเทียบค่าว่าเท่ากันหรือไม่
