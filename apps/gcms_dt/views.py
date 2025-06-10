import copy
import re
import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

import xlrd3 as xlrd
from .models import Gcms_UserFiles


class GcmsProcessShimazu(APIView):
    parser_classes = [MultiPartParser, FormParser]

    # 岛津气质2010&8050
    def post(self, request):
        user = request.user
        # 判断是否登录
        if not user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        # 获取用户uuid
        uuid = user.uuid
        # 生成本次处理记录的id（系统唯一）
        process_id = ""
        current_time = datetime.datetime.now()
        current_time_str = str(current_time.year) + str(current_time.month) + str(current_time.day) + str(
            current_time.hour) + str(current_time.minute) + str(current_time.second)
        process_id = str(uuid) + current_time_str + "gcms"
        # 获取用户设置的RT浮动参数（默认为0.1）
        float_parameter = float(request.data.get("float_parameter"))
        # 获取所有上传文件对象
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            return Response({"status": "error", "message": "未检测到文件"}, status=400)

        try:
            # 处理结果
            processed_results = []
            # 遍历处理每个文件，得到每个文件的待处理数据集合
            for file_obj in uploaded_files:
                # 记录单个文件状态
                file_result = {
                    "file_name": file_obj.name,
                    "status": "success",
                    "data": [],
                    "errors": []
                }
                try:
                    # 检验文件类型
                    if not file_obj.name.lower().endswith(('.xls', '.xlsx')):
                        raise ValueError("仅支持Excel文件 (.xls/.xlsx)")

                    # 读取Excel内容
                    file_data = file_obj.read()
                    workbook = xlrd.open_workbook(file_contents=file_data)

                    # 数据处理核心逻辑

                    # 获得待处理的数据对象
                    file_data = []  # 单个文件中待处理数据
                    # 仅有一个sheet（硬性需求）
                    worksheet = workbook.sheet_by_index(0)
                    if worksheet.nrows != 0:
                        head_index = {}     # 存储指定表头的索引
                        flag = False        # 标志是否找到待处理区域
                        for row_idx in range(0, worksheet.nrows):
                            flag_cell = worksheet.cell(row_idx, 0)
                            if not flag and re.match("^\[MC Peak Table\]$", str(flag_cell.value)):
                                flag = True
                            # 待处理区域结束
                            if flag and flag_cell.value == "":
                                flag = False
                            # 获取指定表头索引
                            if flag and re.match("^Peak#$", str(flag_cell.value)):
                                head_row = worksheet.row_values(row_idx)
                                head_index = {
                                    "RT": head_row.index("Ret.Time"),
                                    "Area": head_row.index("Area"),
                                    "CompoundName": head_row.index("Name"),
                                    "SI": head_row.index("SI"),
                                    "CAS": head_row.index("CAS #")
                                }
                            # 开始获取数据
                            if flag:
                                row = worksheet.row_values(row_idx)
                                table_row = []
                                for key, value in head_index.items():
                                    table_row.append(row[value])

                                # 去除空行
                                if len(table_row) != 0:
                                    # 将area元素位置换到最后，便于后面处理
                                    table_row.append(table_row.pop(1))
                                    file_data.append(table_row)

                    # 单个文件待处理数据集合
                    file_result["data"] = file_data

                except Exception as e:
                    file_result["errors"].append({
                        "error": str(e)
                    })

                # 添加单个文件的待处理数据对象
                processed_results.append(file_result)

            # 文件处理结束，整合所有待处理数据
            # for file_obj in processed_results:
            #     print(file_obj["data"])
            #     print("##########")

            # 下面的逻辑会修改processed_results，故最终返回当前副本
            processed_results_temp = copy.deepcopy(processed_results)

            # 获取基准RT列表（包括[rt,name,si,cas,area])
            base_rt_data = []
            # 以第一个文件的数据为基准
            for data in processed_results[0]["data"][1:]:
                if len(base_rt_data) == 0:
                    base_rt_data.append([ele for ele in data])
                flag = False
                for base_data in base_rt_data:
                    # 在某rt范围内且为同种化合物，即多余数据，不添加至基准数据列表
                    if (base_data[0] + float_parameter) >= data[0] >= (base_data[0] - float_parameter) and base_data[1] == data[1]:
                        flag = True
                if not flag:
                    base_rt_data.append([ele for ele in data])

            # for data in base_rt_data:
            #     print(data)
            # print(len(base_rt_data))

            # 遍历所有文件的数据，丰富基准RT列表，得到最终处理结果列表
            for idx in range(1, len(processed_results)):
                # 建立副本，每次处理一个文件，基准列表均会发生变化
                base_temp = copy.deepcopy(base_rt_data)     # 深拷贝
                # 记录当前文件处理结束后，基准列表元素最终长度（加1）
                result_len = len(base_temp[1]) + 1

                # 对单个文件的数据进行判断
                for data in processed_results[idx]["data"][1:]:
                    match_stack = []    # 数据匹配栈
                    flag = False  # 标志当前数据是否处理
                    # 跳过表头元素，从1开始
                    for base_idx in range(len(base_temp)):
                        # 情况1：如在基准列表的某一rt浮动范围内，且为同种化合物，即重复。在对应基准列表数据添加area数据
                        if (base_temp[base_idx][0] + float_parameter) >= data[0] >= (base_temp[base_idx][0] - float_parameter) and base_temp[base_idx][1] == data[1]:
                            # 特殊情况：单个文件内存在多条数据与基准数据匹配，仅存储第一次匹配到的数据。
                            if len(base_temp[base_idx]) == result_len:
                                flag = True
                                break
                            # 在对应数据列表添加area数据
                            base_temp[base_idx].append(data[-1])
                            # 当前数据已处理，结束
                            flag = True
                            break
                        # 情况2：如在基准列表的某一rt浮动范围内但不为同种化合物，入数据匹配栈（可能后续有符合情况1的基准数据）
                        if (base_temp[base_idx][0] + float_parameter) >= data[0] >= (base_temp[base_idx][0] - float_parameter) and base_temp[base_idx][1] != data[1]:
                            # 将当前数据对应情况2的基准数据索引入栈
                            match_stack.append(base_idx)

                    # 当前数据未处理
                    if not flag:
                        # 数据匹配栈非空，即栈中数据为新基准数据
                        if len(match_stack) != 0:
                            # 此前文件对应数据均为ND
                            for i in range(0, idx):
                                data.insert(-1, "ND")
                            # 添加到对应基准列表数据之后
                            base_temp.insert(match_stack[0] + 1, data)

                        # 不在基准列表的任一rt浮动范围内且数据匹配栈为空，添加到基准列表
                        else:
                            # 此前文件对应数据均为ND
                            for i in range(0, idx):
                                data.insert(-1, "ND")
                            # 添加到基准列表末尾
                            base_temp.append(data)

                # 当前文件数据判断结束，处理基准列表中没有填充数据的空位，添加‘ND’
                for data in base_temp[1:]:
                    if len(data) < result_len:
                        data.append("ND")

                # 单个文件处理结束后的基准列表
                base_rt_data = copy.deepcopy(base_temp)

            # for data in base_rt_data:
            #     print(data)
            # print(len(base_rt_data))

            # 将最终结果按照rt从小到大排序
            base_rt_data.sort(key=lambda x: x[0])
            # 添加表头
            base_rt_data.insert(0, processed_results[0]["data"][0])

            # 整合后的数据
            processed_total_result = copy.deepcopy(base_rt_data)
            # 补充表头，processed_total_result[0]
            for file_obj in processed_results:
                processed_total_result[0].append(file_obj["file_name"])

            # for file_obj in processed_results_temp:
            #     print(file_obj["data"])
            #     print("##########")
            # print("----------")
            # for data in processed_total_result:
            #     print(data)
            # print(len(processed_total_result))

            # 将processed_results_temp和processed_total_result转换为字典
            single_result_head = ["RT", "CompoundName", "SI", "CAS", "Area"]
            for file_obj in processed_results_temp:
                file_obj["data"] = file_obj["data"][1:]
                file_obj["data"] = [
                    {single_result_head[i]: value for i, value in enumerate(item)}
                    for item in file_obj["data"]
                ]

            total_result_head = processed_total_result[0]           # 获取表头
            total_result_head.pop(4)                                # 调整，删除"Area"
            processed_total_result = processed_total_result[1:]     # 去除最终结果的表头
            processed_total_result = [
                {total_result_head[i]: value for i, value in enumerate(item)}
                for item in processed_total_result
            ]

            # 将处理结果保存至数据库
            Gcms_UserFiles.objects.create(process_id=process_id, user=user, file_type="gcms-shimazu-2010&8050", single_file_json=processed_results_temp, total_file_json=processed_total_result)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "服务器处理异常",
                "detail": str(e)
            }, status=500)

        return Response({
            "status": "completed",
            "total_files": len(processed_results),
            "single_results": processed_results_temp,
            "total_result": processed_total_result
        })


