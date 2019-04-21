from time import sleep
from nhget import Nhget
from random import random
from retry import retry

N = Nhget()

def retry_when(errors):
  return retry(errors, 9999, lambda cnt:
               (
                 sleep(1000 * random()),
                 N.__exit__()  # reset
               )
         )

@retry_when((Exception,))
def main():
  N.run("decensored english", 1, 1)

main()
