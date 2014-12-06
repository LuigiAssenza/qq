import json

#-----------------------------------------------------------------------------
# Attempt to convert input to int, then float, then str.
#-----------------------------------------------------------------------------

def convert(s):
   try:
      return int(s)
   except ValueError:
      try:
         return float(s)
      except ValueError:
         return str(s)

#-----------------------------------------------------------------------------

def clean_string(d):
   return str(d).strip().replace('"', '')

#-----------------------------------------------------------------------------

class Color(object):
   def __init__(self):
      self.c = None
      with open('colorbrewer_all_schemes.json') as f:
         self.c = json.loads(f.read())

   def get(self, color_type, theme, n):
      assert(color_type in ('Qualitative', 'Sequential', 'Diverging'))
      N = str(max(n,3))
      if N not in self.c[color_type][theme]:
         raise Exception("too many colors: %s" % n)
      colors = self.c[color_type][theme][N]['Colors']
      colors = [ (a[0]/255.0, a[1]/255.0, a[2]/255.0) for a in colors ]
      if n == 1:
         return colors[1:2]
      if n == 2:
         return colors[1:3]
      return colors

#-----------------------------------------------------------------------------
