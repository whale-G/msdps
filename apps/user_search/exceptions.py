from rest_framework.exceptions import APIException


# 自定义异常类，处理当系统中不存在被查找的记录时抛出的异常
class RecordNotFound(APIException):
    status_code = 404
    default_detail = '记录不存在'
    default_code = 'record_not_found'
