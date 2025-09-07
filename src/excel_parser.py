import pandas as pd


class ExcelParser:
    """Excel文件解析器，用于导入测试用例"""
    
    @staticmethod
    def parse_excel(file_path):
        """
        解析Excel文件，提取测试用例数据
        
        Args:
            file_path: Excel文件路径
            
        Returns:
            list: 包含测试用例数据的列表，每个元素是一个字典
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            # 检查必要的列是否存在
            required_columns = ['用例ID', '测试场景', '预期结果']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Excel文件缺少必要的列: {', '.join(missing_columns)}")
            
            # 将DataFrame转换为字典列表
            cases_data = df.fillna('').to_dict('records')
            
            # 验证用例ID的唯一性
            case_ids = [case.get('用例ID') for case in cases_data]
            if len(case_ids) != len(set(case_ids)):
                raise ValueError("Excel文件中存在重复的用例ID")
            
            return cases_data
            
        except Exception as e:
            raise Exception(f"解析Excel文件失败: {str(e)}")