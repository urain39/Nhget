import os
import re
import sys
import time
from copy import deepcopy
from os import path
from ezreq import EzReq
from pyquery import PyQuery as pq
from random import randint, random

_DOMAIN = "nhentai.net"
_BASE_URL = "https://" + _DOMAIN

_COVER_PATH = "div.container.index-container > .gallery > a.cover"
_THUMB_PATH = "div.container#thumbnail-container > div.thumb-container > a.gallerythumb > img.lazyload[is='lazyload-image']"
_CAPTION_RELATIVE_PATH = "div.caption"

_THUMB_SUFFIX = "t"
_THUMB_SUBDOMAIN = "t"
_ORIGIN_SUBDOMAIN = "i"

_RE_THUMB_IMAGE_URL = re.compile(r"^(?P<protocol>(?:ht|f)tps?\:)\/\/" + _THUMB_SUBDOMAIN + r"\." + _DOMAIN + r"/galleries/(?P<gallery_id>[0-9]+)/(?P<image_num>[0-9]+)" + _THUMB_SUFFIX + r"\.(?P<file_ext>bmp|gif|jpg|png)$")
_FMT_ORIGIN_IMAGE_URL = r"{protocol}//" + _ORIGIN_SUBDOMAIN + r"." + _DOMAIN + r"/galleries/{gallery_id}/{image_num}.{file_ext}"

_DEFAULT_HEADERS = {
  "User-Agent": "Mozilla/5.0 (Linux; Android 7.1.2; EZ01) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.99 Mobile Safari/537.36"
}
_DEFAULT_BUFSIZE = (1 << 20)  # 1MB
_DEFAULT_TIME_INTERVAL = (1, 5)

def generate_urls(elems, attr="href"):
  """
  @param elems: list
  @param attr: str
  @description generator to generate urls of elements
  """
  for elem in elems:
    if getattr(elem, "attrib", None):
      url = elem.attrib.get(attr)

      if url:
        yield url


class Nhget(object):
  def __init__(self):
    self._cwd = os.getcwd()
    self._http = EzReq(_BASE_URL, headers=deepcopy(_DEFAULT_HEADERS))

  def _msg(self, msg):
    sys.stderr.write("=> {0}\n".format(msg))

  def _msg2(self, msg):
    sys.stderr.write("    => {0}\n".format(msg))

  def _query_gallery(self, html):
    """
    @param html: str
    @return gallery_list: list
    @description query and return gallery urls.
    """
    dq = pq(html)
    covers = dq(_COVER_PATH)
    captions = [
      caption.text
      for cover in covers
        for caption in pq(cover)(_CAPTION_RELATIVE_PATH)
    ]

    gallery_urls = generate_urls(covers, "href")
    gallery_list = zip(captions, gallery_urls)

    return gallery_list

  def _query_image(self, html):
    """
    @param html: str
    @return gallery_urls: list
    @description query and return thumb urls.
    """
    dq = pq(html)
    thumbs = dq(_THUMB_PATH)
    thumb_urls = generate_urls(thumbs, "data-src")

    return thumb_urls

  def _delay_multiple(self, multi=1):
    delay = randint(*_DEFAULT_TIME_INTERVAL) + random()
    delay = delay * multi
    self._msg2("sleep %0.2f" % delay)
    time.sleep(delay)

  def _download(self, caption, urls):
    """
    @param urls: list
    @description download the images from thumb_urls
    """
    url_num = 0
    urls = list(urls)
    url_count = len(urls)
    session = self._http.session

    if not path.isdir(caption):
      caption = caption.replace("/", "|")\
                       .replace(':', '.')\
                       .replace('*', '+')\
                       .replace('?', '!')\
                       .replace('<', '(')\
                       .replace('>', ')')\
                       .replace("\\", "|")
      os.mkdir(caption)

    os.chdir(caption)

    for url in urls:
      url_num += 1
      self._msg2("[%4d / %-4d]" % (url_num, url_count))

      matched = _RE_THUMB_IMAGE_URL.match(url)

      if not matched:
        continue

      dic = matched.groupdict()
      url = _FMT_ORIGIN_IMAGE_URL.format(**dic)

      self._delay_multiple(1)
      resp = session.get(url, stream=True)
      dic["image_num"] = int(dic["image_num"])
      imgname = "{image_num:06}.{file_ext}".format(**dic)

      with open(imgname, "wb") as fp:
        for data in resp.iter_content(chunk_size=_DEFAULT_BUFSIZE):
          fp.write(data)

    os.chdir(self._cwd)

  def _visit(self, url, **kwargs):
    """
    @params url: str
    @return html: str
    """
    resp = self._http.get(url, **kwargs)
    return resp.text

  def _process(self, gallery):
    """
    @param gallery: tuple
    """
    caption, url = gallery
    html = self._visit(url)
    thumb_urls = self._query_image(html)

    self._msg2("Gallery: %s" % caption)
    self._download(caption, thumb_urls)
    self._delay_multiple(100)

  def _search(self, params):
    """
    @param params: object
    @return html: str
    """
    self._delay_multiple(1)
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
    for p in range(begin, end + 1):
      self._msg("page [%4d]" % p)

      params = {
        "q": keywords,
        "sort": order,
        "page": p
      }
      html = self._search(params)

      for gallery in self._query_gallery(html):
        self._process(gallery)
