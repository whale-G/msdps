import xlrd3 as xlrd
from celery import shared_task
from .models import Gc_UserFiles
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task(bind=True)
def process_gc_files(self, file_contents_list, user_id, process_id):
    """
    异步处理GC文件的Celery任务，在后台进行
    :param self: 任务实例（Celery提供）
    :param file_contents_list: 文件内容列表
    :param user_id: 用户ID
    :param process_id: 处理ID
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

                # 数据处理核心逻辑

                wait_process_data = []  # 单个文件中待处理数据
                # 获取指定sheet的数据（根据需求文档，sheet名称为PeakSumCalcT）
                worksheet = workbook.sheet_by_name("PeakSumCalcT")
                if worksheet.nrows != 0:
                    # 获取表头索引
                    head_row = worksheet.row_values(0)
                    head_index = {
                        "segName": head_row.index("segName"),
                        "Area": head_row.index("Area"),
                        "PPM": head_row.index("PPM")
                    }
                    
                    # 提取数据
                    for i in range(1, worksheet.nrows):
                        table_row = []
                        table_row.append(worksheet.cell_value(i, head_index["segName"]))
                        table_row.append(worksheet.cell_value(i, head_index["Area"]))
                        table_row.append(worksheet.cell_value(i, head_index["PPM"]))
                        wait_process_data.append(table_row)
                    file_result["data"] = wait_process_data
                        
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
        
        # ↑ 文件处理结束（注意缩进!）

        # 获取基准列表（segName）
        base_data = []
        for data in processed_results[0]["data"]:
            base_data.append(data[0])  # 第一列为segName
            
        for idx in range(1, len(processed_results)):
            for data in processed_results[idx]["data"]:
                # 如果数据中segName不在基准列表中，则添加到基准列表
                if data[0] not in base_data:
                    base_data.append(data[0])
        
        # 根据基准列表填充Area和PPM
        processed_total_result = [base_data[i:i+1] for i in range(0, len(base_data), 1)]
        # print(processed_total_result)

        # 遍历处理基准列表中每一个元素，填充需要的数据
        for seg_idx in range(len(base_data)):
            # 遍历文件处理结果
            for idx in range(len(processed_results)):
                flag = False    # 标志当前文件中是否检测到数据
                for data in processed_results[idx]["data"]:
                    if base_data[seg_idx] in data:
                        processed_total_result[seg_idx].append(data[1])  # Area
                        processed_total_result[seg_idx].append(data[2])  # PPM
                        flag = True
                        break   # 找到数据后，跳出当前文件结果的遍历，即仅填充一次
                if not flag:
                    processed_total_result[seg_idx].extend(["ND", "ND"])
        
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
        file_count = len(total_result_head[1:])             # 文件数量
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
        
        # 保存到数据库
        Gc_UserFiles.objects.create(
            process_id=process_id,
            user=user,
            file_type="gc-ajl-7890",
            single_file_json=processed_results,
            total_file_json=processed_total_result
        )
        
        # 处理完成，保存结果，存入Redis
        return {
            "status": "completed",
            "total_files": total_files,
            "single_results": processed_results,
            "total_result": processed_total_result
        }
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
