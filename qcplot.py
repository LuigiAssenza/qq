'''
Author: Vinhthuy Phan, 2014
'''
import csv
import re
import keyword
import matplotlib.pyplot as plt
import numpy as np
import math
from utils import *

from matplotlib import style
style.use('ggplot')
color = Color()

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

   return Data(header or rows.pop(0), rows)

#-----------------------------------------------------------------------------
#  0 - categorical (type str)
#  1 - discrete quantitative  (type int)
#  2 - continuous quantitative (type float)
#-----------------------------------------------------------------------------

class Column(list):
   def __init__(self, name=None):
      self.name = name
      self.type = 0   # default is type str, categorical

   def set_type(self):
      if all(isinstance(v, int) for v in self):
         self.type = 1
      elif all((isinstance(v,int) or isinstance(v,float)) for v in self):
         self.type = 2


#-----------------------------------------------------------------------------
#  0 - categorical (type str)
#  1 - discrete quantitative  (type int)
#  2 - continuous quantitative (type float)
#-----------------------------------------------------------------------------

def qq_type(col1, col2):
   if col1 is None or col2 is None:
      return False
   return col1.type * col2.type > 0

def cq_type(col1, col2):
   if col1 is None and col2 is None:
      return False
   if col1 is None or col2 is None:
      return True
   return col1.type * col2.type == 0

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
         self[name] = Column(name)
      self._rows_ = []

      for line in lines:
         values = [ clean_string(s) for s in line ]

         if len(column_names) != len(values):
            raise Exception("Inequal number of keys and values:\n%s\n%s\n" % (column_names, values))

         row = Row()
         for i,v in enumerate(values):
            name = column_names[i]
            row[name] = convert(v)
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

   def check_xy(self, t):
      if t == 'qq':
         if self.xy not in ('discrete', 'sequential'):
            raise Exception("Unknown xy type")
      else:
         if self.xy not in ('count', 'sum', 'average', 'quartiles'):
            raise Exception("Unknown xy type")

   def set(self, x=None, y=None, group=None, size=None, xx=None, yy=None, xy=None):
      self.x = self[x] if x in self else x
      self.y = self[y] if y in self else y
      self.xx = self[xx] if xx in self else xx
      self.yy = self[yy] if yy in self else yy
      self.group = self[group] if group in self else group
      self.size = self[size] if size in self else size

      if self.x is not None and self.y is not None:
         if qq_type(self.x, self.y):
            self.xy = xy or 'discrete'
            self.check_xy('qq')
         elif cq_type(self.x, self.y):
            self.xy = xy or 'sum'
            self.check_xy('cq')
      else:
         self.xy = xy or 'count'
         self.check_xy('cq')


   def plot(self):
      if self.x is None and self.y is None:
         return
      if self.x is None or self.y is None or cq_type(self.x, self.y):
         p = CQPlot(self)
      elif qq_type(self.x, self.y):
         p = QQPlot(self)
      else:
         raise Exception("Not Implemented")
      p.plot()

#-----------------------------------------------------------------------------
# rows : a list of Row instances
# key : a Column instance
#-----------------------------------------------------------------------------
def split_rows_by_col(rows, c):
   if c is None:
      return 1, { None : rows }
   result = { k : [] for k in c }
   for r in rows:
      result[r[c.name]].append(r)
   return len(result), result


#-----------------------------------------------------------------------------
# rows : a list of Row instances
# xx, yy: Column instances
#-----------------------------------------------------------------------------
def split_rows_by_2cols(rows, c1, c2):
   if c1 is None and c2 is None:
      return 1, 1, { ('','') : rows }

   set1 = set(c1 if c1 is not None else [''])
   set2 = set(c2 if c2 is not None else [''])

   result = { (k2,k1): [] for k1 in set1 for k2 in set2 }
   for row in rows:
      k1 = row[c1.name] if c1 is not None else ''
      k2 = row[c2.name] if c2 is not None else ''
      result[(k2,k1)].append(row)
   return len(set2), len(set1), result

