import copy
import re

import xlrd3 as xlrd
from celery import shared_task
from .models import Lc_UserFiles
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task(bind=True)
def process_lc_shimazu_files(self, file_contents_list, user_id, process_id, float_parameter):
    """
    异步处理LC_shimazu文件的Celery任务，在后台进行
    :param self: 任务实例（Celery提供）
    :param file_contents_list: 文件内容列表
    :param user_id: 用户ID
    :param process_id: 处理ID
    :param float_parameter: RT浮动参数
    :return: 处理结果
    """
    try:
        # 获取用户对象
        user = User.objects.get(uuid=user_id)

        # 处理结果列表
        processed_results = []
        total_files = len(file_contents_list)

        # 遍历处理每个文件
        for index, file_content in enumerate(file_contents_list, 1):
            file_name = file_content['name']
            file_data = file_content['content']

            # 记录单个文件状态
            file_result = {
                "file_name": file_name,
                "status": "success",
                "data": [],
                "errors": []
            }

            try:
                # 读取Excel内容
                file_data_bytes = bytes.fromhex(file_data)  # 将十六进制字符串转回二进制
                workbook = xlrd.open_workbook(file_contents=file_data_bytes)
                sheets = workbook.sheet_names()
                # 仅处理一个sheet，即内容不为空的那个
                worksheet = workbook.sheet_by_index(0)
                for sheet in sheets:
                    process_sheet = workbook.sheet_by_name(sheet)
                    if process_sheet.nrows != 0:
                        worksheet = process_sheet
                        break

                # 数据处理核心逻辑

                # 获得待处理的数据对象
                file_pda = []  # 单个文件中波长
                file_data = []  # 单个文件中待处理数据
                head_index = {}  # 表头索引

                table_temp = []  # 辅助变量，临时存储提取的数据
                flag = False  # 标志变量
                for row_idx in range(0, worksheet.nrows):
                    table_row = []
                    flag_cell = worksheet.cell(row_idx, 0)
                    # 从[Peak Table]区域开始提取
                    if flag is False and re.match("^\[Peak Table.*\]$", str(flag_cell.value)):
                        file_pda.append(flag_cell.value)  # 记录波长
                        flag = True
                    # 获取指定表头索引
                    if flag and re.match("^Peak#$", str(flag_cell.value)):
                        head_row = worksheet.row_values(row_idx)
                        head_index = {
                            "RT": head_row.index("R.Time"),
                            "Area": head_row.index("Area")
                        }
                    # 提取暂停（存储当前波长的数据）
                    if flag and flag_cell.value == "":
                        flag = False
                        file_data.append(table_temp)
                        table_temp = []  # 清空辅助变量，存储下一个波长数据
                    # 仅提取有效数据
                    if flag and re.match("[0-9]+\.[0-9]+", str(worksheet.cell(row_idx, 1).value)) and re.match(
                            "[0-9]+\.[0-9]+", str(worksheet.cell(row_idx, 2).value)):
                        row = worksheet.row_values(row_idx)
                        for key, value in head_index.items():
                            table_row.append(row[value])
                        if len(table_row) != 0:
                            table_temp.append(table_row)

                # 单个文件待处理数据集合
                file_result["pda"] = file_pda
                file_result["data"] = file_data
            except Exception as e:
                file_result["errors"].append(str(e))

            # 处理过程中更新处理进度，供前端查询任务状态时返回
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': index,  # 当前处理文件索引
                    'total_files': total_files,  # 总文件数
                    'file_name': file_name,  # 当前处理文件名
                    'status': file_result["status"]  # 当前处理文件状态
                }
            )
            # ↑ 进度信息存入Redis，作为Result Backend的缓存

            # 添加单个文件的待处理数据对象
            processed_results.append(file_result)

        # ↑ 文件处理结束，整合所有待处理数据（注意缩进！）

        # for pda in processed_results[0]["data"]:
        #     for data in pda:
        #         print(data)
        #     print("---")

        # 下面的逻辑会修改processed_results，故最终返回当前副本
        processed_results_temp = copy.deepcopy(processed_results)

        # 整合所有待处理数据

        # 获取基准RT列表（包括[rt,area])
        base_rt_data = []
        # 以第一个文件的数据为基准
        for pda in processed_results[0]["data"]:
            base_rt_data.append([ele for ele in pda])

        # for pda in base_rt_data:
        #     for data in pda:
        #         print(data)
        #     print(len(pda))
        #     print("----")

        # 遍历所有文件的数据，丰富基准RT列表，得到最终处理结果列表
        for idx in range(1, len(processed_results)):
            # 建立副本，每次处理一个文件，基准列表均会发生变化
            base_temp = copy.deepcopy(base_rt_data)
            # 对单个文件的数据进行判断
            for pda_idx in range(0, len(processed_results[idx]["data"])):
                # 记录当前波长处理结束后，基准列表元素最终长度
                result_len = len(base_temp[pda_idx][0]) + 1
                # 单个文件内多个波长，挨个处理
                for data in processed_results[idx]["data"][pda_idx]:
                    flag = False  # 标志当前文件中数据是否处理
                    # 波长索引对应基准数据列表索引
                    for base_pda in base_temp[pda_idx]:
                        # 如在基准列表的某一rt浮动范围内，即重复。在对应基准列表数据添加area数据
                        if (base_pda[0] + float_parameter) >= data[0] >= (base_pda[0] - float_parameter):
                            # 特殊情况：单个文件内存在多条数据与基准数据匹配，仅存储第一次匹配到的数据。
                            if len(base_pda) == result_len:
                                flag = True
                                break
                            # 在对应数据列表添加area数据
                            base_pda.append(data[-1])
                            # 当前数据已处理，结束
                            flag = True
                            break
                    # 不在基准列表的任一rt浮动范围内，添加到基准列表
                    if not flag:
                        for i in range(0, idx):
                            data.insert(-1, "ND")
                        # 添加到基准列表末尾
                        base_temp[pda_idx].append(data)

                # 当前波长数据判断结束，处理基准列表中没有被重复的数据
                for data in base_temp[pda_idx]:
                    if len(data) < result_len:
                        data.append("ND")

            # 单个文件处理结束后的基准列表
            base_rt_data = copy.deepcopy(base_temp)

        # for pda in base_rt_data:
        #     for data in pda:
        #         print(data)
        #     print("----")
        # print(len(base_rt_data))

        # 将最终结果按照rt从小到大排序
        for pda in base_rt_data:
            pda.sort(key=lambda x: x[0])
        # 整合后的数据
        processed_total_result = copy.deepcopy(base_rt_data)
        # 补充表头，processed_total_result[0]
        for pda in processed_total_result:
            pda.insert(0, ["RT"])
            for file_obj in processed_results:
                pda[0].append(file_obj["file_name"])

        # for file_obj in processed_results_temp:
        #     for pda in file_obj["data"]:
        #         print(pda)
        #     print("---")
        # for pda in processed_total_result:
        #     for data in pda:
        #         print(data)
        #     print("----")

        # 将processed_results_temp和processed_total_result转换为字典
        single_result_head = ["RT", "Area"]
        for file_obj in processed_results_temp:
            for pda_idx in range(len(file_obj["data"])):
                # 源数据
                origin_data = file_obj["data"][pda_idx]
                # 转换后数据
                transform_data = [
                    {single_result_head[i]: value for i, value in enumerate(item)}
                    for item in origin_data
                ]
                file_obj["data"][pda_idx] = transform_data

        total_result_head = processed_total_result[0][0]  # 获取表头
        for pda_idx in range(len(processed_total_result)):
            # 去除表头元素
            processed_total_result[pda_idx] = processed_total_result[pda_idx][1:]
            # 源数据
            origin_data = processed_total_result[pda_idx]
            # 转换后数据
            transform_data = [
                {total_result_head[i]: value for i, value in enumerate(item)}
                for item in origin_data
            ]
            processed_total_result[pda_idx] = transform_data

        # 将处理结果保存至数据库
        Lc_UserFiles.objects.create(
            process_id=process_id,
            user=user,
            file_type="lc-shimazu-lc30&lc2030",
            single_file_json=processed_results_temp,
            total_file_json=processed_total_result
        )

        # 处理完成，保存结果，存入Redis
        return {
            "status": "completed",
            "total_files": total_files,
            "single_results": processed_results_temp,
            "total_result": processed_total_result
        }

    except Exception as e:
        # 保存原始异常的类型和消息
        original_exc_type = type(e).__name__
        error_message = str(e)
        
        self.update_state(state='FAILURE', meta={
            'error': error_message,
            'exc_type': original_exc_type,
            'exc_message': error_message
        })
        # 直接重新抛出原始异常
        raise