class GcmsProcessThermo(APIView):
    parser_classes = [MultiPartParser, FormParser]

    # 热电气质
    def post(self, request):
        user = request.user
        # 判断是否登录
        if not user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            # 获取用户uuid
            uuid = user.uuid
            # 生成本次处理记录的id（系统唯一）
            process_id = ""
            current_time = datetime.datetime.now()
            current_time_str = str(current_time.year) + str(current_time.month) + str(current_time.day) + str(
                current_time.hour) + str(current_time.minute) + str(current_time.second)
            process_id = str(uuid) + current_time_str + "gcms"
            # 获取用户设置的RT浮动参数（默认为0.1）
            float_parameter = float(request.data.get("float_parameter"))
            # 获取所有上传文件对象
            uploaded_files = request.FILES.getlist('files')
            if not uploaded_files:
                return Response({"status": "error", "message": "未检测到文件"}, status=400)

            # 处理结果
            processed_results = []
            # 遍历处理每个文件，得到每个文件的待处理数据集合
            for file_obj in uploaded_files:
                # 记录单个文件状态
                file_result = {
                    "file_name": file_obj.name,
                    "status": "success",
                    "data": [],
                    "errors": []
                }
                try:
                    # 检验文件类型
                    if not file_obj.name.lower().endswith(('.xls', '.xlsx')):
                        raise ValueError("仅支持Excel文件 (.xls/.xlsx)")

                    # 读取Excel内容
                    file_data = file_obj.read()
                    workbook = xlrd.open_workbook(file_contents=file_data)

                    # 数据处理核心逻辑

                    # 获得待处理的数据对象
                    # 仅有一个sheet（硬性需求）
                    worksheet = workbook.sheet_by_index(0)

                    # 获取RT对应的Area数据
                    rt_area = []  # 单个文件中rt对应的area
                    if worksheet.nrows != 0:
                        flag = False    # 标志匹配待处理区域
                        for row in range(worksheet.nrows):
                            row_temp = []   # 临时存储数据
                            flag_cell_1 = worksheet.cell(row, 0)    # 匹配RT
                            flag_cell_2 = worksheet.cell(row, 2)    # 匹配Peak Area
                            # 区域匹配
                            if flag_cell_1.value == "RT" and flag_cell_2.value == "Peak Area":
                                flag = True
                            # 另一个区域（见下）
                            elif flag_cell_1.value == "RT" and flag_cell_2.value != "Peak Area":
                                break
                            # 匹配的区域结束
                            if flag_cell_1.value == "":
                                flag = False
                            # 提取数据
                            if flag and flag_cell_1.value != "" and flag_cell_1.value != "RT":
                                row_temp.append(flag_cell_1.value)
                                row_temp.append(flag_cell_2.value)
                                rt_area.append(row_temp)

                    # for row in rt_area:
                    #     print(row)
                    # print("-----")
                    # print(len(rt_area))

                    # 获取其他数据
                    file_data = []
                    head_index = {}  # 存储表头索引
                    if worksheet.nrows != 0:
                        flag = False    # 标志区域是否匹配
                        flag_head = False   # 标志获取表头索引
                        for row_idx in range(0, worksheet.nrows):
                            row_temp = []
                            flag_cell_1 = worksheet.cell(row_idx, 0)
                            flag_cell_2 = worksheet.cell(row_idx, 1)
                            # 区域匹配
                            if flag_cell_1.value == "RT" and flag_cell_2.value == "Compound Name":
                                flag = True
                                if not flag_head:
                                    # 0:RT, 1:Compound Name, 3:CAS, 4:Area, 5:MF, 10:SI, 11:RSI
                                    head_row = worksheet.row_values(row_idx)
                                    head_index = {
                                        "RT": head_row.index("RT"),
                                        "CompoundName": head_row.index("Compound Name"),
                                        "CAS": head_row.index("Cas #"),
                                        "MF": head_row.index("Molecular Formula"),
                                        "SI": head_row.index("SI"),
                                        "RSI": head_row.index("RSI")
                                    }
                                    flag_head = True
                            # 提取数据
                            if flag and flag_cell_1.value != "" and flag_cell_1.value != "RT":
                                row = worksheet.row_values(row_idx)
                                for key, value in head_index.items():
                                    row_temp.append(row[value])
                                file_data.append(row_temp)
                                flag = False  # 只取每部分的第一个

                    # for data in file_data:
                    #     print(data)
                    # print(len(file_data))

                    # 增加Area数据
                    for idx in range(0, len(file_data)):
                        file_data[idx].append(rt_area[idx][1])

                    # for data in file_data:
                    #     print(data)
                    # print(len(file_data))

                    # 单个文件待处理数据集合
                    file_result["data"] = file_data

                except Exception as e:
                    print(str(e))
                    file_result["errors"].append({
                        "error": str(e)
                    })

                # 添加单个文件的待处理数据对象
                processed_results.append(file_result)

            # 文件处理结束，整合所有待处理数据

            # 下面的逻辑会修改processed_results，故最终返回当前副本
            processed_results_temp = copy.deepcopy(processed_results)

            # 获取基准列表（包括[RT,CompoundName,CAS,MF,SI,RSI,Area])
            base_rt_data = []
            for data in processed_results[0]["data"]:
                # 以第一个文件的数据为基准
                base_rt_data.append([ele for ele in data])
            # print(base_rt_data)

            # 遍历所有文件的数据，丰富基准RT列表，得到最终处理结果列表
            for idx in range(1, len(processed_results)):
                # 建立副本，每次处理一个文件，基准列表均会发生变化
                base_temp = copy.deepcopy(base_rt_data)
                # 记录当前文件处理结束后，基准列表元素最终长度
                result_len = len(base_temp[0]) + 1

                # 对单个文件的数据进行判断
                for data in processed_results[idx]["data"]:
                    match_stack = []    # 数据匹配栈
                    flag = False        # 标志当前文件中数据是否处理
                    for base_idx in range(len(base_temp)):
                        # 情况1：如在基准列表的某一rt浮动范围内，且为同种化合物，即重复。在对应基准列表数据添加area数据
                        if (float(base_temp[base_idx][0]) + float_parameter) >= float(data[0]) >= (
                                float(base_temp[base_idx][0]) - float_parameter) and base_temp[base_idx][1] == data[1]:
                            # 特殊情况：单个文件内存在多条数据与基准数据匹配，仅存储第一次匹配到的数据。
                            if len(base_temp[base_idx]) == result_len:
                                flag = True
                                break
                            # 在对应数据列表添加area数据
                            base_temp[base_idx].append(data[-1])
                            # 当前数据已处理，结束
                            flag = True
                            break
                        # 情况2：如在基准列表的某一rt浮动范围内但不为同种化合物，入数据匹配栈（可能后续有符合情况1的基准数据）
                        if (float(base_temp[base_idx][0]) + float_parameter) >= float(data[0]) >= (
                                float(base_temp[base_idx][0]) - float_parameter) and base_temp[base_idx][1] != data[1]:
                            # 将当前数据对应情况2的基准数据索引入栈
                            match_stack.append(base_idx)

                    # 当前数据未处理
                    if not flag:
                        # 数据匹配栈非空，即栈中数据为新基准数据
                        if len(match_stack) != 0:
                            # 此前文件对应数据均为ND
                            for i in range(0, idx):
                                data.insert(-1, "ND")
                            # 添加到对应基准列表数据之后
                            base_temp.insert(match_stack[0] + 1, data)
                        # 不在基准列表的任一rt浮动范围内且数据匹配栈为空，添加到基准列表
                        else:
                            # 此前文件对应数据均为ND
                            for i in range(0, idx):
                                data.insert(-1, "ND")
                            # 添加到基准列表末尾
                            base_temp.append(data)

                # 当前文件数据判断结束，处理基准列表中没有被重复的数据
                for data in base_temp:
                    if len(data) < result_len:
                        data.append("ND")

                # 单个文件处理结束后的基准列表
                base_rt_data = copy.deepcopy(base_temp)

            # for data_idx in range(0, len(base_rt_data)):
            #     print(data_idx, base_rt_data[data_idx])
            # print(len(base_rt_data))

            # 将最终结果按照rt从小到大排序
            base_rt_data.sort(key=lambda x: float(x[0]))
            # 最终处理结果列表
            processed_total_result = copy.deepcopy(base_rt_data)
            # 补充表头，processed_total_result[0]
            head = ["RT", "CompoundName", "CAS", "Molecular Formula", "SI", "RSI"]
            for file_obj in processed_results:
                head.append(file_obj["file_name"])
            processed_total_result.insert(0, head)

            # for file_obj in processed_results_temp:
            #     print(file_obj["data"])
            #     print("##########")
            # print("----------")
            # for data in processed_total_result:
            #     print(data)
            # print(len(processed_total_result))

            # 将processed_results_temp和processed_total_result转换为字典
            single_result_head = ["RT", "CompoundName", "CAS", "Molecular Formula", "SI", "RSI", "Area"]
            for file_obj in processed_results_temp:
                file_obj["data"] = [
                    {single_result_head[i]: value for i, value in enumerate(item)}
                    for item in file_obj["data"]
                ]

            total_result_head = processed_total_result[0]           # 获取表头
            processed_total_result = processed_total_result[1:]     # 去除表头元素
            processed_total_result = [
                {total_result_head[i]: value for i, value in enumerate(item)}
                for item in processed_total_result
            ]

            # 将处理结果保存至数据库
            Gcms_UserFiles.objects.create(process_id=process_id, user=user, file_type="gcms-thermo", single_file_json=processed_results_temp, total_file_json=processed_total_result)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "服务器处理异常",
                "detail": str(e)
            }, status=500)

        return Response({
            "status": "completed",
            "total_files": len(processed_results),
            "single_results": processed_results_temp,
            "total_result": processed_total_result
        })
