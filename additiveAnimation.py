# -*- coding: utf-8 -*-
"""
This software is provided 'as-is', without any express or implied
warranty.  In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.

2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.

Author:
Eduardo Simioni <eduardo.simioni@gmail.com>
http://www.eduardosimioni.com
"""

from pyfbsdk import *
import pprint
import math

app = FBApplication()
system = FBSystem()
scene = FBSystem().Scene
player = FBPlayerControl()
animMatrix = [] # used to store each model FCurve (on Take 001)
subMatrix = [] # used to store each model FCurve to be substracted (on Take 002)
pp = pprint.PrettyPrinter()


# from KxL at Autodesk Area:
# http://area.autodesk.com/forum/63719

def FBMatrixFromAnimationNode( pModel, pTime ):
    lResult = FBMatrix()
    lTranslationNode = pModel.Translation.GetAnimationNode()
    lRotationNode = pModel.Rotation.GetAnimationNode()
    lScaleNode = pModel.Scaling.GetAnimationNode()

    lRotationV = FBVector3d(
        lRotationNode.Nodes[0].FCurve.Evaluate(pTime) * 0.017453292519943295769236907684886,
        lRotationNode.Nodes[1].FCurve.Evaluate(pTime) * 0.017453292519943295769236907684886,
        lRotationNode.Nodes[2].FCurve.Evaluate(pTime) * 0.017453292519943295769236907684886)

    lScaleV = FBVector3d(
        lScaleNode.Nodes[0].FCurve.Evaluate(pTime),
        lScaleNode.Nodes[1].FCurve.Evaluate(pTime),
        lScaleNode.Nodes[2].FCurve.Evaluate(pTime))

    sphi = math.sin(lRotationV[0])
    cphi = math.cos(lRotationV[0])
    stheta = math.sin(lRotationV[1])
    ctheta = math.cos(lRotationV[1])
    spsi = math.sin(lRotationV[2])
    cpsi = math.cos(lRotationV[2])

    lResult[0] = (cpsi*ctheta)*lScaleV[0]
    lResult[1] = (spsi*ctheta)*lScaleV[0]
    lResult[2] = (-stheta)*lScaleV[0]

    lResult[4] = (cpsi*stheta*sphi - spsi*cphi)*lScaleV[1]
    lResult[5] = (spsi*stheta*sphi + cpsi*cphi)*lScaleV[1]
    lResult[6] = (ctheta*sphi)*lScaleV[1]

    lResult[8] = (cpsi*stheta*cphi + spsi*sphi)*lScaleV[2]
    lResult[9] = (spsi*stheta*cphi - cpsi*sphi)*lScaleV[2]
    lResult[10] = (ctheta*cphi)*lScaleV[2]

    lResult[12] = lTranslationNode.Nodes[0].FCurve.Evaluate(pTime)
    lResult[13] = lTranslationNode.Nodes[1].FCurve.Evaluate(pTime)
    lResult[14] = lTranslationNode.Nodes[2].FCurve.Evaluate(pTime)

    return lResult


def FBMatrixMult( pParent, pChild ):
    pResult = FBMatrix()
    sum =0
    aa = 0
    bb = 0
    for i in range(0,4):
        for j in range(0,4):
            c = j
            b = bb
            sum = 0
            for k in range(0,4): 
                sum += pChild [b]*pParent[c]
                c += 4
                b += 1
            pResult[aa] = sum
            aa+=1
        bb += 4

    return pResult

# end of KxL code



# neill's code from:
# http://neill3d.com/mobi-skript-raschet-additivnoj-animacii?langswitch_lang=en

def MatrixInverse(M):
    out = FBMatrix()
    out.Identity()

    for i in range(0,4):
            d = M[i*4+i]
            if (d <> 1.0):
                for j in range(0,4):
                    out[i*4+j] /= d
                    M[i*4+j] /= d
                    
            for j in range(0,4):
                if (j <> i):
                    if (M[j*4+i] <> 0.0):
                        mulBy = M[j*4+i]
                        for k in range(0,4):
                            M[j*4+k] -= mulBy * M[i*4+k]
                            out[j*4+k] -= mulBy * out[i*4+k]

    return out

# this one is not working, whereas FBMatrixMult works. need to investigate why.
def MatrixMult(Ma, Mb):
    res = FBMatrix()

    for i in range(0,4):
        for j in range(0,4):
            sum=0
            for k in range(0,4):
                sum += Ma[i*4+k] * Mb[k*4+j]

            res[i*4+j] = sum
    return res

