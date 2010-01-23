import biggles
# assert biggles.__version__ >= 1.6.4

import pylab as pl
import scipy as sp
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as tkr


class tuningPlotX:
    def __init__(self, rows, cols, pages=0, edge_labels=True,
                 title=None, filename=None):
        self.rows, self.cols = rows, cols
        self.idx = -1
        self.fig = plt.figure(figsize=(8.5,11))
        self.title = title
        self.edge_labels = edge_labels
        self.page_manager = None
        self.page = 0
        if pages > 0:
            self.page_manager = 'multi'
            self.filename = filename

    def subplot(self, r=None, c=None,
                title=None, xlabel=None, ylabel=None):
        if r == None and c == None:
            self.idx = (self.idx + 1) % 8
            if self.idx==0:
                if self.page > 0 and self.page_manager != None:
                    self.save(self.filename % (self.page+1))
                    self.fig.clf()
                self.page += 1
            c, r = self.idx % self.cols, self.idx / self.cols
        else:
            self.idx = c*self.rows + r
        ax = self.fig.add_subplot(self.rows, self.cols, self.idx+1)
        if title != None:
            ax.set_title(title)
        if xlabel != None and (not self.edge_labels or r==self.rows-1):
            ax.set_xlabel(xlabel, size=8)
        if ylabel != None and (not self.edge_labels or c==0):
            ax.set_ylabel(ylabel, size=8)
        self.ax = ax
        return self.ax

    def format(self):
        ax = self.ax
        # Scale the axis of the thing you plotted
        #ax.axis('scaled')
        #ax.axis([0,65, 0,20])

        #Font sizes
        ax.title.set_fontsize(6)
        ax.xaxis.label.set_fontsize(6)
        ax.yaxis.label.set_fontsize(6)

        #Set the tick distribution for x and y
        ax.xaxis.set_major_locator(tkr.MaxNLocator(10))
        ax.xaxis.set_minor_locator(tkr.MaxNLocator(30))
        ax.yaxis.set_major_locator(tkr.MaxNLocator(5))
        ax.yaxis.set_minor_locator(tkr.MaxNLocator(80))

        #Set X tick attributes
        for xticka in ax.xaxis.get_major_ticks():
            xticka.tick2line.set_markersize(4)
            xticka.tick1line.set_markersize(4)
            xticka.label1.set_fontsize(6)
    
        for xticki in ax.xaxis.get_minor_ticks():
            xticki.tick2line.set_markersize(2)
            xticki.tick1line.set_markersize(2)
            
        #Set Y tick attributes
        for yticka in ax.yaxis.get_major_ticks():
            yticka.tick2line.set_markersize(6)
            yticka.tick1line.set_markersize(6)
            yticka.label1.set_fontsize(6)
            
        for yticki in ax.yaxis.get_minor_ticks():
            yticki.tick2line.set_markersize(4)
            yticki.tick1line.set_markersize(3)

    def show(self):
        plt.show()

    def save(self, filename):
        plt.savefig(filename)





class tuningPlotB:
    def __init__(self, rows, cols, pages=0, edge_labels=True,
                 title=None, filename=None):
        self.rows, self.cols = rows, cols
        self.idx = -1
        self.fig = self._newpage(title=title)
        self.edge_labels = edge_labels
        self.page_manager = None
        self.page = 0
        if pages > 0:
            self.page_manager = 'multi'
            self.filename = filename

    def _newpage(self, title=None):
        self.fig = biggles.Table(self.rows, self.cols)
        if title != None:
            self.fig.title = title
        return self.fig

    def subplot(self, r=None, c=None,
                title=None, xlabel=None, ylabel=None):
        #if self.idx < 0 and self.title != None:
        #    self.fig.text(0.5, 0.95, self.title,
        #                  ha='center', va='bottom', fontsize=12,
        #                  family='monospace')
        if r == None and c == None:
            self.idx = (self.idx + 1) % 8
            if self.idx==0:
                if self.page > 0 and self.page_manager != None:
                    self.save(self.filename % (self.page+1))
                    self._newpage()
                self.page += 1
            c, r = self.idx % self.cols, self.idx / self.cols
        ax = biggles.FramedPlot()
        if title != None:
            ax.title = title
        if xlabel != None and (not self.edge_labels or r==self.rows-1):
            ax.xlabel = xlabel
        if ylabel != None and (not self.edge_labels or c==0):
            ax.ylabel = ylabel
        self.fig[r,c]  = ax
        return ax

    def show(self):
        self.plt.show()

    def save(self, filename):
        self.fig.write_img( 400, 600, filename)


tuningPlot = tuningPlotB
