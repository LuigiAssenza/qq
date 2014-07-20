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

from matplotlib import style, cm
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
class Row(dict):
   def __init__(self):
      pass

#-----------------------------------------------------------------------------
#  0 - categorical (type str)
#  1 - discrete quantitative  (type int)
#  2 - continuous quantitative (type float)
#-----------------------------------------------------------------------------

class Column(list):
   def __init__(self, name, data):
      self.name = name
      self.label = name
      self.data = data
      self._type = 0   # default is type str, categorical

   @property
   def type(self):
      return self._type

   @type.setter
   def type(self, value):
      if isinstance(value, basestring):
         if value == 'categorical':
            self._type = 0
         elif value == 'discrete':
            self._type = 1
         elif value == 'continuous':
            self._type = 2
         else:
            raise Exception('Unknown column type')
      elif value not in (0, 1, 2):
         raise Exception('Unknown column type')
      else:
         self._type = value
      self.data.xy = None   # this is a hack to force default assignment on xy

   def init_type(self):
      if all(isinstance(v, int) for v in self):
         self._type = 1
      elif all((isinstance(v,int) or isinstance(v,float)) for v in self):
         self._type = 2


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

class ColumnProp(object):
   def __init__(self, name):
      self.name = name
      self.v = None

   def __get__(self, instance, owner):
      return self.v

   def __set__(self, instance, value):
      self.v = instance[value] if value is not None else None

#-----------------------------------------------------------------------------

