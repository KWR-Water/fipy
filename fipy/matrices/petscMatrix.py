__docformat__ = 'restructuredtext'

__all__ = []

from petsc4py import PETSc

from fipy.tools import numerix
from fipy.matrices.sparseMatrix import _SparseMatrix

class _PETScMatrix(_SparseMatrix):
    
    def __init__(self, matrix):
        """Creates a wrapper for a PETSc matrix

        Allows basic python operations __add__, __sub__ etc.
        Facilitate matrix populating in an easy way.
        
        :Parameters:
          - `matrix`: The starting `PETSc.Mat` 
        """
        self.matrix = matrix
   
    def getCoupledClass(self):
        return _CoupledPETScMeshMatrix
    
    def copy(self):
        return _PETScMatrix(matrix=self.matrix.copy())
        
    def __getitem__(self, index):
        self.matrix.assemblyBegin()
        self.matrix.assemblyEnd()
        m = self.matrix[index]
        if numerix.shape(m) == ():
            return m
        else:
            return _PETScMatrix(matrix=m)

    def __iadd__(self, other):
        if other != 0:
            self.matrix.assemblyBegin()
            self.matrix.assemblyEnd()
            other.matrix.assemblyBegin()
            other.matrix.assemblyEnd()
            self.matrix = self.matrix + other.matrix
        return self

    def __add__(self, other):
        """
        Add two sparse matrices
        
            >>> L = _PETScMatrixFromShape(rows=3, cols=3, bandwidth=3)
            >>> L.put([3.,10.,numerix.pi,2.5], [0,0,1,2], [2,1,1,0])
            >>> print L + _PETScIdentityMatrix(size=3)
             1.000000  10.000000   3.000000  
                ---     4.141593      ---    
             2.500000      ---     1.000000  
             
            >>> print L + 0
                ---    10.000000   3.000000  
                ---     3.141593      ---    
             2.500000      ---        ---    
            
            >>> print L + 3
            Traceback (most recent call last):
            ...
            AttributeError: 'int' object has no attribute 'matrix'
        """

        if other == 0:
            return self
        else:
            self.matrix.assemblyBegin()
            self.matrix.assemblyEnd()
            other.matrix.assemblyBegin()
            other.matrix.assemblyEnd()
            return _PETScMatrix(matrix=self.matrix + other.matrix)
        
    __radd__ = __add__
    
    def __sub__(self, other):

        if other == 0:
            return self
        else:
            self.matrix.assemblyBegin()
            self.matrix.assemblyEnd()
            other.matrix.assemblyBegin()
            other.matrix.assemblyEnd()
            return _PETScMatrix(matrix=self.matrix - other.matrix)

    def __rsub__(self, other):
        return -self + other
    
    def __isub__(self, other):
        if other != 0:
            self.matrix.assemblyBegin()
            self.matrix.assemblyEnd()
            other.matrix.assemblyBegin()
            other.matrix.assemblyEnd()
            self.matrix = self.matrix - other.matrix
        return self

    def __mul__(self, other):
        """
        Multiply a sparse matrix by another sparse matrix
        
            >>> L1 = _PETScMatrixFromShape(rows=3, cols=3, bandwidth=2)
            >>> L1.put([3.,10.,numerix.pi,2.5], [0,0,1,2], [2,1,1,0])
            >>> L2 = _PETScIdentityMatrix(size=3, bandwidth=3)
            >>> L2.put([4.38], [2], [1])
            >>> L2.put([4.38,12357.2,1.1], [2,1,0], [1,0,2])
            
            >>> tmp = numerix.array(((1.23572000e+05, 2.31400000e+01, 3.00000000e+00),
            ...                      (3.88212887e+04, 3.14159265e+00, 0.00000000e+00),
            ...                      (2.50000000e+00, 0.00000000e+00, 2.75000000e+00)))

            >>> numerix.allclose((L1 * L2).numpyArray, tmp)
            1

        or a sparse matrix by a vector

            >>> tmp = numerix.array((29., 6.28318531, 2.5))       
            >>> numerix.allclose(L1 * numerix.array((1,2,3),'d'), tmp)
            1
            
        or a vector by a sparse matrix

            >>> tmp = numerix.array((7.5, 16.28318531,  3.))  
            >>> numerix.allclose(numerix.array((1,2,3),'d') * L1, tmp) ## The multiplication is broken. Numpy is calling __rmul__ for every element instead of with  the whole array.
            1

            
        """
        N = self._shape[1]

        self.matrix.assemblyBegin()
        self.matrix.assemblyEnd()

        if isinstance(other, _PETScMatrix):
            other.matrix.assemblyBegin()
            other.matrix.assemblyEnd()
            return _PETScMatrix(matrix=self.matrix.matMult(other.matrix))
        else:
            shape = numerix.shape(other)
            if shape == ():
                return _PETScMatrix(matrix=self.matrix * other)
            elif shape == (N,):
                x = PETSc.Vec().createMPI(N, comm=PETSc.COMM_WORLD)
                y = x.duplicate()
                x[:] = other
                self.matrix.mult(x, y)
                return numerix.asarray(y)
            else:
                raise TypeError
            
    def __rmul__(self, other):
        if type(numerix.ones(1, 'l')) == type(other):
            N = self._shape[1]
            x = PETSc.Vec().createMPI(N, comm=PETSc.COMM_WORLD)
            y = x.duplicate()
            x[:] = other
            self.matrix.multTranspose(x, y)
            return numerix.asarray(y)
        else:
            return self * other
            
    @property
    def _shape(self):
        return self.matrix.size

    @property
    def _range(self):
        return range(self._shape[1]), range(self._shape[0])
        
    def put(self, vector, id1, id2):
        """
        Put elements of `vector` at positions of the matrix corresponding to (`id1`, `id2`)
        
            >>> L = _PETScMatrixFromShape(rows=3, cols=3, bandwidth=2)
            >>> L.put([3.,10.,numerix.pi,2.5], [0,0,1,2], [2,1,1,0])
            >>> print L
                ---    10.000000   3.000000  
                ---     3.141593      ---    
             2.500000      ---        ---    
        """
        self.matrix.setValuesCSR(*self._ijv2csr(id2, id1, vector))
            
    def _ijv2csr(self, i, j, v):
        """Convert arrays of matrix indices and values into CSR format
        
        see: http://netlib.org/linalg/html_templates/node91.html#SECTION00931100000000000000

        .. note::
           petsc4py only understands CSR formatted matrices (setValuesCSR and
           setValuesIJV both inexplicably call the same underlying routine).
        
        Parameters
        ----------
        i : array_like
            column indices
        j : array_like
            row indices
        v : array_like
            non-zero values
            
        Returns
        -------
        row_ptr : array_like
            locations in the val vector that start a row, 
            terminated with len(val) + 1
        cols : array_like
            column indices
        val : array_like
            non-zero values
        """
        i = numerix.asarray(i)
        j = numerix.asarray(j)
        v = numerix.asarray(v)
        start_row, end_row = self.matrix.getOwnershipRange()
        
        ix = numerix.lexsort([i, j])
        cols = i[ix]
        row_ptr = numerix.searchsorted(j[ix], 
                                       numerix.arange(start_row, end_row + 1))
        vals = v[ix]
        # note: PETSc (at least via pip) only seems to handle 32 bit addressing
        return row_ptr.astype('int32'), cols.astype('int32'), vals

    def putDiagonal(self, vector):
        """
        Put elements of `vector` along diagonal of matrix
        
            >>> L = _PETScMatrixFromShape(rows=3, cols=3, bandwidth=1)
            >>> L.putDiagonal([3.,10.,numerix.pi])
            >>> print L
             3.000000      ---        ---    
                ---    10.000000      ---    
                ---        ---     3.141593  
            >>> L.putDiagonal([10.,3.])
            >>> print L
            10.000000      ---        ---    
                ---     3.000000      ---    
                ---        ---     3.141593  
        """
        if type(vector) in [type(1), type(1.)]:
            ids = numerix.arange(self._shape[0])
            tmp = numerix.zeros((self._shape[0],), 'd')
            tmp[:] = vector
            self.put(tmp, ids, ids)
        else:
            ids = numerix.arange(len(vector))
            self.put(vector, ids, ids)

    def take(self, id1, id2):
        # FIXME: This is a terrible implementation
        self.matrix.assemblyBegin()
        self.matrix.assemblyEnd()
        vector = [self.matrix[i, j] for i, j in zip(id1, id2)]
        vector = numerix.array(vector, 'd')
        return vector

    def takeDiagonal(self):
        ids = numerix.arange(self._shape[0])
        return self.take(ids, ids)

    def addAt(self, vector, id1, id2):
        """
        Add elements of `vector` to the positions in the matrix corresponding to (`id1`,`id2`)
        
            >>> L = _PETScMatrixFromShape(rows=3, cols=3, bandwidth=3)
            >>> L.put([3.,10.,numerix.pi,2.5], [0,0,1,2], [2,1,1,0])
            >>> L.addAt([1.73,2.2,8.4,3.9,1.23], [1,2,0,0,1], [2,2,0,0,2])
            >>> print L
            12.300000  10.000000   3.000000  
                ---     3.141593   2.960000  
             2.500000      ---     2.200000  
        """
        self.matrix.setValuesCSR(*self._ijv2csr(id2, id1, vector),
                                 addv=True)

    def addAtDiagonal(self, vector):
        if type(vector) in [type(1), type(1.)]:
            ids = numerix.arange(self._shape[0])
            tmp = numerix.zeros((self._shape[0],), 'd')
            tmp[:] = vector
            self.addAt(tmp, ids, ids)
        else:
            ids = numerix.arange(len(vector))
            self.addAt(vector, ids, ids)

    @property
    def numpyArray(self):
        shape = self._shape
        indices = numerix.indices(shape)
        numMatrix = self.take(indices[0].ravel(), indices[1].ravel())
        return numerix.reshape(numMatrix, shape)
                
    def matvec(self, x):
        """
        This method is required for scipy solvers.
        """
        return self * x

    def exportMmf(self, filename):
        """
        Exports the matrix to a Matrix Market file of the given filename.
        """
        self.matrix.export_mtx(filename)
    