#-----------------------------------------------------------------------------

class Plot(object):
   def __init__(self, data):
      self.data = data
      self.figure = None
      self.styles = {}
      self.markers_and_labels = None

   def get_sequential_colors(self):
      # Linearly interpolate alpha between alpha_min and alpha_max based on quantitative labels
      m, M = min(self.legend_labels), max(self.legend_labels)
      alpha_min, alpha_max = 0.3, 1.0
      alphas = [ alpha_min*(M-v)/(M-m) + alpha_max*(v-m)/(M-m) for v in self.legend_labels ]

      # Combine interpolated alphas with a predefined color (e.g. blue)
      blue = (5/255.0, 112/255.0, 176/255.0)
      return [ (blue[0], blue[1], blue[2], a) for a in alphas ]

   def prepare_legend(self):
      self.legend_adj = [0,0]
      if self.data.group is not None:
         self.legend_adj[0] = 0.0365
         self.legend_labels = sorted(set(self.data[self.data.group.name]))

         # set color theme
         if self.data.group.type > 0 and qq_type(self.data.x, self.data.y):
            colors = self.get_sequential_colors()
         else:
            if len(self.legend_labels) > 9:
               raise Exception("Too many colors.")
            colors = color.get('Qualitative', 'Set1', len(self.legend_labels))
         self.color_map = { c:colors[i] for i,c in enumerate(self.legend_labels) }

         self.legend_markers = [
            plt.Line2D([],[], marker='o', linewidth=0, mfc=self.color_map[v], mec=self.color_map[v]) for v in self.legend_labels ]
      else:
         colors = color.get('Qualitative', 'Set1', 1)
         self.color_map = { None : colors[0] }

   def set_legend(self):
      if self.data.group is not None:
         self.figure.subplots_adjust(right=0.8)
         self.figure.legend(self.legend_markers, self.legend_labels, loc="center right", \
            title=self.data.group.name, numpoints=1, bbox_to_anchor=(1, 0.5))


   def update_plot_options(self, groups, options):
      for k, group in groups.items():
         options[k].update(color = self.color_map[k])

         if self.data.size is not None:
            if isinstance(self.data.size, int) or isinstance(self.data.size, float):
               options[k].update('s', self.data.size)
            else:
               options[k].update('s', [r[self.data.size.name] for r in row])

   def plot(self):
      data = self.data
      self.m, self.n, self.rows = split_rows_by_2cols(data._rows_, data.xx, data.yy)
      self.figure, self.axarr = plt.subplots(self.m, self.n, sharex=True, sharey=True, squeeze=False)
      self.prepare_legend()
      self.precompute()
      for k, grid_id in enumerate(sorted(self.rows.keys())):
         idx = (k/self.n, k%self.n)
         xx_label = '%s = %s'%(data.xx.name,grid_id[1]) if data.xx is not None else ''
         yy_label = '%s = %s'%(data.yy.name,grid_id[0]) if data.yy is not None else ''
         if k<self.n:
            self.axarr[idx].text(0.5, 1.05, xx_label, ha='center', va='bottom', rotation=0, transform=self.axarr[idx].transAxes)
         if (k+1)%self.n==0:
            self.axarr[idx].text(1.05, 0.5, yy_label, ha='left', va='center', rotation=270, transform=self.axarr[idx].transAxes)
         self.figure.subplots_adjust(hspace=0, wspace=0)
         if data.x is not None:
            self.figure.text(0.5-self.legend_adj[0], 0.05, data.x.name, ha='center', va='top')
         if data.y is not None:
            self.figure.text(0.04, 0.5-self.legend_adj[1], data.y.name, ha='left', va='center', rotation='vertical')

         _, groups = split_rows_by_col(self.rows[grid_id], data.group)
         options =  { k : {} for k in groups }
         self.update_plot_options(groups, options)
         self.plot_groups(idx, groups, options)

      self.postcompute()
      self.set_legend()
      plt.show()