def MatrixToEulerAngles( M ):
    heading = 0.0
    attitude = 0.0
    bank = 0.0

    if (M[4] > 0.998):
        heading = math.atan2(M[2], M[10] )
        attitude = math.pi /2
        bank = 0
    if (M[4] < -0.998):
        heading = math.atan2(M[2], M[10] )
        attitude = -math.pi /2
        bank = 0

    heading = math.atan2(-M[8], M[0])
    bank = math.atan2(-M[6], M[5])
    attitude = math.asin(M[4])

    heading = heading * 180 / math.pi
    attitude = attitude * 180 / math.pi
    bank = bank * 180 / math.pi

    res = FBVector3d( -1*bank, -1 * heading, -attitude )
    return res

# end of Neill's code





def getCurve(lModel, fFirst, fLast):
    """
    Receives root model (hips) and proceeds to store all skeleton
    keys information as a single array of FBMatrix() in vectorToRet
    """
    
    lAnimNode = lModel.Rotation.GetAnimationNode()
    vectorToRet = []

    for lCounter in range(fFirst, fLast+1): # range is not inclusive http://docs.python.org/library/functions.html#range    
        vectorToRet.append( FBMatrixFromAnimationNode(lModel, FBTime(0,0,0,lCounter)) )

    # print lModel.Name
    # pp.pprint( vectorToRet)
       
    for child in lModel.Children:
        vectorToRet.extend(getCurve(child, fFirst, fLast))
    
    return vectorToRet




def setCurve(lModel, fFirst, fLast, vResult, offset):
    """
    Receives root model and array of FBVector3d() to apply
    to each model of the skeleton's Rotation.AnimationNode
    """
    
    lAnimNode = lModel.Rotation.GetAnimationNode()
    timeline = fLast - fFirst + 1
    
    for lCounter in range(timeline):
        for axis in range(3):
            # print "lcounter: " + str(lCounter) + "    axis: " + str(axis) + "           offset: " + str(offset) + "      vResult len: " + str(len(vResult)) + "      node name: " + lModel.Name
            lAnimNode.Nodes[axis].KeyAdd(FBTime(0,0,0,lCounter), vResult[lCounter+offset][axis])

    offset += timeline
    for child in lModel.Children:
        offset = setCurve(child, fFirst, fLast, vResult, offset)
    # print timeline
    return offset
    

def main():
   
    if (len(scene.Takes)!= 3):
        FBMessageBox( "Incorrect amount of takes", "Please create 3 takes in this order: additive anim, substraction anim, result take", "OK", None, None )
        return False
    else:
        takeAnimation = scene.Takes[0]
        takeSubstraction = scene.Takes[1]
        takeResult = scene.Takes[2]

    lStartFrame = FBPlayerControl().LoopStart.GetFrame(True)
    lStopFrame = FBPlayerControl().LoopStop.GetFrame(True)

    rootModel = FBFindModelByName("b_Hips")
    
    system.CurrentTake = takeAnimation
    scene.Evaluate()
    animMatrix = getCurve(rootModel, lStartFrame, lStopFrame)

    system.CurrentTake = takeSubstraction
    scene.Evaluate()
    subMatrix = getCurve(rootModel, lStartFrame, lStopFrame)

    system.CurrentTake = takeResult
    scene.Evaluate()
   
   
    # iterates through each matrix and stores the result as FBVector3d for the rotation animatino node.
    # subtracted rotation = (original rotation matrix) * (inverse of subtrahend)
    # M3 = M1 * M2^-1
    # we also extract euler angles from the rotation matrix
    resultVectors = []
    for i in range(len(animMatrix)):
        resultVectors.append( MatrixToEulerAngles (FBMatrixMult(animMatrix[i], (MatrixInverse(subMatrix[i])))))
    
    # print "resultvectors"
    # pp.pprint(resultVectors)

    setCurve(rootModel, lStartFrame, lStopFrame, resultVectors, 0)


#   To be added on version 1.0

#    character = app.CurrentCharacter #FBCharacter()
#    if character:
#       #DO SCRIPT
#       rootModel = character.GetModel(FBBodyNodeId.kFBHipsNodeId)
#       print "rootModel is:", rootModel.Name
#        
#    else: # if character fails there's no character on the scene/selected
#        FBMessageBox( "No character selected", "Please select a character", "OK", None, None )
        
        


main()