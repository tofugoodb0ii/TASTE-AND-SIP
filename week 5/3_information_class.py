class sutudent() :
    def __init__(self,firstname,surname,year,major,gender) :
        self.firstname = firstname
        self.surname = surname 
        self.year = year
        self.major = major
        self.gender = gender
    def data(self) :
        if gender == 'male' :
            print(f"hello my name is {self.firstname} {self.surname} , I'm a year {self.year} male student , majoring in {self.major}")
        elif gender == 'female' :
             print(f"hello my name is {self.firstname} {self.surname} , I'm a year {self.year} female student , majoring in {self.major}")

print('\n{0:=<100}'.format(''))
print('{0:^100}'.format(' -+ introducing +- '))
print('{0:=<100}'.format(''))
firstname = input('input your firstname : ')
surname = input('input your surname : ')
year = input('input your year : ')
major = input('input your major : ')
gender = input('input your gender : ')

print('\n{0:=<100}'.format(''))
print('{0:^100}'.format(' -+ this is your infromation +- '))
print('{0:=<100}'.format(''))
p = sutudent(firstname,surname,year,major,gender)
p.data()
print('{0:=<100}'.format(''))