class _PETScMatrixFromShape(_PETScMatrix):
    
    def __init__(self, rows, cols, bandwidth=0, sizeHint=None, matrix=None):
        """Instantiates and wraps a PETSc `Mat` matrix

        :Parameters:
          - `rows`: The number of matrix rows
          - `cols`: The number of matrix columns
          - `bandwidth`: The proposed band width of the matrix.
          - `sizeHint`: estimate of the number of non-zeros
          - `matrix`: pre-assembled `ll_mat` to use for storage
          
        """
        bandwidth = bandwidth 
        if (bandwidth == 0) and (sizeHint is not None):
            bandwidth = sizeHint / max(rows, cols)
        if matrix is None:
            matrix = PETSc.Mat()
            matrix.create(PETSc.COMM_WORLD)
            matrix.setSizes([rows, cols])
            matrix.setType('aij') # sparse
            matrix.setPreallocationNNZ(None) # FIXME: ??? #bandwidth)
                
        _PETScMatrix.__init__(self, matrix=matrix)

class _PETScMeshMatrix(_PETScMatrixFromShape):
    def __init__(self, mesh, bandwidth=0, sizeHint=None, matrix=None, numberOfVariables=1, numberOfEquations=1):

        """Creates a `_PETScMatrixFromShape` associated with a `Mesh`. Allows for different number of equations and/or variables

        :Parameters:
          - `mesh`: The `Mesh` to assemble the matrix for.
          - `bandwidth`: The proposed band width of the matrix.
          - `sizeHint`: estimate of the number of non-zeros
          - `matrix`: pre-assembled `ll_mat` to use for storage
          - `numberOfVariables`: The columns of the matrix is determined by numberOfVariables * self.mesh.numberOfCells.
          - `numberOfEquations`: The rows of the matrix is determined by numberOfEquations * self.mesh.numberOfCells.
        """
        self.mesh = mesh
        self.numberOfVariables = numberOfVariables
        self.numberOfEquations = numberOfEquations
        rows = numberOfEquations * self.mesh.numberOfCells
        cols = numberOfVariables * self.mesh.numberOfCells
        _PETScMatrixFromShape.__init__(self, rows=rows, cols=cols, bandwidth=bandwidth, sizeHint=sizeHint, matrix=matrix)

    def __mul__(self, other):
        if isinstance(other, _PETScMeshMatrix):
            self.matrix.assemblyBegin()
            self.matrix.assemblyEnd()
            other.matrix.assemblyBegin()
            other.matrix.assemblyEnd()
            return _PETScMeshMatrix(mesh=self.mesh, 
                                    matrix=self.matrix.matMult(other.matrix))
        else:
            return _PETScMatrixFromShape.__mul__(self, other)

    @property
    def numpyArray(self):
        return super(_PETScMeshMatrix, self).numpyArray

    def flush(self):
        """
        Deletes the copy of the PETSc matrix held.
        """
    
        if not getattr(self, 'cache', False):
            del self.matrix

    def _test(self):
        """
        Tests
        
        >>> m = _PETScMatrixFromShape(rows=3, cols=3, bandwidth=1)
        >>> m.addAt((1., 0., 2.), (0, 2, 1), (1, 2, 0))
        >>> m.matrix.assemblyBegin()
        >>> m.matrix.assemblyEnd()
        
        # FIXME: are these names even right? is this a good test?
        
        >>> col, row, val = m.matrix.getValuesCSR()
        >>> print numerix.allequal(col, [0, 1, 2, 3])
        True
        >>> print numerix.allequal(row, [1, 0, 2])
        True
        >>> print numerix.allclose(val, [1., 2., 0.])
        True
        """
        pass
        
