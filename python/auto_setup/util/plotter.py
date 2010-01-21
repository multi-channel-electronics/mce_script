import pylab as pl
import scipy as sp
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as tkr

class tuningPlot:
    def __init__(self, rows, cols, pages=1, edge_labels=True,
                 title=None):
        self.rows, self.cols = rows, cols
        self.idx = -1
        self.fig = plt.figure(figsize=(8.5,11))
        self.title = title
        self.edge_labels = edge_labels

    def subplot(self, r=None, c=None,
                title=None, xlabel=None, ylabel=None):
        if self.idx < 0 and self.title != None:
            self.fig.text(0.5, 0.95, self.title,
                          ha='center', va='bottom', fontsize=12,
                          family='monospace')
        if r == None and c == None:
            self.idx += 1
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

#adjustments to make sure text is readable
#pl.savefig('plotter2', dpi=250, papertype='letter', orientation='landscape')
#plt.subplots_adjust(wspace=0.25, hspace=-0.5)
#plt.show()