@shared_task(bind=True)
def process_lc_agilent_files(self, file_contents_list, user_id, process_id, float_parameter):
    """
    异步处理LC_agilent文件的Celery任务，在后台进行
    :param self: 任务实例（Celery提供）
    :param file_contents_list: 文件内容列表
    :param user_id: 用户ID
    :param process_id: 处理ID
    :param float_parameter: RT浮动参数
    :return: 处理结果
    """
    try:
        # 获取用户对象
        user = User.objects.get(uuid=user_id)

        # 处理结果列表
        processed_results = []
        total_files = len(file_contents_list)

        # 遍历处理每个文件
        for index, file_content in enumerate(file_contents_list, 1):
            file_name = file_content['name']
            file_data = file_content['content']

            # 记录单个文件状态
            file_result = {
                "file_name": file_name,
                "status": "success",
                "data": [],
                "errors": []
            }

            try:
                # 读取Excel内容
                file_data_bytes = bytes.fromhex(file_data)  # 将十六进制字符串转回二进制
                workbook = xlrd.open_workbook(file_contents=file_data_bytes)
                sheets = workbook.sheet_names()
                # 仅处理一个sheet，即内容不为空的那个
                worksheet = workbook.sheet_by_index(0)
                for sheet in sheets:
                    process_sheet = workbook.sheet_by_name(sheet)
                    if process_sheet.nrows != 0:
                        worksheet = process_sheet
                        break

                # 数据处理核心逻辑

                # 获得待处理的数据对象
                file_data = []  # 单个文件中待处理数据
                start_idx = 0  # 待处理数据开始的列索引
                flag = False  # 标志变量，标志开始提取数据
                for row_idx in range(0, worksheet.nrows):
                    row = worksheet.row_values(row_idx)
                    if not all(item == "" for item in row):
                        # 获取数据开始列索引
                        for col in range(0, len(row)):
                            if row[col] != "":
                                start_idx = col
                                break
                        flag = True
                    if flag:
                        # 提取数据，仅包括[rt, area]，需求规定第二列为rt，第四列为area
                        row_temp = row[start_idx:]
                        file_data.append([row_temp[1], row_temp[3]])
                    # 区域终止
                    if flag and all(item == "" for item in row):
                        flag = False

                # for data in file_data:
                #     print(data)
                # print("------")

                # 单个文件待处理数据集合
                file_result["data"] = file_data
            except Exception as e:
                file_result["errors"].append(str(e))

            # 处理过程中更新处理进度，供前端查询任务状态时返回
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': index,                   # 当前处理文件索引
                    'total_files': total_files,         # 总文件数
                    'file_name': file_name,             # 当前处理文件名
                    'status': file_result["status"]     # 当前处理文件状态
                }
            )
            # ↑ 进度信息存入Redis，作为Result Backend的缓存

            # 添加单个文件的待处理数据对象
            processed_results.append(file_result)

        # ↑ 文件处理结束，整合所有待处理数据（注意缩进！）

        # 下面的逻辑会修改processed_results，故最终返回当前副本
        processed_results_temp = copy.deepcopy(processed_results)

        # 获取基准RT列表（包括[rt,area])
        base_rt_data = []
        # 以第一个文件的数据为基准
        for data in processed_results[0]["data"]:
            base_rt_data.append([ele for ele in data])

        # for data in base_rt_data:
        #     print(data)
        # print("------")

        # 遍历所有文件的数据，丰富基准RT列表，得到最终处理结果列表
        for idx in range(1, len(processed_results)):
            # 建立副本，每次处理一个文件，基准列表均会发生变化
            base_temp = copy.deepcopy(base_rt_data)
            # 记录当前文件处理结束后，基准列表元素最终长度
            result_len = len(base_temp[0]) + 1
            # 对单个文件的数据进行判断
            for data in processed_results[idx]["data"]:
                flag = False  # 标志当前文件中数据是否处理
                for base_data in base_temp:
                    # 如在基准列表的某一rt浮动范围内，即重复。在对应基准列表数据添加area数据
                    if (base_data[0] + float_parameter) >= data[0] >= (base_data[0] - float_parameter):
                        # 特殊情况：单个文件内存在多条数据与基准数据匹配，仅存储第一次匹配到的数据。
                        if len(base_data) == result_len:
                            flag = True
                            break
                        # 在对应数据列表添加area数据
                        base_data.append(data[-1])
                        # 当前数据已找到重复数据，结束
                        flag = True
                        break
                # 不在基准列表的任一rt浮动范围内，添加到基准列表
                if not flag:
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

        # for data in base_rt_data:
        #     print(data)
        # print(len(base_rt_data))

        # 将最终结果按照rt从小到大排序
        base_rt_data.sort(key=lambda x: x[0])

        # 整合后的数据
        processed_total_result = copy.deepcopy(base_rt_data)
        # 补充表头，processed_total_result[0]
        processed_total_result.insert(0, ["RT"])
        for file_obj in processed_results:
            processed_total_result[0].append(file_obj["file_name"])

        # for file_obj in processed_results_temp:
        #     print(file_obj["data"])
        #     print("##########")
        # for data in processed_total_result:
        #     print(data)
        # print(len(processed_total_result))

        # 将processed_results_temp和processed_total_result转换为字典
        single_result_head = ["RT", "Area"]
        for file_obj in processed_results_temp:
            file_obj["data"] = [
                {single_result_head[i]: value for i, value in enumerate(item)}
                for item in file_obj["data"]
            ]

        total_result_head = processed_total_result[0]  # 获取表头
        processed_total_result = processed_total_result[1:]  # 去除最终结果的表头
        processed_total_result = [
            {total_result_head[i]: value for i, value in enumerate(item)}
            for item in processed_total_result
        ]

        # 将处理结果保存至数据库
        Lc_UserFiles.objects.create(
            process_id=process_id,
            user=user,
            file_type="lc-ajl-1290",
            single_file_json=processed_results_temp,
            total_file_json=processed_total_result
        )

        # 处理完成，保存结果，存入Redis
        return {
            "status": "completed",
            "total_files": total_files,
            "single_results": processed_results_temp,
            "total_result": processed_total_result
        }

    except Exception as e:
        # 保存原始异常的类型和消息
        original_exc_type = type(e).__name__
        error_message = str(e)
        
        self.update_state(state='FAILURE', meta={
            'error': error_message,
            'exc_type': original_exc_type,
            'exc_message': error_message
        })
        # 直接重新抛出原始异常
        raise
