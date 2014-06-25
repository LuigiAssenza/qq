'''
Author: Vinhthuy Phan, 2014
'''
import re
import keyword

#-----------------------------------------------------------------------------
def is_float(s):
   try:
      v = float(s)
      return True
   except ValueError:
      return False

#-----------------------------------------------------------------------------
class Column(list):
   def __init__(self, init_list):
      if any(not is_float(s) for s in init_list):
         self.type = 'categorical'
         self.extend(init_list)
      else:
         self.type = 'numerical'
         self.extend([float(s) for s in init_list if is_float(s)])

   def __getitem__(self, key):
      return super(Column, self).__getitem__(key-1)

   def __setitem__(self, key, item):
      super(Column, self).__setitem__(key-1,item)

#-----------------------------------------------------------------------------
class Row(object):
   def __init__(self, ks, values, sep):
      vs = [ i.strip() for i in values.split(sep) ]
      if len(ks) != len(vs):
         raise Exception("Inequal number of keys and values:\n%s\n%s\n" % (ks, values))

      for i, k in enumerate(ks):
         self.__setattr__(k, vs[i])

#-----------------------------------------------------------------------------

def get_column_names(header, sep, reserved):
   items = [ i.strip() for i in header.split(sep) ]
   for i in items:
      i = i.replace('"',"")
      if i in reserved:
         raise Exception("Invalid column name", i, "is a reserved name.")
      if keyword.iskeyword(i):
         raise Exception("Invalid column name", i, "is a Python keyword.")
      if re.match('[a-zA-Z_][0-9a-zA-Z_]*', i) is None:
         raise Exception("Invalid column name", i, "is an invalid Python identifier.")

   return items


class Data(object):
   def __init__(self, header, lines, sep):
      self._sep_ = sep
      self._column_names_ = []
      self._rows_ = []
      self._cur_index_ = -1
      self._column_names_ = get_column_names(header, sep, dir(self))

      self._rows_ = [ Row(self._column_names_, line, sep) for line in lines ]

      for name in self._column_names_:
         self.__setattr__(name, Column([r.__getattribute__(name) for r in self]))

      for i, r in enumerate(self._rows_):
         for name in self._column_names_:
            if self.__getattribute__(name).type == 'numerical':
               self._rows_[i].__setattr__(name, float(self._rows_[i].__getattribute__(name)))

   def nrow(self):
      return len(self._rows_)

   def ncol(self):
      return len(self._column_names_)

   # Iterate through rows
   def __iter__(self):
      self._cur_index_ = -1
      return self

   def next(self):
      if self._cur_index_ < len(self._rows_)-1:
         self._cur_index_ += 1
         return self._rows_[self._cur_index_]
      else:
         raise StopIteration


#-----------------------------------------------------------------------------
def read(filename, sep='\t', header=None, skip_header=0):
   ''' Default setting assumes the file is tab-delimited '''
   with open(filename, 'rU') as f:
      lines = [ line.strip() for line in f.readlines() ]
      lines = lines[skip_header : ]
      # remove empty lines and comments (lines starting with #) in data
      lines = [ line for line in lines if line and line[0]!='#']

   return Data(header or lines.pop(0).strip(), lines, sep)


#-----------------------------------------------------------------------------
if __name__ == '__main__':
   d = read("datasets/crimeRatesByState2005.csv", ",")
   a=[ (r.state, r.robbery, r.population) for r in d if r.robbery < 100 and r.population > 2000000 ]
   print(a)
   print d.robbery
