import os

def a():
    b()
    os.path.join("a", "b")

def b():
    pass

class User:
    def save(self):
        pass

def c(user):
    user.save()
