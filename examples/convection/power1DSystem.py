#!/usr/bin/env python

## 
 # ###################################################################
 #  PFM - Python-based phase field solver
 # 
 #  FILE: "testStdyConvectionDiffusion.py"
 #                                    created: 12/16/03 {3:23:47 PM}
 #                                last update: 12/22/03 {4:28:58 PM} 
 #  Author: Jonathan Guyer
 #  E-mail: guyer@nist.gov
 #    mail: NIST
 #     www: http://ctcms.nist.gov
 #  
 # ========================================================================
 # This software was developed at the National Institute of Standards
 # and Technology by employees of the Federal Government in the course
 # of their official duties.  Pursuant to title 17 Section 105 of the
 # United States Code this software is not subject to copyright
 # protection and is in the public domain.  PFM is an experimental
 # system.  NIST assumes no responsibility whatsoever for its use by
 # other parties, and makes no guarantees, expressed or implied, about
 # its quality, reliability, or any other characteristic.  We would
 # appreciate acknowledgement if the software is used.
 # 
 # This software can be redistributed and/or modified freely
 # provided that any derivative works bear some notice that they are
 # derived from it, and any modified versions bear some notice that
 # they have been modified.
 # ========================================================================
 #  
 #  Description: 
 # 
 #  History
 # 
 #  modified   by  rev reason
 #  ---------- --- --- -----------
 #  2003-11-10 JEG 1.0 original
 # ###################################################################
 ##

from terms.powerLawConvectionTerm import PowerLawConvectionTerm
from convectionDiffusionSystem import ConvectionDiffusionSystem
from boundaryConditions.fixedValue import FixedValue
from boundaryConditions.fixedFlux import FixedFlux

class Power1DSystem(ConvectionDiffusionSystem):

    def __init__(self):
        self.L = 10.
        self.nx = 1000
        self.ny = 1
        self.diffCoeff = 1.
        self.convCoeff = (10.,0.)
        self.sourceCoeff = 0.
        self.convectionScheme = PowerLawConvectionTerm
        ConvectionDiffusionSystem.__init__(self)

    def getBoundaryConditions(self):
        return (
            FixedValue(faces = self.mesh.getFacesLeft(),value = self.valueLeft),
            FixedValue(faces = self.mesh.getFacesRight(),value = self.valueRight),
            FixedFlux(faces = self.mesh.getFacesTop(),value = 0.),
            FixedFlux(faces = self.mesh.getFacesBottom(),value = 0.)
            )

if __name__ == '__main__':
    system = Power1DSystem()
    system.run()

            
            
