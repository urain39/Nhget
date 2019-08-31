from functools import wraps

def retry(errors, max_count=3, callback=None, is_method=False):
  """
  @param errors: any class which based on `Exception`
  @param max_count: optional, the max retry count
  @param callback: optional, be called with `retry count` before retry
  @param is_method: optional, useful when you want to wrap a method
  Examples:
    @retry(ZeroDivisionError, 3,
           lambda cnt, err: print(cnt, err))
    def _():
      0/0
    _()
  """

  # pylint: disable=invalid-name
  def fn_wrapper(fn):
    @wraps(fn)
    def wrapped_fn(*args, **kwargs):
      result = None

      if is_method:
        self = args[0]

      count = 0
      while True:
        try:
          count += 1
          result = fn(*args, **kwargs)
          break
        # pylint: disable=invalid-name
        except errors as err:
          if count <= max_count:
            if callable(callback):
              if is_method:
                callback(self, count, err)
              else:  # function
                callback(count, err)

            continue
          else:
            raise err

      return result
    return wrapped_fn
  return fn_wrapper