#
# iterate through rows, keyed by columns
#
class Data(dict):
   x = ColumnProp('x')
   y = ColumnProp('y')
   xx = ColumnProp('xx')
   yy = ColumnProp('yy')
   group = ColumnProp('group')
   size = ColumnProp('size')

   def __init__(self, header, lines):
      self._xy = None
      self.styles = { 'bar_spacing' : 0.2 }
      self._cur_index_ = -1
      column_names = [ clean_string(s) for s in header ]

      for name in column_names:
         self[name] = Column(name, self)
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
         self[name].init_type()

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

   @property
   def xy(self):
      return self._xy

   @xy.setter
   def xy(self, value):
      if self.x is None and self.y is None:
         raise Exception("cannot define xy without x and y defined.")

      if self.x is not None and self.y is not None:
         if qq_type(self.x, self.y):
            self._xy = value or 'discrete'
            if self.xy not in ('discrete', 'sequential', 'distribution'):
               raise Exception("Unknown xy type: " + self.xy)
         elif cq_type(self.x, self.y):
            self._xy = value or 'sum'
            if self.xy not in ('sum', 'count', 'average', 'quartiles'):
               raise Exception("Unknown xy type: " + self.xy)
      else:
         self._xy = value or 'count'
         if self.xy not in ('count', 'distribution'):
            raise Exception("Unknown xy type: " + self.xy)

   def set(self, x=None, y=None, group=None, size=None, xx=None, yy=None, xy=None):
      self.x = x
      self.y = y
      self.xx = xx
      self.yy = yy
      self.group = group
      self.size = size
      self.xy = xy

   def plot(self):
      if self.x is None and self.y is None:
         return
      if self.x is None or self.y is None or cq_type(self.x, self.y):
         p = CQPlot(self)
         self.styles['legend_marker'] = 's'
      elif qq_type(self.x, self.y):
         p = QQPlot(self)
         self.styles['legend_marker'] = 'o'
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
      self.markers_and_labels = None

   def get_sequential_colors(self):
      # Linearly interpolate alpha between alpha_min and alpha_max based on quantitative labels
      m, M = min(self.legend_labels), max(self.legend_labels)
      alpha_min, alpha_max = 0.2, 1.0
      alphas = [ alpha_min*(M-v)/(M-m) + alpha_max*(v-m)/(M-m) for v in self.legend_labels ]

      # Combine interpolated alphas with a predefined color (e.g. blue)
      blue = (5/255.0, 112/255.0, 176/255.0)
      return [ (blue[0], blue[1], blue[2], a) for a in alphas ]

   def prepare_legend(self):
      self.legend_colorbar = False
      if self.data.group is not None:
         self.legend_labels = sorted(set(self.data[self.data.group.name]))

         # set color theme
         if self.data.group.type > 0 and qq_type(self.data.x, self.data.y):
            if len(self.legend_labels) < 9:
               colors = self.get_sequential_colors()
            else:
               self.legend_colorbar = True
               self.vmin, self.vmax = min(self.data.group), max(self.data.group)
         else:
            if len(self.legend_labels) > 9:
               raise Exception("Too many colors.")
            colors = color.get('Qualitative', 'Set1', len(self.legend_labels))

         # set legend markers in case there is no color bar
         if not self.legend_colorbar:
            self.color_map = { c:colors[i] for i,c in enumerate(self.legend_labels) }
            self.legend_markers = [
               plt.Line2D([],[], marker=self.data.styles['legend_marker'], linewidth=0, mfc=self.color_map[v], mec=self.color_map[v]) for v in self.legend_labels ]

         # set parameters for position of legend
         self.data.styles.setdefault('legend_position', 'right')
         if self.legend_colorbar:
            self.data.styles.setdefault('legend_space', 0)
         else:
            if self.data.styles['legend_position'] == 'right':
               self.data.styles.setdefault('legend_space', 0.2)
            elif self.data.styles['legend_position'] == 'top':
               self.data.styles.setdefault('legend_space', 0.12)

      else:
         colors = color.get('Qualitative', 'Set1', 1)
         self.color_map = { None : colors[0] }


   def set_legend(self):
      if not self.legend_colorbar:
         if self.data.styles.get('legend_position', None) == 'right':
            self.data.styles.setdefault('legend_cols', 1)
            self.figure.subplots_adjust(right=1-self.data.styles['legend_space'])
            self.figure.legend(self.legend_markers, self.legend_labels, loc="center right", \
               title=self.data.group.label, numpoints=1, bbox_to_anchor=(1, 0.5), ncol=self.data.styles['legend_cols'])
         elif self.data.styles.get('legend_position', None) == 'top':
            self.data.styles.setdefault('legend_cols', len(self.legend_labels))
            self.figure.subplots_adjust(top=1-self.data.styles['legend_space'])
            self.figure.legend(self.legend_markers, self.legend_labels,  loc='upper center', numpoints=1, \
               title=self.data.group.label, bbox_to_anchor=(0.5, 1), ncol=self.data.styles['legend_cols'])

      else:
         if self.data.styles.get('legend_position', None) == 'right':
            self.figure.subplots_adjust(right=1-self.data.styles['legend_space'])
            legend = self.figure.colorbar(self.mappable, ax=self.axarr.ravel().tolist(), aspect=20)
            legend.ax.set_title(self.data.group.label, fontsize='medium')
         else:
            self.figure.subplots_adjust(bottom=self.data.styles['legend_space'])
            legend = self.figure.colorbar(self.mappable, ax=self.axarr.ravel().tolist(), aspect=20, pad=0.12, orientation='horizontal')
            legend.ax.set_xlabel(self.data.group.label, position=(0.5,0), fontsize='medium')


   def update_plot_options(self, groups, options):
      for k, group in groups.items():
         if self.data.size is not None:
            if isinstance(self.data.size, int) or isinstance(self.data.size, float):
               options[k].update(s = self.data.size)
            else:
               t = self.data.size.transform
               options[k].update(s = [r[self.data.size.name] if t is None else t(r[self.data.size.name]) for r in group])

         if self.legend_colorbar:
            c = [r[self.data.group.name] for r in group]
            if c:
               options[k].update(cmap=cm.copper, c=c, vmin=self.vmin, vmax=self.vmax)
         else:
            options[k].update(color = self.color_map[k])

   def set_labels(self):
      if self.data.x is not None:
         xlabel = self.data.x.label
      else:
         xlabel = 'density' if self.data.styles.get('normed',None) else 'count'
      if self.data.y is not None:
         ylabel = self.data.y.label
      else:
         ylabel = 'density' if self.data.styles.get('normed',None) else 'count'

      xmin = min( self.axarr[k/self.n, k%self.n].get_position().xmin for k in range(len(self.rows.keys())) )
      xmax = max( self.axarr[k/self.n, k%self.n].get_position().xmax for k in range(len(self.rows.keys())) )
      ymin = min( self.axarr[k/self.n, k%self.n].get_position().ymin for k in range(len(self.rows.keys())) )
      ymax = max( self.axarr[k/self.n, k%self.n].get_position().ymax for k in range(len(self.rows.keys())) )

      self.figure.text(xmin+(xmax-xmin)*0.5, ymin-0.05, xlabel, ha='center', va='top')
      self.figure.text(0.05, ymin+(ymax-ymin)*0.5, ylabel, ha='left', va='center', rotation='vertical')


   def plot(self):
      data = self.data
      self.m, self.n, self.rows = split_rows_by_2cols(data._rows_, data.xx, data.yy)
      self.figure, self.axarr = plt.subplots(self.m, self.n, sharex=True, sharey=True, squeeze=False)
      self.prepare_legend()
      self.precompute()
      for k, grid_id in enumerate(sorted(self.rows.keys())):
         idx = (k/self.n, k%self.n)
         self.figure.subplots_adjust(hspace=0, wspace=0)
         self.axarr[idx].tick_params(top='off', right='off')
         if data.xx is not None and k<self.n:
            label_spacing = 1.01+0.015*(0.9-0.1)/(self.axarr[idx].get_position().ymax-self.axarr[idx].get_position().ymin)
            xx_label = '%s = %s'%(data.xx.label,grid_id[1]) if data.xx.label else grid_id[1]
            self.axarr[idx].text(0.5, label_spacing, xx_label, ha='center', va='bottom', rotation=0, transform=self.axarr[idx].transAxes)
         if data.yy is not None and (k+1)%self.n==0:
            label_spacing = 1.01+0.015*(0.9-0.125)/ (self.axarr[idx].get_position().xmax-self.axarr[idx].get_position().xmin)
            yy_label = '%s = %s'%(data.yy.label,grid_id[0]) if data.yy.label else grid_id[0]
            self.axarr[idx].text(label_spacing, 0.5, yy_label, ha='left', va='center', rotation=270, transform=self.axarr[idx].transAxes)

         _, groups = split_rows_by_col(self.rows[grid_id], data.group)
         options =  { k : dict(alpha=self.data.styles.get('alpha', None)) for k in groups }
         self.update_plot_options(groups, options)
         self.plot_groups(idx, groups, options)

      self.postcompute()
      self.set_legend()
      self.set_labels()
      plt.show()


   def precompute(self):
      ''' this function is defined at the child level '''
      pass

   def postcompute(self):
      ''' this function is defined at the child level '''
      pass

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

   def plot_groups(self, idx, groups, options):
      for key, g in groups.items():
         x = [r[self.data.x.name] for r in g]
         y = [r[self.data.y.name] for r in g]
         if self.data.xy == 'discrete':
            options[key]['marker'] = 'o'
            if not self.legend_colorbar:
               options[key]['facecolors'] = options[key]['edgecolors'] = [options[key]['color']] * len(x)
               del options[key]['color']
            plot_res = self.axarr[idx].scatter(x,y, **options[key])
            if 'cmap' in options[key]:
               self.mappable = plot_res
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
      self.rmin, self.rmax = 0, 0
      if self.data.x is None or (self.data.y is not None and self.data.y.type == 0):
         self.cvar, self.qvar = self.data.y, self.data.x
      elif self.data.y is None or self.data.x.type == 0:
         self.cvar, self.qvar = self.data.x, self.data.y
      else:
         raise Exception("unsupported")

   def postcompute(self):
      labels = sorted(set(self.cvar))
      for k, key in enumerate(sorted(self.rows)):
         idx = (k/self.n, k%self.n)
         if self.data.xy == 'distribution':
            self.axarr[idx].set_ybound(self.rmin, self.rmax)
         else:
            if self.data.xy == 'quartiles':
               self.data.styles['bar_spacing'] = 0
            ticks = [ i+(1.0-self.data.styles['bar_spacing'])*0.5 for i in range(len(labels))]
            if self.data.y is self.qvar:
               self.axarr[idx].set_ybound(self.rmin, self.rmax)
               self.axarr[idx].set_xticklabels(labels)
               self.axarr[idx].set_xticks(ticks)
               self.axarr[idx].set_xbound(0-self.data.styles['bar_spacing'], len(ticks))
            elif self.data.x is self.qvar:
               self.axarr[idx].set_xbound(self.rmin, self.rmax)
               self.axarr[idx].set_yticklabels(labels)
               self.axarr[idx].set_yticks(ticks)
               self.axarr[idx].set_ybound(0-self.data.styles['bar_spacing'], len(ticks))
            else:
               raise Exception("Unsupported")

   def plot_groups(self, idx, groups, options):
      i = 0
      for key in sorted(groups.keys()):
         g = groups[key]
         if self.data.xy == 'distribution':
            if self.data.x is None:
               raise Exception("Must set x variable to plot distributions.")
            values = [r[self.data.x.name] for r in g]
            options[key]['normed'] = self.data.styles.get('normed',False)
            options[key]['histtype'] = 'stepfilled'
            self.axarr[idx].hist(values, self.data.styles.get('bars',10), **options[key])
         else:
            _, subgroups = split_rows_by_col(g, self.cvar)
            keys = sorted(subgroups.keys())
            values = None
            if self.data.xy == 'quartiles':
               bar_width = 1.0 /float(len(groups)+1)
               values = [ [r[self.qvar.name] for r in subgroups[k]] for k in keys ]
               positions = [ j + (i+1)*bar_width for j in range(len(subgroups)) ]
               if self.data.x is self.cvar:
                  plot_res = self.axarr[idx].boxplot(values, patch_artist=True, positions=positions, widths=.8*bar_width)
               else:
                  plot_res = self.axarr[idx].boxplot(values, vert=False, patch_artist=True, positions=positions, widths=.8*bar_width)
               for box in plot_res['boxes']:
                  box.set(color=options[key]['color'])
               for whisker in plot_res['whiskers']:
                  whisker.set(color='grey')
               for cap in plot_res['caps']:
                  cap.set(color='grey')
               for flier in plot_res['fliers']:
                  flier.set(color='grey', markeredgecolor='grey', marker='+')
               for median in plot_res['medians']:
                  median.set(color='#333333')
            else:
               bar_width = (1.0 - self.data.styles['bar_spacing']) /float(len(groups))
               positions = [ j + i*bar_width for j in range(len(subgroups)) ]
               if self.data.xy == 'count' or self.qvar is None:
                  values = [len(subgroups[k]) if k in subgroups else 0 for k in keys]
               elif self.data.xy == 'sum':
                  values = [sum(r[self.qvar.name] for r in subgroups[k]) if k in subgroups else 0 for k in keys]
               if values is not None:
                  if self.data.x is self.cvar:
                     self.axarr[idx].bar(positions, values, bar_width, **options[key])
                  elif self.data.y is self.cvar:
                     self.axarr[idx].barh(positions, values, bar_width, **options[key])
                  else:
                     raise Exception("Unknown plot")

         i += 1

      if self.data.y is self.qvar:
         self.rmin, self.rmax = min(self.rmin, self.axarr[idx].get_ybound()[0]), max(self.rmax, self.axarr[idx].get_ybound()[1])
      elif self.data.x is self.qvar:
         self.rmin, self.rmax = min(self.rmin, self.axarr[idx].get_xbound()[0]), max(self.rmax, self.axarr[idx].get_xbound()[1])
      else:
         raise Exception("Unsupported")


#-----------------------------------------------------------------------------
