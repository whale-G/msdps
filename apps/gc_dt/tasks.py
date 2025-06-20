import datetime
import xlrd3 as xlrd
from celery import shared_task
from .models import Gc_UserFiles
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task(bind=True)
def process_gc_files(self, file_contents_list, user_id, process_id):
    """
    异步处理GC文件的Celery任务
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
                workbook = xlrd.open_workbook(file_contents=file_data)
                
                # 获取指定sheet的数据
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
                        file_result["data"].append(table_row)
                        
            except Exception as e:
                file_result["status"] = "error"
                file_result["errors"].append(str(e))
            
            # 更新处理进度
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': index,
                    'total': total_files,
                    'file_name': file_name,
                    'status': file_result["status"]
                }
            )
            
            processed_results.append(file_result)
        
        # 获取基准列表（segName）
        base_data = []
        for data in processed_results[0]["data"]:
            base_data.append(data[0])  # 第一列为segName
            
        for idx in range(1, len(processed_results)):
            for data in processed_results[idx]["data"]:
                if data[0] not in base_data:
                    base_data.append(data[0])
        
        # 根据基准列表填充Area和PPM
        processed_total_result = [base_data[i:i+1] for i in range(len(base_data))]
        
        # 填充数据
        for seg_idx in range(len(base_data)):
            for idx in range(len(processed_results)):
                flag = False
                for data in processed_results[idx]["data"]:
                    if base_data[seg_idx] in data:
                        processed_total_result[seg_idx].append(data[1])  # Area
                        processed_total_result[seg_idx].append(data[2])  # PPM
                        flag = True
                        break
                if not flag:
                    processed_total_result[seg_idx].extend(["ND", "ND"])
        
        # 转换为字典格式
        result = []
        total_result_head = ["segName"] + [f["file_name"] for f in processed_results]
        total_result_subHead = ["Area", "PPM"]
        
        for data in processed_total_result:
            main_dict = {total_result_head[0]: data[0]}
            for idx in range(1, len(total_result_head)):
                data_idx = idx * 2 - 1
                main_dict[total_result_head[idx]] = {
                    total_result_subHead[0]: data[data_idx],
                    total_result_subHead[1]: data[data_idx + 1]
                }
            result.append(main_dict)
        
        # 保存到数据库
        Gc_UserFiles.objects.create(
            process_id=process_id,
            user=user,
            file_type="gc-ajl-7890",
            single_file_json=processed_results,
            total_file_json=result
        )
        
        return {
            "status": "completed",
            "total_files": total_files,
            "single_results": processed_results,
            "total_result": result
        }
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise 