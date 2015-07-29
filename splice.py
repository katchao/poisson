from PIL import Image, ImageTk
import numpy
from scipy.signal import *
from scipy.sparse import lil_matrix, csr_matrix
import scipy.sparse.linalg
import sys

def splice(source, target, mask, color=True):
    # create mask
    mask = mask.convert('L') # grayscale
    mask = numpy.array(mask)
    mask = mask.astype(numpy.float64)
    mask[mask>0] = 1

    # define sizes
    if not color:
        target = target.convert('L')
        targetw, targeth = target.size

        source = source.convert('L')
        sourcew, sourceh = source.size
    else:
        targetw, targeth = target.split()[0].size;
        sourcew, sourceh = source.split()[0].size;


    # find extent of region
    xNon, yNon = numpy.where(mask==1)
    startX = max([min(xNon) - 1, 0])
    endX = min([max(xNon) + 1, sourceh - 1])
    startY = max([min(yNon) - 1, 0])
    endY = min([max(yNon) + 1, sourcew - 1])
    region_width = endY - startY + 1
    region_height = endX - startX + 1
    half_region_width = region_width//2
    half_region_height = region_height//2


    #define coordinates of destination in target image if difference sizes
    if targeth != sourceh or targetw != sourcew:
        flag = 0
        while flag != 1:
            # GET OFFSET VIA SOME KIND OF INPUT THING HERE
            # currently hardcoded offsets
            offY = 244
            offX = 158

            # print "offx minus: ", offX - half_region_height
            # print "targetx: ", targeth-1
            # print "offx plus: ", offX + half_region_height

            # print "offy minus: ", offY - half_region_width
            # print "targetw: ", targetw-1
            # print "offy plus: ", offY + half_region_width


            if (offX + half_region_height > targeth-1) or (offY + half_region_width > targetw-1) or (offX - half_region_height < 0) or (offY - half_region_width < 0):
                raise ValueError('Destination out of bounds. Choose another location.')
            else:
                flag = 1
                #print "current center: ", numpy.asarray(target)[offX, offY]
                break

        startX_offset = offX - half_region_height
        startY_offset = offY - half_region_width
        endX_offset = offX + half_region_height
        endY_offset = offY + half_region_width

    else: # no offset otherwise
        startX_offset = startX
        startY_offset = startY
        endX_offset = endX
        endY_offset = endY

    # process img
    if not color:
        source = source.convert('L')
        target = target.convert('L')
        result_array = splice_gray(source, target, mask, startX_offset, startY_offset, endX_offset, endY_offset)
        result = Image.fromarray(result_array)
    else:
        source = source.split()
        sr, sg, sb = source[0], source[1], source[2]

        target = target.split()
        tr, tg, tb = target[0], target[1], target[2]
    
        r = splice_gray(sr, tr, mask, startX_offset, startY_offset, endX_offset, endY_offset)
        g = splice_gray(sg, tg, mask, startX_offset, startY_offset, endX_offset, endY_offset)
        b = splice_gray(sb, tb, mask, startX_offset, startY_offset, endX_offset, endY_offset)
        
        rgb = numpy.dstack((r, g, b))
        result = Image.fromarray(rgb)


    result.show()
    return result


def splice_gray(source, target, mask, startX_offset, startY_offset, endX_offset, endY_offset):
    targetw, targeth = target.size
    sourcew, sourceh = source.size

    # convert images to arrays
    target = numpy.array(target)
    source = numpy.array(source)

    # find extent of region
    xNon, yNon = numpy.where(mask==1)
    startX = max([min(xNon) - 1, 0])
    endX = min([max(xNon) + 1, sourceh - 1])
    startY = max([min(yNon) - 1, 0])
    endY = min([max(yNon) + 1, sourcew - 1])
    region_width = endY - startY + 1
    region_height = endX - startX + 1
    half_region_width = region_width//2
    half_region_height = region_height//2

    # find boundaries of mask, mask = 2 for boundaries
    n = xNon.size
    for cy, cx in zip(xNon, yNon):
        if cy-1 >= 0 and mask[cy-1, cx] == 0:
            mask[cy-1, cx] = 2
        if cy+1 < sourceh and mask[cy+1, cx] == 0:
            mask[cy+1, cx] = 2
        if cx-1 >= 0 and mask[cy, cx-1] == 0:
            mask[cy, cx-1] = 2
        if cx+1 < sourcew and mask[cy, cx+1] == 0:
            mask[cy, cx+1] = 2

    # clip to relevant space
    clipped_mask = mask[startX:endX+1, startY:endY+1]
    clipped_target = target[startX_offset-1:endX_offset, startY_offset-1:endY_offset]
    clipped_source = source[startX:endX+1, startY:endY+1]

    # convert to ints
    clipped_mask = clipped_mask.astype(numpy.float64)
    clipped_target = clipped_target.astype(numpy.float64)
    clipped_source = clipped_source.astype(numpy.float64)
    


    laplacian = numpy.array([[0.0, -1.0, 0.0],
                            [-1.0, 4.0, -1.0],
                            [0.0, -1.0, 0.0]])

    # get gradient of source and target
    source_gradient = scipy.signal.convolve2d(clipped_source, laplacian)
    source_gradient = source_gradient[1:region_height+1, 1:region_width+1]

    target_gradient = scipy.signal.convolve2d(clipped_target, laplacian)
    target_gradient = target_gradient[1:region_height+1, 1:region_width+1]

    #initialize A matrix and b matrix
    A = lil_matrix((n, n))
    b = numpy.zeros((n, 1), numpy.float64)

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
                        curb = curb + clipped_target[cx-1, cy]

                if cx+1 < region_height:
                    if clipped_mask[cx+1, cy] == 1:
                        A[index, index+1] = -1
                    elif clipped_mask[cx+1, cy] == 2:
                        curb = curb + clipped_target[cx+1, cy]

                if cy-1 >= 0:
                    if clipped_mask[cx, cy-1] == 1:
                        col = u_dict[(cx, cy-1)]
                        A[index, col] = -1
                    elif clipped_mask[cx, cy-1] == 2:
                        curb = curb + clipped_target[cx, cy-1]

                if cy+1 < region_width:
                    if clipped_mask[cx, cy+1] == 1:
                        col = u_dict[(cx, cy+1)]
                        A[index, col] = -1
                    elif clipped_mask[cx, cy+1] == 2:
                        curb = curb + clipped_target[cx, cy+1]

                A[index, index] = 4

                # compute b matrix
                # version 1: alway add source_gradient
                b[index] = curb + source_gradient[cx, cy]
                """
                cur_source_grad = source_gradient[cx, cy]
                cur_target_grad = target_gradient[cx, cy]
                if abs(cur_source_grad) > abs(cur_target_grad):
                    b[index] = curb + cur_source_grad
                else:
                    b[index] = curb + cur_target_grad
                """
                index = index + 1


    # solve system
    x = scipy.sparse.linalg.spsolve(A.tocsr(), b)
    x[x>255] = 255
    x[x<0] = 0
    x = x.astype(numpy.uint8)
    clipped_target = clipped_target.astype(numpy.uint8)

    # insert into image
    index = 0
    for cy in range(region_width):
        for cx in range(region_height):
            if clipped_mask[cx, cy] == 1:
                clipped_target[cx, cy] = x[index]
                index += 1

    target[startX_offset-1:endX_offset, startY_offset-1:endY_offset] = clipped_target

    return target


def test():
    source = Image.open('niccage.png')
    target = Image.open('apple.png')
    m = Image.open('niccage-mask2.png')
    
    splice(source, target, m, True)
    return

test()
