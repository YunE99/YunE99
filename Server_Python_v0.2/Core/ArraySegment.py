import numpy as np

class ArraySegment:
    # 생성자
    def __init__(self, array, offset, count):
        if array is None:
            raise ValueError("Array cannot be null.")
        if offset < 0 or count < 0 or offset + count > len(array):
            raise IndexError("Invalid offset or count.")
        
        self._array = np.array(array, dtype=np.uint8)  # 바이트 배열 유지
        self._offset = offset
        self._count = count

    # 배열 얻기
    def array(self):
        return self._array

    # 오프셋 얻기
    def offset(self):
        return self._offset

    # 개수 얻기
    def count(self):
        return self._count
    
    def length(self):
        return self._count

    # 내 배열의 일부 얻기
    def get(self, index):
        if index < 0 or index >= self._count:
            raise IndexError("Index out of range.")
        return self._array[self._offset + index]

    # 내 배열의 일부 복사
    def toArray(self):
        return self.slice().copy()

    # ByteBuffer 역할을 하는 slice 함수
    def slice(self):
        return self._array[self._offset:self._offset + self._count]

    def sliceWithOffset(self, offset, length):
        return self._array[self._offset + offset:self._offset + offset + length]
