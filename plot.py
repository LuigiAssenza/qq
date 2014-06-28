'''
Author: Vinhthuy Phan, 2014
'''
import csv
import re
import keyword
import matplotlib.pyplot as plt
import numpy as np
import math

COLOR = ['#131313', '#f3c300', '#875692', '#f38400', '#a1caf1', '#be0032', '#c2b280', '#848482', '#008856',
   '#e68fac', '#0067a5', '#f99379', '#604e97', '#f6a600', '#b3446c', '#dcd300', '#882d17', '#27a64c',
   '#654522', '#e25822', '#2b3d26']

# http://colorbrewer2.org/
COLOR = [
   '#8dd3c7',
   '#ffffb3',
   '#bebada',
   '#fb8072',
   '#80b1d3',
   '#fdb462',
   '#b3de69',
   '#fccde5',
   '#d9d9d9',
   '#bc80bd',
   '#ccebc5',
   '#ffed6f'
]

COLOR = [
   '#e41a1c',
   '#377eb8',
   '#4daf4a',
   '#984ea3',
   '#ff7f00',
   '#ffff33',
   '#a65628',
   '#f781bf',
   '#999999',
   '#ccebc5',  # extra
]

COLOR = [
   '#a6cee3',
   '#1f78b4',
   '#b2df8a',
   '#33a02c',
   '#fb9a99',
   '#e31a1c',
   '#fdbf6f',
   '#ff7f00',
   '#cab2d6',
   '#6a3d9a',
   '#ffff99',
   '#b15928',
]
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


   def select(self, xx=None, yy=None):
      if xx is None and yy is None:
         return 0, 0, self._rows_

      xx_set = set(self[xx] if xx is not None else [])
      yy_set = set(self[yy] if yy is not None else [])

      if xx is None:
         result = { k : [] for k in yy_set }
      elif yy is None:
         result = { k : [] for k in xx_set }
      else:
         result = { (k2,k1): [] for k1 in xx_set for k2 in yy_set }

      for row in self._rows_:
         key = row[yy] if xx is None else row[xx] if yy is None else (row[yy],row[xx])
         result[key].append(row)
      return len(yy_set), len(xx_set), result


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
      self.styles = dict(marker='o')
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

