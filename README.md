qq.py simplifies plotting.  As it has limited customization, it is appropriate for quick analysis of data.

```
usage: qq.py [-h] [-c] file x [y] [z] [u] [v]

positional arguments:
  file         data file in tab or comma separated format. Must have a header
               with column names.
  x            column representing the x axis.
  y            column representing the y axis.
  z
  u
  v

optional arguments:
  -h, --help   show this help message and exit
  -c, --comma  separator is comma, instead of tab (which is default).
```

Examples:

+ Simple scatter plot, providing x and y variables.

```
    python qq.py data/mpg.csv cty hwy
    python qq.py data/iris.csv Petal.Width Petal.Length
```

+ Scatter plot with three variables: x, y, and z.

```
    python qq.py data/mpg.csv cty hwy cyl
    python qq.py data/mpg.csv cty hwy displ
    python qq.py data/iris.csv Petal.Length Petal.Width Species
    python qq.py data/snp_caller.tsv P-S R-S Alg
```

+ x is categorical and y is quantitative.

```
    python qq.py data/iris.csv Species Petal.Length
```

