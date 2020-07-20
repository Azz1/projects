# import the necessary packages
from imutils import contours
from skimage import measure
import numpy as np
import argparse
import imutils
import math
import cv2

class CV2Helper :

    def __init__(self, thresh_limit, blur_limit):
        self.thresh_limit = thresh_limit
        self.blur_limit = blur_limit

    def setref(self, x0, y0, x1, y1) :
        self.ref0 = (x0, y0)
        self.ref1 = (x1, y1)

    def loadimage(self, imgpath) :
        self.image = cv2.imread(imgpath)
        self.height, self.width, _ = self.image.shape
        return self.image

    def processimage(self, mark = False):
        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (self.blur_limit, self.blur_limit), 0)

        # threshold the image to reveal light regions in the
        # blurred image
        thresh = cv2.threshold(blurred, self.thresh_limit, 255, cv2.THRESH_BINARY)[1]
        #cv2.imshow("Thresh", thresh)
        #cv2.waitKey(0)

        # perform a series of erosions and dilations to remove
        # any small blobs of noise from the thresholded image
        #thresh = cv2.erode(thresh, None, iterations=1)
        #thresh = cv2.dilate(thresh, None, iterations=2)

        # perform a connected component analysis on the thresholded
        # image, then initialize a mask to store only the "large"
        # components
        #labels = measure.label(thresh, connectivity=2, background=0)
        labels = measure.label(thresh, neighbors=8, background=0)
        mask = np.zeros(thresh.shape, dtype="uint8")
        # loop over the unique components
        for label in np.unique(labels):
             # if this is the background label, ignore it
             if label == 0:
                 continue

             # otherwise, construct the label mask and count the
             # number of pixels
             labelMask = np.zeros(thresh.shape, dtype="uint8")
             labelMask[labels == label] = 255
             numPixels = cv2.countNonZero(labelMask)

             # if the number of pixels in the component is sufficiently
             # large, then add it to our mask of "large blobs"
             if numPixels >= 4:
                 mask = cv2.add(mask, labelMask)

        # find the contours in the mask, then sort them from left to right
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        cnts = contours.sort_contours(cnts)[0]

        self.centers = [None]*len(cnts)
        self.radius = [None]*len(cnts)
        # loop over the contours
        for (i, c) in enumerate(cnts):
            # draw the bright spot on the image
            ((cX, cY), r) = cv2.minEnclosingCircle(c)
            self.centers[i], self.radius[i] = (cX, cY), int(r)+3

            if mark == True :
                cv2.circle(self.image, (int(cX), int(cY)), int(r)+3, (0, 0, 255), 1)
                cv2.putText(self.image, "#{}".format(i + 1), (int(cX)+5, int(cY) - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)

        return [self.centers, self.radius, self.image]

    def find_nearest_point(self, mark = True ) :
        ni = 0
        dist = 999999.9
        for (i, p) in enumerate(self.centers):
            d = (p[0] - self.ref0[0]) * (p[0] - self.ref0[0]) + (p[1] - self.ref0[1]) * (p[1] - self.ref0[1])
            if d < dist : 
                ni = i
                dist = d

        if mark == True :
            cv2.line(self.image, (int(self.ref0[0]), int(self.ref0[1])), (int(self.ref1[0]), int(self.ref1[1])), (0, 100, 100), 1)
            cv2.line(self.image, (int(self.ref0[0]-5), int(self.ref0[1])), (int(self.ref0[0]+5), int(self.ref0[1])), (0, 250, 150), 1)
            cv2.line(self.image, (int(self.ref0[0]), int(self.ref0[1]-5)), (int(self.ref0[0]), int(self.ref0[1]+5)), (0, 250, 150), 1)
            cv2.circle(self.image, (int(self.ref1[0]), int(self.ref1[1])), int(2), (0, 250, 255), 1)

            cv2.circle(self.image, (int(self.centers[ni][0]), int(self.centers[ni][1])), int(self.radius[ni]), (0, 250, 255), 1)
            cv2.putText(self.image, "#{}".format(ni + 1), (int(self.centers[ni][0]+5), int(self.centers[ni][1]) - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 250, 255), 1)

        return [ni, self.centers[ni], self.image]

    def printcenters(self):
        for (i, p) in enumerate(self.centers):
            print("Point ", "#{}".format(i+1), "- (", int(p[0]), ",", int(p[1]), ")   radius:", self.radius[i])

    def calc_offset(self, x, y):
        A = self.ref1[1] - self.ref0[1]		# A = y1 - y0
        B = self.ref0[0] - self.ref1[0] 	# B = x0 - x1
        C = -B * self.ref0[1] - A * self.ref0[0] # C = -B * y0 - A * x0
        print("A = ", A, "  B = ", B, " C = ", C)

        d = (A * x + B * y + C) / math.sqrt(A * A + B * B)
        print("d = ", d)
		
        R0 = math.sqrt( (x - self.ref0[0]) * (x - self.ref0[0]) + (y - self.ref0[1]) * (y - self.ref0[1]) )
        R1 = math.sqrt( (x - self.ref1[0]) * (x - self.ref1[0]) + (y - self.ref1[1]) * (y - self.ref1[1]) )
        S = math.sqrt( A * A + B * B )
        print("R0 = ", R0, "  R1 = ", R1)
	
        S1 = math.sqrt( R1 * R1 - d * d )
        print("S = ", S, " S1 = ", S1)
        r = S - S1

        return r, d		
		
# Main body

if __name__ == '__main__':
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", required=True, help="path to the image file")
    ap.add_argument("-x0", "--x0", required=True, help="x of ref0 location")
    ap.add_argument("-y0", "--y0", required=True, help="y of ref0 location")
    ap.add_argument("-x1", "--x1", required=True, help="x of ref1 location")
    ap.add_argument("-y1", "--y1", required=True, help="y of ref1 location")
    args = vars(ap.parse_args())

    cvhelper = CV2Helper( blur_limit = 9, thresh_limit = 35 )

    # load the image, convert it to grayscale, and blur it
    image = cvhelper.loadimage(args["image"])
    #cv2.imshow("Original", image)
    #cv2.waitKey(0)

    #image = cvhelper.loadimage("test.jpg")
    [centers, radius, image] = cvhelper.processimage(mark = True)
    cvhelper.printcenters()

    x0, y0 = int(args["x0"]), int(args["y0"])
    x1, y1 = int(args["x1"]), int(args["y1"])
    print("Located Point near", "- (", int(x0), ",", int(y0), ") -->",  "(", int(x1), ",", int(y1), ")")
    cvhelper.setref(x0, y0, x1, y1)
    [idx, cntr, image] = cvhelper.find_nearest_point(True)
    print("Nearest Point ", "#{}".format(idx+1), "- (", int(cntr[0]), ",", int(cntr[1]), ") ")

    r, d = cvhelper.calc_offset(cntr[0], cntr[1])
    print("\nDelta-RA:", r, " Delta-Dec:", d)

    # show the output image
    cv2.imshow("Image", image)
    cv2.waitKey(0)

    #image = cvhelper.loadimage("test1.jpg")
    #[centers, radius, image] = cvhelper.processimage()
    #cvhelper.printcenters()

    # show the output image
    #cv2.imshow("Image1", image)
    #cv2.waitKey(0)


