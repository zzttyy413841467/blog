import json, logging, inspect, functools


class APIError(Exception):
    ' the base APIError which contains error(required), data(optional) and message(optional). '

    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message


class APIValueError(APIError):
    '''indicate the input value has error or invalid.'''

    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('value:invalid', field, message)


class APIResourceNotFoundError(APIError):
    """indicate the resource was not found."""

    def __init__(self, field, message=''):
        super(APIResourceNotFoundError, self).__init__('value:notFound', field, message)


class APIPermissionError(APIError):
    """indicate the api has no permission."""

    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)


class Page(object):
    def __init__(self, item_count, page_index=1, page_size=10):
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        if (item_count == 0) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size
        self.has_next = self.page_index < self.page_count  # 下一页标识
        self.has_previous = self.page_index >1 # 上一页标识

    def __str__(self):
        '''定制print(Page)显示的信息'''
        return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' %(self.item_count,
                                                                                                      self.page_count,
                                                                                                     self.page_index,
                                                                                                      self.page_size,
                                                                                                      self.offset,
                                                                                                      self.limit)

    __repr__ = __str__  # 命令行中显示的信息与print(Page)一致



if __name__=='__main__':
    import doctest
    doctest.testmod()