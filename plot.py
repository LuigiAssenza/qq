'''
Author: Vinhthuy Phan, 2014
'''
import csv
import re
import keyword
import matplotlib.pyplot as plt
import numpy as np

#-----------------------------------------------------------------------------
def is_float(s):
   try:
      v = float(s)
      return True
   except ValueError:
      return False

#-----------------------------------------------------------------------------

def float_or_str(s):
   try:
      return float(s)
   except ValueError:
      return str(s)

#-----------------------------------------------------------------------------

def clean_string(d):
   return str(d).strip().replace('"', '')

#-----------------------------------------------------------------------------
class Column(list):
   def __init__(self):
      self.type = None

   def set_type(self):
      if all(isinstance(v, float) for v in self):
         self.type = 1  # numerical
      else:
         self.type = 2  # categorical


#-----------------------------------------------------------------------------
class Row(dict):
   def __init__(self):
      pass


#-----------------------------------------------------------------------------

#
# iterate through rows, keyed by columns
#
class Data(dict):
   def __init__(self, header, lines):
      self._cur_index_ = -1
      column_names = [ clean_string(s) for s in header ]

      for name in column_names:
         self[name] = Column()
      self._rows_ = []

      for line in lines:
         values = [ clean_string(s) for s in line ]

         if len(column_names) != len(values):
            raise Exception("Inequal number of keys and values:\n%s\n%s\n" % (column_names, values))

         row = Row()
         for i,v in enumerate(values):
            name = column_names[i]
            row[name] = float_or_str(v)
            self[name].append(row[name])
         self._rows_.append(row)

      for name in column_names:
         self[name].set_type()

      self.nrow = len(self._rows_)
      self.ncol = len(self.keys())


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


   # select all pairs (field1, field2) partitioned into key1, key2
   # return a dict of two lists x, y
   def select(self, field1, field2, key1, key2=None):
      if key2 is None:
         all_keys = set(self[key1])
      else:
         all_keys = set((k1,k2) for k1 in set(self[key1]) for k2 in set(self[key2]))

      result = { k : ([], []) for k in all_keys }

      for row in self._rows_:
         key = row[key1] if key2 is None else (row[key1], row[key2])
         if key not in result:
            result[key] = ([], [])
         result[key][0].append(row[field1])
         result[key][1].append(row[field2])
      return result

#-----------------------------------------------------------------------------

class Plot(object):
   def __init__(self, data):
      self.data = data
      self.x = None
      self.y = None
      self.xx = None
      self.yy = None
      self.xy = None

   def __getattribute__(self, var):
      return object.__getattribute__(self, var)

#-----------------------------------------------------------------------------

def read(filename, sep=None, header=None, skip_header=0):
   if sep is None:
      if filename[-4:] == '.csv':
         sep = ','
      elif filename[-4:] == '.tsv':
         sep = '\t'
      else:
         raise Exception("Unknown file type.  Please specify separator.")

   with open(filename, 'rU') as f:
      reader = csv.reader(f)
      rows = []
      for row in reader:
         if skip_header > 0:
            skip_header -= 1
         elif row and row[0] != '#':
            rows.append(row)

   return Plot(Data(header or rows.pop(0), rows))

#-----------------------------------------------------------------------------
# import sys
# print sys.__stdin__.isatty()

if __name__ == '__main__':
   plot = read("datasets/iris.csv")
   print plot.data["Petal.Length"], plot.data.keys()

   print plot.x
   print plot.y
