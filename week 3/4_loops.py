#loops
#while(True) :
    #print("i love you")

#แม่สูตรคูณ
x = int(input("input number : "))
i = 1
while ( i < 13 ) :
    print(str(x) + "x" + str(i) + "=" + str (x*i))
    i += 1

#รับค่า จำนวน n รอบ
x = int(input("input round : ")) #จำนวนรอบ
i = 0
z = 0
sum = 0
while ( i < x ) :
    z = int(input("pls input the number : "))
    sum += z
    i += 1
print("sum of all the number is ",sum )