class _PETScIdentityMatrix(_PETScMatrixFromShape):
    """
    Represents a sparse identity matrix for pysparse.
    """
    def __init__(self, size, bandwidth=1):
        """Create a sparse matrix with '1' in the diagonal
        
            >>> print _PETScIdentityMatrix(size=3)
             1.000000      ---        ---    
                ---     1.000000      ---    
                ---        ---     1.000000  
        """
        _PETScMatrixFromShape.__init__(self, rows=size, cols=size, bandwidth=bandwidth)
        ids = numerix.arange(size)
        self.put(numerix.ones(size, 'd'), ids, ids)
        
class _PETScIdentityMeshMatrix(_PETScIdentityMatrix):
    def __init__(self, mesh, bandwidth=1):
        """Create a sparse matrix associated with a `Mesh` with '1' in the diagonal
        
            >>> from fipy import Grid1D
            >>> from fipy.tools import serialComm
            >>> mesh = Grid1D(nx=3, communicator=serialComm)
            >>> print _PETScIdentityMeshMatrix(mesh=mesh)
             1.000000      ---        ---    
                ---     1.000000      ---    
                ---        ---     1.000000  
        """
        _PETScIdentityMatrix.__init__(self, size=mesh.numberOfCells, bandwidth=bandwidth)

def _test(): 
    import fipy.tests.doctestPlus
    return fipy.tests.doctestPlus.testmod()
    
if __name__ == "__main__": 
    _test() 
