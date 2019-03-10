import re
import sys
from time import sleep
from queue import Queue
from threading import Thread
from nhget import Nhget


_ALIAS_EOF = r''
_ALIAS_FINISHED = "\xe2\x95"
_TIME_INTERVAL = 0.5
_RE_GALLERY_URL = re.compile(r"/g/[0-9]{1,}")

def do_task(queue):
  N = Nhget()

  while True:
    if not queue.empty():
      gallery_url = queue.get()

      if gallery_url == _ALIAS_FINISHED:
        break

      N.handle_gallery(gallery_url)
    sleep(_TIME_INTERVAL)

def prompt():
  return sys.stdin.readline().strip()

def main():
  taskQueue = Queue()
  gallery_url = prompt()

  Thread(target=do_task, args=(taskQueue,)).start()

  while gallery_url is not _ALIAS_EOF:
    if _RE_GALLERY_URL.match(gallery_url):
      taskQueue.put(gallery_url)

    gallery_url = prompt()

  # Notify the `do_task` we are finished.
  taskQueue.put(_ALIAS_FINISHED)

if __name__ == "__main__":
  main()
