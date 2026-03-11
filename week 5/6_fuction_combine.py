def combine(pos_only , / , standard , * ,kwd_only) :
    print(pos_only , standard , kwd_only)
#combine(1,2,3)
combine(1,2,kwd_only=3)
combine(1,standard=2,kwd_only=3)

def combine(pos_only , / , standard , * ,kwd_only) :
    print(pos_only , standard , kwd_only)
#combine(1,2,3)
combine('P',8,kwd_only=2005)
combine('P',standard=8,kwd_only=2005)