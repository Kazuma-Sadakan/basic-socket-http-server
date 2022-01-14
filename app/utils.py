import os 
import bcrypt

BASE_URL  = os.path.dirname(__file__)

def hash_password(password, rounds=13):
    return bcrypt.hashpw(str(password).encode('utf-8'), bcrypt.gensalt(rounds=rounds, prefix=b"2a"))

def check_password(hashed_password, password):
    return bcrypt.checkpw(str(password).encode("utf-8"), hashed_password)

if __name__ == "__main__":
    hashed_password = hash_password(123)
    print(hashed_password)
    print(check_password(hashed_password, 123))

        