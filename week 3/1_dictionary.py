thisdict = {
    "fname":"thattep",
    "lname":"tiaksom",
    "year":2005
}
x = thisdict["fname"]
print(x)

#change data
thisdict = {
    "fname":"thattep",
    "lname":"tiaksom",
    "year":2005
}
thisdict["year"] = 2025
print(thisdict)

#add new data
thisdict = {
    "fname":"thattep",
    "lname":"tiaksom",
    "year":2005
}
thisdict["nation"] = "thai" # สร้าง key ใหม่
print(thisdict)

#delete data
thisdict = {
    "fname":"thattep",
    "lname":"tiaksom",
    "year":2005,
    "nation":"thai",
}
thisdict.pop("year") # ลบช้อมูลที่มี key เป็น year
print(thisdict)

thisdict = {
    "fname":"thattep",
    "lname":"tiaksom",
    "year":2005,
    "nation":"thai",
}
thisdict.popitem() # ลบข้อมูลที่เพิ่มล่าสุด
print(thisdict)

thisdict = {
    "fname":"thattep",
    "lname":"tiaksom",
    "year":2005,
    "nation":"thai",
}
del thisdict # ลบข้อมูลที่อยู่ใน dict ทั้งหมด
print(thisdict)