class Plot(object):
   def __init__(self, data):
      self.data = data
      self.x = self.y = self.xx = self.yy = self.xy = self.color = self.size = self.shape = None
      self.figure = None
      self.styles = {}
      self.plot_func = dict(Pair=self.plotPair, Correlate=self.plotCorrelation)
      self.markers_and_labels = None

   def __getattribute__(self, name):
      return object.__getattribute__(self, name)

   def __setattr__(self, name, value):
      if value is not None:
         if name == 'x':
            self.xrange = min(self.data[value.name]), max(self.data[value.name])
            inc = abs(self.xrange[1] - self.xrange[0]) * 0.1
            self.xrange = self.xrange[0]-inc, self.xrange[1]+inc

         if name == 'y':
            self.yrange = min(self.data[value.name]), max(self.data[value.name])
            inc = abs(self.yrange[1] - self.yrange[0]) * 0.1
            self.yrange = self.yrange[0]-inc, self.yrange[1]+inc

         if name == 'xy':
            if not (isinstance(value, tuple) or isinstance(value, list)):
               value = (value, )
            for v in value:
               if v.name == "Pair":
                  x = self.data[self.x.name]
                  y = self.data[self.y.name]
                  if x.type!=1 or y.type!=1:
                     raise Exception("%s (type %s) and %s (type %s) must be numerical data" %
                        (self.x.name, x.type, self.y.name, y.type))

         if name=='size' and not (isinstance(value,int) or isinstance(value,float) or isinstance(value,Var)):
            raise Exception("Size must be a number or a Var() instance.", value)

      object.__setattr__(self, name, value)


   def plotPair(self, relation, ax, rows):
      subplots = []
      if isinstance(self.color, Var):
         split_rows = partition(self.color.name, rows)
      else:
         split_rows = {None : rows}

      i = 0
      markers, marker_labels = [], []
      for key, row in split_rows.items():
         options = dict(color = self.color if isinstance(self.color,basestring) else COLOR[i])

         # Keep track of markers and labels for legend
         if self.color is not None:
            markers_options = dict(marker='o', linewidth=0, mfc=COLOR[i], mec=COLOR[i])
            if "alpha" in relation.styles:
               markers_options.update(alpha=relation.styles["alpha"])
            markers.append(plt.Line2D([],[], **markers_options))
            marker_labels.append(key)

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
         i += 1

      [ax.scatter(p['x'], p['y'], **p['options']) for p in subplots]

      if self.color is not None and self.markers_and_labels is None:
         self.markers_and_labels = (markers, marker_labels)


   def plotCorrelation(self, relation, ax, rows):
      options = {}
      options.update(relation.styles)
      x = [ r[self.x.name] for r in rows ]
      y = [ r[self.y.name] for r in rows ]
      if len(x) > 0 and len(y) > 0:
         slope, const = np.linalg.lstsq(np.vstack([x, np.ones(len(x))]).T, y)[0]
         ax.plot(x, np.array(x)*slope + const, **options)


   def plot(self):
      if self.xy is None:
         raise Exception("Must define relationships between x and y variables (xy).")

      xx = self.xx.name if self.xx is not None else None
      yy = self.yy.name if self.yy is not None else None
      m, n, rows = plot.data.select(xx, yy)
      self.figure, axarr = plt.subplots(m or 1, n or 1, sharex=True, sharey=True)

      if not hasattr(axarr, '__iter__'):
         self.plot_axis(axarr, rows)
         axarr.set_xlabel(self.x.name)
         axarr.set_ylabel(self.y.name)
      else:
         for k, key in enumerate(sorted(rows.keys())):
            if isinstance(key, tuple):
               idx = (k/n, k%n)
               xx_label, yy_label = '%s = %s'%(self.xx.name,key[1]), '%s = %s'%(self.yy.name,key[0])
            else:
               idx = k
               xx_label = '%s = %s'%(self.xx.name,key) if self.xx is not None else None
               yy_label = '%s = %s'%(self.yy.name,key) if self.yy is not None else None

            self.plot_axis(axarr[idx], rows[key])
            axarr[idx].set_xlim(*self.xrange)
            axarr[idx].set_ylim(*self.yrange)
            if k<n:
               axarr[idx].text(0.5, 1.03, xx_label, ha='center', va='bottom', rotation=0, transform=axarr[idx].transAxes)
            if n==0 or (m>0 and (k+1)%n==0):
               axarr[idx].text(1.03, 0.5, yy_label, ha='left', va='center', rotation=270, transform=axarr[idx].transAxes)

         self.figure.subplots_adjust(hspace=0, wspace=0)

         # give one label for all subplots sharing same axis
         adj_for_leg = 0 if self.markers_and_labels is None else 0.0365
         self.figure.text(0.5-adj_for_leg,0.05,self.x.name, ha='center', va='top')
         self.figure.text(0.05,0.5,self.y.name, ha='left', va='center', rotation='vertical')

      # plot legend
      if self.markers_and_labels is not None:
         self.figure.subplots_adjust(right=0.8)
         self.figure.legend(*self.markers_and_labels, loc="center right", numpoints=1, bbox_to_anchor=(1, 0.5))

      plt.show()


   def plot_axis(self, ax, rows):
      for relation in self.xy:
         plot_func = self.plot_func.get(relation.name)
         if plot_func is None:
            raise Exception("Unknown relation", relation.name)
         plot_func(relation, ax, rows)

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
   plot = read("datasets/mpg.csv")
   print plot.data.keys()
   plot.x = Var("cty")
   plot.y = Var("hwy")
   plot.xx = Var("cyl")
   plot.yy = Var("drv")
   plot.color = Var("year")
   plot.xy = Pair() #, Correlate(), Categorize()
   plot.plot()
