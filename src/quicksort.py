def quicksort(arr):
    """
    快速排序函数
    使用原地分区策略，以中间元素作为基准值
    时间复杂度：平均 O(n log n)，最坏 O(n²)
    空间复杂度：O(log n) 递归调用栈
    """
    # 边界情况处理：空列表或单元素列表直接返回
    if len(arr) <= 1:
        return arr
    
    # 原地快速排序
    _quick_sort_inplace(arr, 0, len(arr) - 1)
    return arr


def _quick_sort_inplace(arr, low, high):
    """
    原地快速排序的递归实现
    
    参数:
        arr: 待排序列表
        low: 起始索引
        high: 结束索引
    """
    if low < high:
        # 分区操作，返回基准值的正确位置
        pivot_index = _partition(arr, low, high)
        
        # 递归排序左半部分
        _quick_sort_inplace(arr, low, pivot_index - 1)
        # 递归排序右半部分
        _quick_sort_inplace(arr, pivot_index + 1, high)


def _partition(arr, low, high):
    """
    分区函数：选择基准值并将数组分为两部分
    
    策略：选择中间元素作为基准值，避免最坏情况
    """
    # 选择中间元素作为基准值
    mid = (low + high) // 2
    arr[mid], arr[high] = arr[high], arr[mid]
    pivot = arr[high]
    
    # i 指向小于基准值的元素的最后位置
    i = low - 1
    
    # 遍历 low 到 high-1 的元素
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    
    # 将基准值放到正确位置
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    
    return i + 1


# 测试代码
if __name__ == "__main__":
    # 测试用例
    test_cases = [
        [],                     # 空列表
        [1],                    # 单元素
        [5, 2, 9, 1, 7, 6, 3], # 普通乱序
        [3, 3, 3, 3],          # 重复元素
        [1, 2, 3, 4, 5],      # 已排序
        [5, 4, 3, 2, 1],      # 逆序
        [-3, 10, -5, 0, 8],   # 包含负数和零
    ]
    
    for arr in test_cases:
        original = arr.copy()
        result = quicksort(arr.copy())
        print(f"原始: {original}")
        print(f"排序后: {result}")
        print("-" * 30)