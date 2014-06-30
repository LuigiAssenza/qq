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
         self.type = "Q"
      else:
         self.type = "C"


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
      self.x = self.y = self.xx = self.yy = self.xy = self.group = self.size = self.shape = None
      self.figure = None
      self.styles = {}
      self.markers_and_labels = None
      self.plot_func = dict(QQ=self.qq_plot, CQ=self.cq_plot, CC=self.cc_plot)

   def __getattribute__(self, name):
      return object.__getattribute__(self, name)

   def compute_range(self, values):
      if values.type == "Q":
         r = min(values), max(values)
         buffer = 0.1 * abs(r[1]-r[0])
         return r[0]-buffer, r[1]+buffer

   def __setattr__(self, name, value):
      if value is not None:
         if name == 'x':
            self.xrange = self.compute_range(self.data[value.name])

         if name == 'y':
            self.yrange = self.compute_range(self.data[value.name])

         if name=='size':
            if not (isinstance(value,int) or isinstance(value,float) or isinstance(value,Var)):
               raise Exception("Size must be a number or a Var() instance.", value)
            if 't' not in value:
               value['t'] = lambda x: x   # default transformation is identity

         if name=='group' and len(set(self.data[value.name])) > len(COLOR):
            raise Exception("Not enough colors (%d) to assign to %d different groups." %
               (len(COLOR), len(set(self.data[value.name]))))

      object.__setattr__(self, name, value)

   def split_data_xx_yy(self):
      if self.xx is None and self.yy is None:
         return 1, 1, { ('','') : self.data._rows_ }

      xx_set = set(self.data[self.xx.name] if self.xx is not None else [''])
      yy_set = set(self.data[self.yy.name] if self.yy is not None else [''])

      result = { (kyy,kxx): [] for kxx in xx_set for kyy in yy_set }
      for row in self.data:
         kxx = row[self.xx.name] if self.xx is not None else ''
         kyy = row[self.yy.name] if self.yy is not None else ''
         result[(kyy,kxx)].append(row)
      return len(yy_set), len(xx_set), result


   def split_rows_by_key(self, key, rows):
      res = {}
      for row in rows:
         if row[key] not in res:
            res[row[key]] = [row]
         else:
            res[row[key]].append(row)
      return res

   def establish_xy_relationship(self, forced=False):
      if self.xy is None or forced:
         xtype = self.data[self.x.name].type if self.x is not None else '_'
         ytype = self.data[self.y.name].type if self.y is not None else '_'
         self.xy = xtype + ytype

   def prepare_legend(self):
      self.legend_adj = [0,0]
      if isinstance(self.group, Var):
         self.legend_adj[0] = 0.0365
         self.legend_labels = sorted(set(self.data[self.group.name]))
         self.color_map = { c:COLOR[i] for i,c in enumerate(self.legend_labels) }
         self.legend_markers = [
            plt.Line2D([],[], marker='o', linewidth=0, mfc=COLOR[i], mec=COLOR[i]) for i in range(len(self.legend_labels))
         ]

   def set_legend(self):
      if isinstance(self.group, Var):
         self.figure.subplots_adjust(right=0.8)
         self.figure.legend(self.legend_markers, self.legend_labels, loc="center right", numpoints=1, bbox_to_anchor=(1, 0.5))


   def split_rows_into_groups(self, rows):
      groups, group_options = [], []

      if isinstance(self.group, Var):
         split_rows = self.split_rows_by_key(self.group.name, rows)
      else:
         split_rows = {None : rows}

      for key, row in split_rows.items():
         options = dict()
         if self.group is not None:
            options.update(color = self.color_map[key])

         if self.size is not None:
            if isinstance(self.size, int) or isinstance(self.size, float):
               options['s'] = self.size
            else:
               options['s'] = [self.size['t'](r[self.size.name]) for r in row]

         options.update(self.styles)
         groups.append(row)
         group_options.append(options)

      return groups, group_options


   def qq_plot(self):
      m, n, rows = self.split_data_xx_yy()
      self.figure, axarr = plt.subplots(m, n, sharex=True, sharey=True, squeeze=False)
      self.prepare_legend()
      for k, grid_id in enumerate(sorted(rows.keys())):
         idx = (k/n, k%n)
         xx_label = '%s = %s'%(self.xx.name,grid_id[1]) if self.xx is not None else ''
         yy_label = '%s = %s'%(self.yy.name,grid_id[0]) if self.yy is not None else ''
         if k<n:
            axarr[idx].text(0.5, 1.03, xx_label, ha='center', va='bottom', rotation=0, transform=axarr[idx].transAxes)
         if (k+1)%n==0:
            axarr[idx].text(1.03, 0.5, yy_label, ha='left', va='center', rotation=270, transform=axarr[idx].transAxes)
         self.figure.subplots_adjust(hspace=0, wspace=0)
         self.figure.text(0.5-self.legend_adj[0], 0.05, self.x.name, ha='center', va='top')
         self.figure.text(0.05, 0.5-self.legend_adj[1], self.y.name, ha='left', va='center', rotation='vertical')

         axarr[idx].set_xlim(*self.xrange)
         axarr[idx].set_ylim(*self.yrange)
         groups, group_options = self.split_rows_into_groups(rows[grid_id])
         for i in range(len(groups)):
            x = [r[self.x.name] for r in groups[i]]
            y = [r[self.y.name] for r in groups[i]]
            axarr[idx].scatter(x,y, **group_options[i])

      self.set_legend()
      plt.show()


   # todo: hbar
   def cq_plot(self):
      m, n, rows = self.split_data_xx_yy()
      self.figure, axarr = plt.subplots(m, n, sharex=True, sharey=True, squeeze=False)
      self.prepare_legend()
      rmin, rmax = 0, 0
      spacing = 0.2
      cvar, qvar = (self.x, self.y)
      # cvar, qvar = (self.x, self.y) if self.data[self.x.name].type == 'C' else (self.y, self.x)

      for k, grid_id in enumerate(sorted(rows.keys())):
         idx = (k/n, k%n)
         xx_label = '%s = %s'%(self.xx.name,grid_id[1]) if self.xx is not None else ''
         yy_label = '%s = %s'%(self.yy.name,grid_id[0]) if self.yy is not None else ''
         if k<n:
            axarr[idx].text(0.5, 1.03, xx_label, ha='center', va='bottom', rotation=0, transform=axarr[idx].transAxes)
         if (k+1)%n==0:
            axarr[idx].text(1.03, 0.5, yy_label, ha='left', va='center', rotation=270, transform=axarr[idx].transAxes)
         self.figure.subplots_adjust(hspace=0, wspace=0)
         self.figure.text(0.5-self.legend_adj[0], 0.05, self.x.name, ha='center', va='top')
         self.figure.text(0.05, 0.5-self.legend_adj[1], self.y.name, ha='left', va='center', rotation='vertical')

         groups, group_options = self.split_rows_into_groups(rows[grid_id])

         bar_width = (1.0 - spacing) /float(len(groups))
         for i,g in enumerate(groups):
            subgroups = self.split_rows_by_key(cvar.name, g)
            index = [ j + i*bar_width for j in range(len(subgroups)) ]
            keys = sorted(subgroups.keys())
            values = [sum(r[qvar.name] for r in subgroups[k]) if k in subgroups else 0 for k in keys]
            axarr[idx].bar(index, values, bar_width, **group_options[i])

         if qvar == self.y:
            rmin, rmax = min(rmin, axarr[idx].get_ybound()[0]), max(rmax, axarr[idx].get_ybound()[1])
         else:
            rmin, rmax = min(rmin, axarr[idx].get_xbound()[0]), max(rmax, axarr[idx].get_xbound()[1])

      labels = sorted(set(self.data[cvar.name]))
      ticks = [ i+(1.0-spacing)*0.5 for i in range(len(labels))]

      for k, key in enumerate(sorted(rows.keys())):
         idx = (k/n, k%n)
         if qvar == self.y:
            axarr[idx].set_ybound(rmin, rmax)
            axarr[idx].set_xticks(ticks)
            axarr[idx].set_xticklabels(labels)
            axarr[idx].set_xbound(0-spacing)
         else:
            axarr[idx].set_xbound(rmin, rmax)
            axarr[idx].set_yticks(ticks)
            axarr[idx].set_yticklabels(labels)
            axarr[idx].set_ybound(0-spacing)

      self.set_legend()
      plt.show()



   def cc_plot(self, ax, rows):
      pass

   def plotCorrelation(self, relation, ax, rows):
      options = {}
      options.update(relation.styles)
      x = [ r[self.x.name] for r in rows ]
      y = [ r[self.y.name] for r in rows ]
      if len(x) > 0 and len(y) > 0:
         slope, const = np.linalg.lstsq(np.vstack([x, np.ones(len(x))]).T, y)[0]
         ax.plot(x, np.array(x)*slope + const, **options)

   def plot(self):
      self.establish_xy_relationship()
      plot_func = self.plot_func.get(self.xy)
      if hasattr(plot_func, '__call__'):
         plot_func()




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

def test_scatter():
   plot = read("data/mpg.csv"); print plot.data.keys()
   plot.x = Var("cty")
   plot.y = Var("hwy")
   plot.xx = Var("cyl")
   plot.yy = Var("drv")
   plot.group = Var("class")
   # plot.size = Var("cyl", t=lambda x: x**3)
   plot.plot()


def test_bar():
   plot = read('data/iris.csv'); print plot.data.keys()
   plot.x = Var('Species')
   plot.y = Var('Petal.Length')
   plot.plot()

def test_bar2():
   plot = read("data/mtcars.csv"); print plot.data.keys()
   plot.x = Var("cyl")
   plot.y = Var("mpg")
   plot.group = Var("gear")
   plot.xy = "CQ"
   plot.plot()

if __name__ == '__main__':
   test_bar()
   # test_scatter()

   '''
   plot.group_by("class", "somedimension_for_shape")
   plot.separate_by("cyl", None)
   '''

