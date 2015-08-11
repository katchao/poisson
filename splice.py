from PIL import Image, ImageTk
import numpy
from scipy.signal import *
from scipy.sparse import lil_matrix, csr_matrix
import scipy.sparse.linalg
import sys


"""
Params:
    mask: PIL image (rgb)
Returns:
    mask: logical matrix
"""
def create_mask_from_image(mask):
    mask = mask.convert('L') # grayscale
    mask = numpy.array(mask)
    mask = mask.astype(numpy.float64)
    mask[mask>0] = 1 # turn non-white into 1

    return mask



"""
Params:
    source: PIL image (rgb)
    target: PIL image (rgb)
    mask: logical matrix
Returns:
    result: dictionary of all necessary boundary information
"""
def get_size_info(source, target, mask):
    # get target and source heights and widths
    targetw, targeth = target.split()[0].size
    sourcew, sourceh = source.split()[0].size

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

    return {"targetw": targetw,
            "targeth": targeth,
            "sourcew": sourcew,
            "sourceh": sourceh,
            "startX": startX, 
            "endX": endX,
            "startY": startY,
            "endY": endY,
            "xNon": xNon,
            "yNon": yNon,
            "region_width": region_width,
            "region_height": region_height,
            "half_region_width": half_region_width,
            "half_region_height": half_region_height }


"""
Params:
    source: PIL image (rgb)
    target: PIL image (rgb)
    mask: logical matrix
    offX: integer
    offY: integer
    db: dictionary
    color: boolean
Returns:
    result: PIL image, final result of splice
"""

def splice(source, target, mask, offY, offX, db):
    #define coordinates of destination in target image if difference sizes
    if db['targeth'] != db['sourceh'] or db['targetw'] != db['sourcew']:
        db['startX_offset'] = offX - db['half_region_height']
        db['startY_offset'] = offY - db['half_region_width']
        db['endX_offset'] = offX + db['half_region_height']
        db['endY_offset'] = offY + db['half_region_width']

    else: # no offset otherwise
        db['startX_offset'] = db['startX']
        db['startY_offset'] = db['startY']
        db['endX_offset'] = db['endX']
        db['endY_offset'] = db['endY']

    # process img
    source = source.split()
    sr, sg, sb = source[0], source[1], source[2]

    target = target.split()
    tr, tg, tb = target[0], target[1], target[2]

    r = splice_gray(sr, tr, mask, db)
    g = splice_gray(sg, tg, mask, db)
    b = splice_gray(sb, tb, mask, db)
    
    rgb = numpy.dstack((r, g, b))
    result = Image.fromarray(rgb)

    return result




"""
Params:
    source: PIL image (grayscale)
    target = PIL image (grayscale)
    mask = logical array
    db = dictionary of all necessary boundary info

Return:
    result = 2D numpy array with one color channel processed
"""
def splice_gray(source, target, mask, db):
    # convert images to arrays
    target = numpy.array(target)
    source = numpy.array(source)

    # find boundaries of mask, mask = 2 for boundaries
    n = db['xNon'].size
    for cy, cx in zip(db['xNon'], db['yNon']):
        if cy-1 >= 0 and mask[cy-1, cx] == 0:
            mask[cy-1, cx] = 2
        if cy+1 < db['sourceh'] and mask[cy+1, cx] == 0:
            mask[cy+1, cx] = 2
        if cx-1 >= 0 and mask[cy, cx-1] == 0:
            mask[cy, cx-1] = 2
        if cx+1 < db['sourcew'] and mask[cy, cx+1] == 0:
            mask[cy, cx+1] = 2

    # clip to relevant space
    clipped_mask = mask[db['startX']:db['endX']+1, db['startY']:db['endY']+1]
    clipped_target = target[db['startX_offset']-1:db['endX_offset'], db['startY_offset']-1:db['endY_offset']]
    clipped_source = source[db['startX']:db['endX']+1, db['startY']:db['endY']+1]

    # convert to ints
    clipped_mask = clipped_mask.astype(numpy.float64)
    clipped_target = clipped_target.astype(numpy.float64)
    clipped_source = clipped_source.astype(numpy.float64)

    laplacian = numpy.array([[0.0, -1.0, 0.0],
                            [-1.0, 4.0, -1.0],
                            [0.0, -1.0, 0.0]])

    # get gradient of source and target
    source_gradient = scipy.signal.convolve2d(clipped_source, laplacian)
    source_gradient = source_gradient[1:db['region_height']+1, 1:db['region_width']+1]

    target_gradient = scipy.signal.convolve2d(clipped_target, laplacian)
    target_gradient = target_gradient[1:db['region_height']+1, 1:db['region_width']+1]

    #initialize A matrix and b matrix
    A = lil_matrix((n, n))
    b = numpy.zeros((n, 1), numpy.float64)

    # build map of unknowns to indices so each unknown has its own unique index
    u_dict = {}
    index = 0
    for cy in range(db['region_width']):
        for cx in range(db['region_height']):
            if clipped_mask[cx, cy] == 1:
                u_dict[(cx, cy)] = index
                index = index+1

    # build A matrix
    index = 0
    for cy in range(db['region_width']):
        for cx in range(db['region_height']):
            if clipped_mask[cx, cy] == 1:
                # check neighbors
                curb = 0
                if cx-1 >= 0:
                    if clipped_mask[cx-1, cy] == 1: # neighbor is in mask
                        A[index, index-1] = -1
                    elif clipped_mask[cx-1, cy] == 2: # neighbor is boundary
                        curb = curb + clipped_target[cx-1, cy]

                if cx+1 < db['region_height']:
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

                if cy+1 < db['region_width']:
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
    for cy in range(db['region_width']):
        for cx in range(db['region_height']):
            if clipped_mask[cx, cy] == 1:
                clipped_target[cx, cy] = x[index]
                index += 1

    target[db['startX_offset']-1:db['endX_offset'], db['startY_offset']-1:db['endY_offset']] = clipped_target

    return target
