#collection (array)
#thislist

plist = ["thattep" , "tiaksom" , "673050385-7" , "19" , "0954751704" , "mahasarakham"]
#print(plist)

plist = ["thattep" , "tiaksom" , "673050385-7" , "19" , "0954751704" , "mahasarakham"]
#print(plist[3])

plist = ["thattep" , "tiaksom" , "673050385-7" , "19" , "0954751704" , "mahasarakham"]
#print(plist[-2]) # ถ้าเป็นตำแหน่งที่ติดลบ (-) จะเป็นการเรียงตำแหน่งจากด้านหลังโดยตำแหน่งสุดท้ายคือ -1

#range of index
thislist = ["Com" , "Ed" , "KKU" , 99] # ตำแหน่ง 0 , 1 , 2 , 3 , 4 ,......
#print(thislist[1:3]) # เป็นการระบุจุดเริ่มต้นของ index

#change data in list
thislist = ["Com" , "Ed" , "KKU" , 99]
thislist[3] = "MSU"
#print(thislist) 

#add data in list
thislist = ["Com" , "Ed" , "KKU" , 99]
thislist.append("hello , world")
#print(thislist)

#input append
#x = input("pls input your text : ")
thislist = ["Com" , "Ed" , "KKU" , 99]
#thislist.append(x)
#print("this is your new list : " , thislist)

#insert index
#x = input("pls input your text : ")
thislist = ["Com" , "Ed" , "KKU" , 99]
#thislist.insert(1,x) #การเพิ่มข้อมูลในตำแหน่งที่เราระบุ
#print("this is your new list : " , thislist)

#remove data
thislist = ["Com" , "Ed" , "KKU" , 99]
#thislist.remove("Com") #การลบข้อมูลใน list
#print(thislist) 

#pop list
thislist = ["Com" , "Ed" , "KKU" , 99]
#thislist.pop()
#print(thislist) 

#del list
thislist = ["Com" , "Ed" , "KKU" , 99]
#del thislist[2] # เป็นการลบข้อมูลในตำแหน่งที่ 3 
#print(thislist)

#del list
thislist = ["Com" , "Ed" , "KKU" , 99]
#del thislist # เป็นการลบข้อมูลทั้งหมดที่อยู่ใน list
#print(thislist)

#clear list
thislist = ["Com" , "Ed" , "KKU" , 99]
thislist.clear()
print(thislist)