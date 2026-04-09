"""
快速排序函数的 pytest 测试用例
"""
import pytest
import sys
import os

# 将源文件路径添加到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from quicksort import quicksort


class TestQuicksort:
    """测试快速排序函数的各种场景"""
    
    # ========== 边界情况测试 ==========
    
    def test_empty_array(self):
        """测试空数组"""
        arr = []
        result = quicksort(arr.copy())
        assert result == []
    
    def test_single_element(self):
        """测试单元素数组"""
        arr = [1]
        result = quicksort(arr.copy())
        assert result == [1]
    
    def test_two_elements(self):
        """测试两元素数组"""
        arr = [2, 1]
        result = quicksort(arr.copy())
        assert result == [1, 2]
    
    # ========== 普通情况测试 ==========
    
    def test_regular_unsorted_array(self):
        """测试普通乱序数组"""
        arr = [5, 2, 9, 1, 7, 6, 3]
        result = quicksort(arr.copy())
        assert result == [1, 2, 3, 5, 6, 7, 9]
    
    def test_array_with_negative_numbers(self):
        """测试包含负数的数组"""
        arr = [-3, 10, -5, 0, 8]
        result = quicksort(arr.copy())
        assert result == [-5, -3, 0, 8, 10]
    
    # ========== 特殊情况测试 ==========
    
    def test_already_sorted_array(self):
        """测试已升序排序的数组"""
        arr = [1, 2, 3, 4, 5]
        result = quicksort(arr.copy())
        assert result == [1, 2, 3, 4, 5]
        # 验证原始数组未被修改
        assert arr == [1, 2, 3, 4, 5]
    
    def test_reverse_sorted_array(self):
        """测试降序数组"""
        arr = [5, 4, 3, 2, 1]
        result = quicksort(arr.copy())
        assert result == [1, 2, 3, 4, 5]
    
    def test_array_with_duplicates(self):
        """测试包含重复元素的数组"""
        arr = [3, 3, 3, 3]
        result = quicksort(arr.copy())
        assert result == [3, 3, 3, 3]
    
    def test_array_with_multiple_duplicates(self):
        """测试包含多个不同重复值的数组"""
        arr = [2, 5, 2, 8, 5, 2, 8, 5]
        result = quicksort(arr.copy())
        assert result == [2, 2, 2, 5, 5, 5, 8, 8]
    
    def test_array_with_all_same_value(self):
        """测试所有元素相同的数组"""
        arr = [7, 7, 7, 7, 7]
        result = quicksort(arr.copy())
        assert result == [7, 7, 7, 7, 7]
    
    # ========== 大小边界测试 ==========
    
    def test_large_array(self):
        """测试较大的数组"""
        arr = list(range(1000, 0, -1))
        result = quicksort(arr.copy())
        assert result == list(range(1, 1001))
    
    def test_already_sorted_large_array(self):
        """测试已排序的大数组"""
        arr = list(range(1, 1001))
        result = quicksort(arr.copy())
        assert result == list(range(1, 1001))
    
    # ========== 正确性验证测试 ==========
    
    def test_sorted_result_is_correct_order(self):
        """验证排序结果的正确性"""
        arr = [64, 34, 25, 12, 22, 11, 90]
        result = quicksort(arr.copy())
        
        # 验证每个元素都在正确位置
        for i in range(len(result) - 1):
            assert result[i] <= result[i + 1]
    
    def test_original_array_not_modified(self):
        """验证原始数组未被修改"""
        original = [5, 3, 8, 1, 9, 2]
        arr_copy = original.copy()
        
        result = quicksort(arr_copy)
        
        # 验证原始数组未被修改
        assert original == [5, 3, 8, 1, 9, 2]
        # 验证返回的是排序后的数组
        assert result == [1, 2, 3, 5, 8, 9]
    
    def test_returns_list(self):
        """验证返回值是列表类型"""
        arr = [3, 1, 4, 1, 5]
        result = quicksort(arr)
        
        assert isinstance(result, list)
    
    def test_preserves_all_elements(self):
        """验证排序后包含所有原始元素"""
        original = [5, 2, 8, 1, 9, 3, 7, 4, 6]
        result = quicksort(original.copy())
        
        assert sorted(result) == sorted(original)
        assert len(result) == len(original)
    
    # ========== 特殊数值测试 ==========
    
    def test_with_zeros(self):
        """测试包含零的数组"""
        arr = [0, -1, 3, 0, 2]
        result = quicksort(arr.copy())
        assert result == [-1, 0, 0, 2, 3]
    
    def test_with_floats(self):
        """测试包含浮点数的数组"""
        arr = [3.5, 1.2, 2.8, 0.5, 4.1]
        result = quicksort(arr.copy())
        assert result == [0.5, 1.2, 2.8, 3.5, 4.1]
    
    def test_with_mixed_integers_and_floats(self):
        """测试包含整数和浮点数的混合数组"""
        arr = [1, 2.5, 3, 0.5, 4]
        result = quicksort(arr.copy())
        assert result == [0.5, 1, 2.5, 3, 4]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])