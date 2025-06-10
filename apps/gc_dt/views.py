from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

import datetime
import xlrd3 as xlrd
from .models import Gc_UserFiles


class GcProcess(APIView):
    parser_classes = [MultiPartParser, FormParser]

    # 安捷伦气相7890
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
        current_time_str = str(current_time.year) + str(current_time.month) + str(current_time.day) + str(current_time.hour) + str(current_time.minute) + str(current_time.second)
        process_id = str(uuid) + current_time_str + "gc"
        # 获取所有上传文件对象
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            return Response({"status": "error", "message": "未检测到文件"}, status=400)

        try:
            # 处理结果
            processed_results = []
            # 遍历处理每个文件
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
                    # 需求仅需要这个sheet的内容
                    worksheet = workbook.sheet_by_name("PeakSumCalcT")
                    if worksheet.nrows != 0:
                        # 获取指定表头的索引
                        head_row = worksheet.row_values(0)
                        head_index = {
                            "segName": head_row.index("segName"),
                            "Area": head_row.index("Area"),
                            "PPM": head_row.index("PPM")
                        }
                        for i in range(1, worksheet.nrows):
                            table_row = []
                            table_row.append(worksheet.cell_value(i, head_index["segName"]))
                            table_row.append(worksheet.cell_value(i, head_index["Area"]))
                            table_row.append(worksheet.cell_value(i, head_index["PPM"]))
                            file_data.append(table_row)
                        file_result["data"] = file_data

                except Exception as e:
                    file_result["errors"].append({
                        "error": str(e)
                    })

                # 添加单个文件的待处理数据对象
                processed_results.append(file_result)

            # 文件处理结束

            # 获取基准列表（segName）
            base_data = []
            for data in processed_results[0]["data"]:
                # 第一列为segName
                base_data.append(data[0])
            for idx in range(1, len(processed_results)):
                for data in processed_results[idx]["data"]:
                    # 添加不在基准列表中的segName
                    if data[0] not in base_data:
                        base_data.append(data[0])
            # 根据基准列表填充Area和PPM
            processed_total_result = [base_data[i:i+1] for i in range(0, len(base_data), 1)]  # 最终处理结果
            # print(processed_total_result)
            # 遍历处理基准列表中每一个元素，填充需要的数据
            for seg_idx in range(0, len(base_data)):
                # 遍历文件处理结果
                for idx in range(0, len(processed_results)):
                    flag = False    # 标志当前文件中是否检测到数据
                    for data in processed_results[idx]["data"]:
                        if base_data[seg_idx] in data:
                            processed_total_result[seg_idx].append(data[1])     # Area
                            processed_total_result[seg_idx].append(data[2])     # PPM
                            flag = True
                            break   # 仅填充一次
                    if not flag:
                        # 未检测到数据
                        processed_total_result[seg_idx].append("ND")
                        processed_total_result[seg_idx].append("ND")

            # for file in processed_results:
            #     print(file["data"])
            #     print("##########")
            # print("--------")
            # for data in processed_total_result:
            #     print(data)

            # 将processed_results和processed_total_result转换为字典列表
            single_result_head = ["segName", "Area", "PPM"]
            for file_obj in processed_results:
                file_obj["data"] = [
                    {single_result_head[i]: value for i, value in enumerate(item)}
                    for item in file_obj["data"]
                ]

            total_result_head = ["segName"]
            for file_obj in processed_results:
                total_result_head.append(file_obj["file_name"])
            total_result_subHead = ["Area", "PPM"]
            result = []
            file_count = len(total_result_head[1:])     # 文件数量
            for data in processed_total_result:
                main_dict = {total_result_head[0]: data[0]}     # 创建主字典
                for idx in range(1, file_count + 1):
                    data_idx = idx * 2 - 1      # 在data列表中的索引
                    main_dict[total_result_head[idx]] = {
                        total_result_subHead[0]: data[data_idx],        # Area
                        total_result_subHead[1]: data[data_idx + 1]     # PPM
                    }
                    result.append(main_dict)
            processed_total_result = result

            # 将处理结果保存至数据库
            Gc_UserFiles.objects.create(process_id=process_id, user=user, file_type="gc-ajl-7890", single_file_json=processed_results, total_file_json=processed_total_result)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "服务器处理异常",
                "detail": str(e)
            }, status=500)

        return Response({
            "status": "completed",
            "total_files": len(uploaded_files),
            "single_results": processed_results,
            "total_result": processed_total_result
        })