#-----------------------------------------------------------------------------

class QQPlot(Plot):
   def __init__(self, data):
      super(QQPlot, self).__init__(data)

   def precompute(self):
      def f(values):
         r = min(values), max(values)
         buffer = 0.1 * abs(r[1]-r[0])
         return r[0]-buffer, r[1]+buffer
      self.rangex = f(self.data.x)
      self.rangey = f(self.data.y)

   def postcompute(self):
      pass

   def plot_groups(self, idx, groups, options):
      for key, g in groups.items():
         x = [r[self.data.x.name] for r in g]
         y = [r[self.data.y.name] for r in g]
         options[key]['marker'] = 'o'
         options[key]['color'] = [options[key]['color']] * len(x)
         if self.data.xy == 'discrete':
            self.axarr[idx].scatter(x,y, **options[key])
         elif self.data.xy == 'sequential':
            options[key]['marker'] = None
            self.axarr[idx].plot(x,y, **options[key])

      self.axarr[idx].set_xlim(*self.rangex)
      self.axarr[idx].set_ylim(*self.rangey)

#-----------------------------------------------------------------------------

class CQPlot(Plot):
   def __init__(self, data):
      super(CQPlot, self).__init__(data)

   def precompute(self):
      self.spacing = 0.2
      self.rmin, self.rmax = 0, 0

      if self.data.x is None or (self.data.y is not None and self.data.y.type == 0):
         self.cvar, self.qvar = self.data.y, self.data.x
      elif self.data.y is None or self.data.x.type == 0:
         self.cvar, self.qvar = self.data.x, self.data.y
      else:
         raise Exception("unsupported")

   def postcompute(self):
      labels = sorted(set(self.cvar))
      ticks = [ i+(1.0-self.spacing)*0.5 for i in range(len(labels))]
      for k, key in enumerate(sorted(self.rows)):
         idx = (k/self.n, k%self.n)

         if self.data.y is self.qvar:
            self.axarr[idx].set_ybound(self.rmin, self.rmax)
            self.axarr[idx].set_xticks(ticks)
            self.axarr[idx].set_xticklabels(labels)
            self.axarr[idx].set_xbound(0-self.spacing, len(ticks))
         elif self.data.x is self.qvar:
            self.axarr[idx].set_xbound(self.rmin, self.rmax)
            self.axarr[idx].set_yticks(ticks)
            self.axarr[idx].set_yticklabels(labels)
            self.axarr[idx].set_ybound(0-self.spacing, len(ticks))
         else:
            raise Exception("Unsupported")

   def plot_groups(self, idx, groups, options):
      bar_width = (1.0 - self.spacing) /float(len(groups))
      i = 0
      for key,g in groups.items():
         _, subgroups = split_rows_by_col(g, self.cvar)
         index = [ j + i*bar_width for j in range(len(subgroups)) ]
         keys = sorted(subgroups.keys())
         values = [sum(r[self.qvar.name] if self.qvar is not None else 1 for r in subgroups[k]) if k in subgroups else 0 for k in keys]
         if self.data.x is self.cvar:
            self.axarr[idx].bar(index, values, bar_width, **options[key])
         elif self.data.y is self.cvar:
            self.axarr[idx].barh(index, values, bar_width, **options[key])
         i += 1

      if self.data.y is self.qvar:
         self.rmin, self.rmax = min(self.rmin, self.axarr[idx].get_ybound()[0]), max(self.rmax, self.axarr[idx].get_ybound()[1])
      elif self.data.x is self.qvar:
         self.rmin, self.rmax = min(self.rmin, self.axarr[idx].get_xbound()[0]), max(self.rmax, self.axarr[idx].get_xbound()[1])
      else:
         raise Exception("Unsupported")

#-----------------------------------------------------------------------------
