def standard_arg(arg) :
    print(arg)
standard_arg(1)

def position_only(* , arg) :
    print(arg)
#position_only(1)
position_only(arg=1)

def keyword_only(*,arg) :
    print(arg)
keyword_only(arg=1)
