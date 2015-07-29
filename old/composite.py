from Tkinter import *
from PIL import Image, ImageTk
import numpy
from scipy.sparse import lil_matrix, csr_matrix
import scipy.sparse.linalg
from tkFileDialog import askopenfilename

#function to be called when mouse is clicked
def printcoords(event):
    #outputting x and y coords to console
    coords = (event.x, event.y)
    return coords

def composite(source, target, mask, color=True):
    # mask = numpy array

    # create mask
    #mask = mask.convert('L') # grayscale
    mask = numpy.array(mask)
    mask[mask>0] = 1

    # find extent of region
    target_height, target_width = target.convert('L').size
    source_height, source_width = source.convert('L').size
    xNon, yNon = numpy.where(mask==1)
    startX = max([min(xNon)-1, 0])
    endX = min([max(xNon)+1, source_height-1])
    startY = max([min(yNon)-1, 0])
    endY = min([max(yNon)+1, source_width-1])
    region_height = endX - startX + 1 #region_size_X
    region_width = endY - startY + 1 #region_size_Y
    half_region_height = region_height//2
    half_region_width = region_width//2

    # define coordinates of destination in target
    root = Tk()

    #setting up a tkinter canvas with scrollbars
    frame = Frame(root)
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    xscroll = Scrollbar(frame, orient=HORIZONTAL)
    xscroll.grid(row=1, column=0, sticky=E+W)
    yscroll = Scrollbar(frame)
    yscroll.grid(row=0, column=1, sticky=N+S)
    canvas = Canvas(frame, bd=0, xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
    canvas.grid(row=0, column=0, sticky=N+S+E+W)
    xscroll.config(command=canvas.xview)
    yscroll.config(command=canvas.yview)
    frame.pack(fill=BOTH,expand=1)

    #adding the image
    File = askopenfilename(parent=root, initialdir="C:/",title='Choose an image.')
    img = ImageTk.PhotoImage(Image.open(File))
    canvas.create_image(0,0,image=img,anchor="nw")
    canvas.config(scrollregion=canvas.bbox(ALL))

    #mouseclick event
    canvas.bind("<Button 1>",printcoords)
    

    root.mainloop()

    # find boundaries of mask, mask = 2 for boundaries
    for cx, cy in zip(xNon, yNon):
        if cx-1 >= 0 and mask[cx-1, cy] == 0:
            mask[cx-1, cy] = 2
        if cx+1 < source_height and mask[cx+1, cy] == 0:
            mask[cx+1, cy] = 2
        if cy-1 >= 0 and mask[cx, cy-1] == 0:
            mask[cx, cy-1] = 2
        if cy+1 < source_width and mask[cx, cy+1] == 0:
            mask[cx, cy+1] = 2
    print mask


######### MAIN ############
a = numpy.arange(26, 37)
b = numpy.arange(37, 48)
c = numpy.arange(48, 59)
d = numpy.arange(59, 70)
e = numpy.arange(70, 81)
f = numpy.arange(81, 92)
g = numpy.arange(92, 103)
target = numpy.vstack((a, b, c, d, e, f, g))

source = numpy.array([[1, 20, 3, 4, 5], [6, 7, 5, 50, 10], [11, 72, 26, 61, 15], [16, 9, 18, 19, 20], [21, 4, 23, 32, 25]])
mask = numpy.array([[0, 0, 0, 0, 0], [0, 0, 1, 1, 0], [0, 1, 1, 1, 0], [0, 1, 1, 1, 0], [0, 0, 0, 0, 0]])

target = Image.fromarray(target)
source = Image.fromarray(source)
composite(source, target, mask, False)
