from Tkinter import *
from PIL import Image, ImageTk
import numpy
from scipy.sparse import lil_matrix, csr_matrix
import scipy.sparse.linalg

def region_fill(image, mask, color=True):
    # mask = numpy array

    # create mask
    mask = mask.convert('L') # grayscale
    mask = numpy.array(mask)
    mask[mask>0] = 1

    # process image
    if color==False:
        image = image.convert('L')
        result_array = region_fill_gray(image, mask)
        result = Image.fromarray(result_array)
        
    else:
        image = im.split()
        r = region_fill_gray(image[0], mask)
        g = region_fill_gray(image[1], mask)
        b = region_fill_gray(image[2], mask)
        rgb = numpy.dstack((r,g,b))
        result = Image.fromarray(rgb)

    result.show()
    return result


def region_fill_gray(image, mask):
    image_mode = image.mode
    height, width = image.size
    image = numpy.array(image)

    # find extent of region
    xNon, yNon = numpy.where(mask==1)
    startX = max([min(xNon)-1, 0])
    endX = min([max(xNon)+1, height-1])
    startY = max([min(yNon)-1, 0])
    endY = min([max(yNon)+1, width-1])
    region_height = endX - startX + 1 #region_size_X
    region_width = endY - startY + 1 #region_size_Y

    n = xNon.size

    # find boundaries, mask = 2 for boundaries
    for cx, cy in zip(xNon, yNon):
        if cx-1 >= 0 and mask[cx-1, cy] == 0:
            mask[cx-1, cy] = 2
        if cx+1 < height and mask[cx+1, cy] == 0:
            mask[cx+1, cy] = 2
        if cy-1 >= 0 and mask[cx, cy-1] == 0:
            mask[cx, cy-1] = 2
        if cy+1 < width and mask[cx, cy+1] == 0:
            mask[cx, cy+1] = 2

    # clip to relevant space
    clipped_mask = mask[startX:endX+1, startY:endY+1]
    clipped_img = image[startX:endX+1, startY:endY+1]

    # initialize A matrix and b matrix
    A = lil_matrix((n, n))
    b = numpy.zeros((n, 1), numpy.double)

    # build map of unknowns to indices so each unknown has its own unique index
    u_dict = {}
    index = 0
    for cy in range(region_width):
        for cx in range(region_height):
            if clipped_mask[cx, cy] == 1:
                u_dict[(cx, cy)] = index
                index = index+1

    # build A matrix
    index = 0
    for cy in range(region_width):
        for cx in range(region_height):
            if clipped_mask[cx, cy] == 1:
                # check neighbors
                curb = 0
                if cx-1 >= 0:
                    if clipped_mask[cx-1, cy] == 1: # neighbor is in mask
                        A[index, index-1] = -1
                    elif clipped_mask[cx-1, cy] == 2: # neighbor is boundary
                        curb = curb + clipped_img[cx-1, cy]

                if cx+1 < region_height:
                    if clipped_mask[cx+1, cy] == 1:
                        A[index, index+1] = -1
                    elif clipped_mask[cx+1, cy] == 2:
                        curb = curb + clipped_img[cx+1, cy]

                if cy-1 >= 0:
                    if clipped_mask[cx, cy-1] == 1:
                        col = u_dict[(cx, cy-1)]
                        A[index, col] = -1
                    elif clipped_mask[cx, cy-1] == 2:
                        curb = curb + clipped_img[cx, cy-1]

                if cy+1 < region_width:
                    if clipped_mask[cx, cy+1] == 1:
                        col = u_dict[(cx, cy+1)]
                        A[index, col] = -1
                    elif clipped_mask[cx, cy+1] == 2:
                        curb = curb + clipped_img[cx, cy+1]

                A[index, index] = 4
                b[index] = curb
                index = index + 1

    # solve system
    x = scipy.sparse.linalg.spsolve(A.tocsr(), b)
    x = x.astype(numpy.uint8)

    # insert into image
    index = 0
    for cy in range(region_width):
        for cx in range(region_height):
            if clipped_mask[cx, cy] == 1:
                clipped_img[cx, cy] = x[index]
                index += 1

    image[startX: endX+1, startY:endY+1] = clipped_img
    return image
    
                    


#im = numpy.array([[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12], [13, 14, 15, 16, 17, 18], [19, 20, 21, 22, 23, 24], [25, 26, 27, 28, 29, 30], [31, 32, 33, 34, 35, 36]])
#im = Image.fromarray(im)
#m = numpy.array([[0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 0], [0, 0, 1, 1, 1, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]])
im = Image.open('niccage.png')
m = Image.open('mask.png')

region_fill(im, m, False)
