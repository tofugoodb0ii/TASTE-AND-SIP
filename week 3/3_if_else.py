x = int(input("pls input your unmber : "))
if x % 3 == 0 :
    print("fizz")
elif x % 5 == 0 :

    print("buzz")
elif x % 15 == 0 :
    print("fizz - buzz")

#การใช้คำสั่งแบบย่อ
me = 19
myFriends = 20
print("i am older than you ") if me > myFriends else print("No!!")

x,y = 19,20
print("older") if x > y else print("equal") if x == y else print("No!!")

#nested if
#x = 24 
x = int(input("pls input your unmber : "))
if x >= 7 :
    if x <= 12 :
        print("elementary school")
    elif x <= 18 :
        print("high school")
    else :
        print("older")
else :
    print("pre school")
