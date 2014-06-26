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
# return a dict whose keys from rows are values of a specific input field:

def partition(field, rows):
   res = {}
   for row in rows:
      if field not in row:
         return { field : rows }

      if row[field] not in res:
         res[row[field]] = []
      else:
         res[row[field]].append(row)
   return res


#-----------------------------------------------------------------------------

class Var(dict):
   def __init__(self, name, **kv):
      self.name = name
      super(Var,self).__init__(**kv)

#-----------------------------------------------------------------------------

class Relationship(object):
   def __init__(self, name, **kv):
      self.name = name

class Pair(Relationship):
   def __init__(self, **kv):
      self.styles = {}
      if "alpha" in kv:
         self.styles["alpha"] = kv["alpha"]
      super(Pair, self).__init__("Pair")

class Correlate(Relationship):
   def __init__(self, **kv):
      self.styles = dict(color="#333333")
      if "color" in kv:
         self.styles["color"] = kv["color"]
      super(Correlate, self).__init__("Correlate")

#-----------------------------------------------------------------------------

COLOR = ['b', 'g', 'r']

class Plot(object):
   def __init__(self, data):
      self.data = data
      self.x = self.y = self.xx = self.yy = self.xy = self.color = self.size = self.shape = None
      self.figure = None
      self.styles = {}

   def __getattribute__(self, name):
      return object.__getattribute__(self, name)

   def __setattr__(self, name, value):
      if value is not None:
         if name == 'xy':
            if not (isinstance(value, tuple) or isinstance(value, list)):
               value = (value, )

         if name=='size' and not (isinstance(value,int) or isinstance(value,float) or isinstance(value,Var)):
            raise Exception("Size must be a number or a Var() instance.", value)

      object.__setattr__(self, name, value)


   def plotPair(self, relation, ax):
      subplots = []
      rows = self.data._rows_
      if isinstance(self.color, Var):
         split_rows = partition(self.color.name, rows)
      else:
         split_rows = {None : rows}

      i = 0
      for key, row in split_rows.items():
         options = dict(color = self.color if isinstance(self.color,basestring) else COLOR[i])
         i += 1

         if self.size is not None:
            if isinstance(self.size, int) or isinstance(self.size, float):
               options['s'] = self.size
            else:
               if 't' in self.size:
                  options['s'] = [self.size['t'](r[self.size.name]) for r in row]
               else:
                  options['s'] = [r[self.size.name] for r in row]

         options.update(self.styles)
         options.update(relation.styles)

         subplots.append(dict(
            x = [r[self.x.name] for r in row],
            y = [r[self.y.name] for r in row],
            options = options
         ))

      for subplot in subplots:
         ax.scatter(subplot['x'], subplot['y'], **subplot['options'])


   def plotCorrelation(self, relation, ax):
      subplots = []
      rows = self.data._rows_
      options = {}
      options.update(relation.styles)

      x = [ r[self.x.name] for r in rows ]
      y = [ r[self.y.name] for r in rows ]
      slope, const = np.linalg.lstsq(np.vstack([x, np.ones(len(x))]).T, y)[0]

      ax.plot(x, np.array(x)*slope + const, **options)


   def plot(self):
      plots = dict(Pair=self.plotPair, Correlate=self.plotCorrelation)
      self.figure, ax = plt.subplots()
      for relation in self.xy:
         plot_func = plots.get(relation.name)
         if plot_func is None:
            raise Exception("Unknown relation", relation.name)
         plot_func(relation, ax)
      plt.show()

#---------------------------------------------------------------------------------
# read a delimited file and return a plot referenced to "data" based on this file
#---------------------------------------------------------------------------------

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
         elif row and row[0][0] != '#':
            rows.append(row)

   return Plot(Data(header or rows.pop(0), rows))

#---------------------------------------------------------------------------------
# import sys
# print sys.__stdin__.isatty()

if __name__ == '__main__':
   plot = read("datasets/iris.csv")
   plot.x = Var("Petal.Length")
   plot.y = Var("Petal.Width")
   plot.color = Var("Species")
   plot.xy = Pair(), Correlate()
   plot.plot()

   # plot.size = Var("Sepal.Width", t=lambda x: 10*x*x*x)
   # plot.xy = Pair(alpha=0.4), Correlate()
