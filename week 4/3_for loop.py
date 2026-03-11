#for loop
names01 = ['a','b','c','d'] #create object (list)
for x in names01 : # assign each value to x
    print(x)

names02 = 'python' #create object (string)
for y in names02 :
    print(y)

#range
for x in range(5) :
    print(x)

#range (start,stop,step)
a = list(range(10))
b = list(range(5,11))
c = list(range(0,10,2))
d = list(range(0,-10,-2))
print(a)
print(b)
print(c)
print(d)


#function range
department = ['COMED','SCIED','MATHED']
university = ['KKU','CMU','CU']
for x in department :
    for y in university :
        print(x +' '+ y)

