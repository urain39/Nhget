from inspect import ismethod
from functools import wraps

def retry(errors, max_count=3, callback=None):
  """
  @param errors: any class which based on `Exception`
  @param max_count: optional, the max retry count
  @param callback: optional, be called with `retry count` before retry

  Examples:
    @retry(ZeroDivisionError, 3,
           lambda cnt, err: print(cnt, err))
    def _():
      0/0

    _()
  """
  # NOTE: This is a bug on CPython closure,
  #       the name of the variable in the sub
  #       function is just a value, so we can
  #       only use it as a pointer(list)...

  # count = 0
  count = [0]
  # pylint: disable=invalid-name
  def fn_wrapper(fn):
    @wraps(fn)
    def wrapped_fn(*args, **kwargs):
      self = None
      result = None
      is_method = False

      if len(args) > 0: # pylint: disable=len-as-condition
        # The applied wrapped_fn
        _fn = getattr(args[0], fn.__name__, None)

        if ismethod(_fn):
          self = args[0]
          is_method = True

      while True:
        try:
          count[0] += 1
          result = fn(*args, **kwargs)
          break
        # pylint: disable=invalid-name
        except errors as err:
          if count[0] <= max_count:
            if callable(callback):
              if is_method:
                callback(self, count[0], err)
              else:  # function
                callback(count[0], err)

            continue
          else:
            raise err

      return result
    return wrapped_fn
  return fn_wrapper
