from __future__ import unicode_literals

import os
import re
import sys
import time
from copy import deepcopy
from random import random, randrange
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
from ezreq import EzReq as HttpClient

from .retry import retry


_DOMAIN = "nhentai.net"
_BASE_URL = "https://" + _DOMAIN

_COVER_PATH = "div.container.index-container > .gallery > a.cover"
_THUMB_PATH = "div.container#thumbnail-container > div.thumb-container > a.gallerythumb > img.lazyload[is='lazyload-image']"
_CAPTION_PATH_EN = "div.container#bigcontainer > div#info-block > div#info > h1"
_CAPTION_PATH_JP = "div.container#bigcontainer > div#info-block > div#info > h2"

_THUMB_SUFFIX = "t"
_THUMB_SUBDOMAIN = "t"
_ORIGIN_SUBDOMAIN = "i"

_RE_THUMB_IMAGE_URL = re.compile(r"^(?P<protocol>(?:ht|f)tps?\:)\/\/" + _THUMB_SUBDOMAIN + r"\." + _DOMAIN + r"/galleries/(?P<gallery_id>[0-9]+)/(?P<page_num>[0-9]+)" + _THUMB_SUFFIX + r"\.(?P<file_ext>bmp|gif|jpg|png)$")
_FMT_ORIGIN_IMAGE_URL = r"{protocol}//" + _ORIGIN_SUBDOMAIN + r"." + _DOMAIN + r"/galleries/{gallery_id}/{page_num}.{file_ext}"

_DEFAULT_HEADERS = {
  "User-Agent": "Mozilla/5.0 (Linux; Android 8.1.1; uPackMan P02) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.99 Mobile Safari/537.36"  # + " (I am robot)"
}
_DEFAULT_TIMEOUT = 60
_DEFAULT_BUFSIZE = (1 << 20)  # 1MB
_DEFAULT_TIME_INTERVAL = 5

_TRANSLATE_ESCAPE_DIRNAME = str.maketrans(
  "/:*?<>#=\\",  # NOTE: Do not use `r` prefix here.
  "|.+!()+_|"
)


def retry_when(errors):
  def handler(self, cnt, err):
    time.sleep(_DEFAULT_TIME_INTERVAL * random())
    self.__exit__()  # Reset

  return retry(errors, 0xffff, handler)

def url_generator(elems, attr="href"):
  """
  @param elems: list
  @param attr: str
  @description generator to generate urls of elements
  """
  for elem in elems:
    url = elem.get(attr)

    if url:
      yield url

def yes_or_no(n, cnt):
  return randrange(0, cnt) < n

# Alias constructor of BeautifulSoup with self arguments
# You can modify the default parser to lxml or else here...
def Soup(markup, features="html.parser", **kwargs):  # pylint: disable=invalid-name
  return BeautifulSoup(markup, features, **kwargs)


class Nhget(object):
  def __init__(self):
    self._cwd = os.getcwd()
    self._http = HttpClient(_BASE_URL, headers=deepcopy(_DEFAULT_HEADERS), max_retries=3)

    # Simulate Browser
    self._http.session.get("{0}/favicon.ico".format(_BASE_URL))

  def __enter__(self):
    return self

  def __exit__(self, *args, **kwargs):
    os.chdir(self._cwd)  # Reset.

  def _msg(self, msg):
    sys.stderr.write("=> {0}\n".format(msg))

  def _msg2(self, msg):
    sys.stderr.write("    => {0}\n".format(msg))

  def _query_gallery(self, html):
    """
    @param html: str
    @return gallery_urls: list
    @description query and return gallery urls.
    """
    dom = Soup(html)  # pylint: disable=invalid-name
    covers = dom.select(_COVER_PATH)
    gallery_urls = url_generator(covers, "href")

    return gallery_urls

  def _query_image(self, html):
    """
    @param html: str
    @return gallery_urls: list
    @description query and return thumb urls.
    """
    dom = Soup(html)  # pylint: disable=invalid-name
    thumbs = dom.select(_THUMB_PATH)
    thumb_urls = url_generator(thumbs, "data-src")

    return thumb_urls

  def _wait(self, multiple=1):
    if yes_or_no(2, 9):
      # NOTE: range is indexable
      wait_time = _DEFAULT_TIME_INTERVAL * random()
      wait_time = wait_time * multiple

      self._msg2("sleep %0.2f" % wait_time)
      time.sleep(wait_time)

  @retry_when((RequestException,))
  def _download(self, caption, urls):
    """
    @param urls: list
    @description download the images from thumb_urls
    """
    urls = list(urls)
    page_count = len(urls)
    curr_count = 0  # for display
    session = self._http.session
    caption = caption.translate(_TRANSLATE_ESCAPE_DIRNAME)

    if not os.path.isdir(caption):
      os.mkdir(caption)

    os.chdir(caption)

    is_wait = True
    while len(urls) > 0:
      idx = randrange(0, len(urls))
      url = urls.pop(idx)
      matched = _RE_THUMB_IMAGE_URL.match(url)
      curr_count += 1

      if not matched:
        continue

      dic = matched.groupdict()
      self._msg2("[%4d / %-4d]" % (curr_count, page_count))
      url = _FMT_ORIGIN_IMAGE_URL.format(**dic)

      if is_wait:
        self._wait(multiple=1)

      dic["page_num"] = int(dic["page_num"])
      imgname = "{page_num:06}.{file_ext}".format(**dic)

      if os.path.isfile(imgname):
         self._msg2("skip %s" % imgname)
         is_wait = False
         continue

      is_wait = True
      resp = session.get(url, stream=True, timeout=_DEFAULT_TIMEOUT)
      with open(imgname, "wb") as fp:  # pylint: disable=invalid-name
        for data in resp.iter_content(chunk_size=_DEFAULT_BUFSIZE):
          fp.write(data)

    os.chdir(self._cwd)

  @retry_when((RequestException,))
  def _visit(self, url, **kwargs):
    """
    @param url: str
    @return html: str
    """
    resp = self._http.visit(url, **kwargs)
    return resp.text

  def handle_gallery(self, url):
    """
    @param gallery: tuple
    """
    html = self._visit(url)
    dom = Soup(html)  # pylint: disable=invalid-name
    caption = (dom.select(_CAPTION_PATH_JP) or
               dom.select(_CAPTION_PATH_EN))[0].text
    thumb_urls = self._query_image(html)

    self._msg2("Gallery: %s" % caption)
    self._download(caption, thumb_urls)
    self._wait(multiple=2)

  def _search(self, params):
    """
    @param params: dict
    @return html: str
    """
    self._wait(multiple=1)
    html = self._visit("/search/", params=params)
    return html

  def run(self, keywords, begin, end, order="date"):
    """
    @param keywords: str
    @param begin: int
    @param end: int
    @param order: str date|popular
    @description the main entry of Nhget.
    """
    # pylint: disable=invalid-name
    for p in range(begin, end + 1):
      self._msg("page [%4d]" % p)

      params = {
        "q": keywords,
        "sort": order,
        "page": p
      }
      html = self._search(params)

      for gallery_url in self._query_gallery(html):
        self.handle_gallery(gallery_url)
