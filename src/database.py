import os
import sqlite3
import json
from datetime import datetime
from typing import Optional


class Database:
    """数据库操作类，封装所有与SQLite数据库相关的操作"""
    
    def __init__(self, db_path='data/qa_test_logger.db'):
        """初始化数据库连接"""
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """连接到数据库"""
        self.conn = sqlite3.connect(self.db_path)
        # 设置行工厂以便返回字典形式的结果
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
    
    def create_tables(self):
        """创建必要的数据表"""
        # 创建测试用例表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_cases (
            case_id TEXT PRIMARY KEY,
            scenario TEXT NOT NULL,
            test_steps TEXT,
            expected_result TEXT NOT NULL,
            priority TEXT,
            case_collection_name TEXT
        )
        ''')
        
        # 创建测试记录表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            status TEXT NOT NULL,
            actual_result TEXT,
            notes TEXT,
            executor TEXT,
            timestamp INTEGER NOT NULL,
            FOREIGN KEY (case_id) REFERENCES test_cases(case_id)
        )
        ''')
        
        # 创建图片表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS record_images (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            FOREIGN KEY (record_id) REFERENCES test_records(record_id)
        )
        ''')
        
        self.conn.commit()
        
        # 检查是否需要迁移旧数据
        self._migrate_old_image_data()
        self._migrate_precondition_to_test_steps()
        self._migrate_add_case_collection_name()
    
    def _migrate_old_image_data(self):
        """迁移旧的图片数据到新表"""
        try:
            # 检查旧表中是否有image_path列
            self.cursor.execute("PRAGMA table_info(test_records)")
            columns = self.cursor.fetchall()
            has_image_path = any(col['name'] == 'image_path' for col in columns)
            
            if has_image_path:
                # 获取所有有图片的记录
                self.cursor.execute("SELECT record_id, image_path FROM test_records WHERE image_path IS NOT NULL AND image_path != ''")
                records = self.cursor.fetchall()
                
                for record in records:
                    record_id = record['record_id']
                    image_path = record['image_path']
                    
                    # 添加到新表
                    self.cursor.execute('''
                    INSERT INTO record_images (record_id, image_path, order_index)
                    VALUES (?, ?, ?)
                    ''', (record_id, image_path, 0))
                
                # 删除旧列
                self.cursor.execute("ALTER TABLE test_records DROP COLUMN image_path")
                self.conn.commit()
        except sqlite3.Error as e:
            print(f"迁移图片数据失败: {e}")

    def _migrate_precondition_to_test_steps(self):
        """将旧列 precondition 迁移为 test_steps，保留原列以兼容旧数据"""
        try:
            self.cursor.execute("PRAGMA table_info(test_cases)")
            columns = self.cursor.fetchall()
            has_pre = any(col['name'] == 'precondition' for col in columns)
            has_steps = any(col['name'] == 'test_steps' for col in columns)

            if not has_steps and has_pre:
                # 增加新列
                self.cursor.execute("ALTER TABLE test_cases ADD COLUMN test_steps TEXT")
                # 将旧数据复制到新列
                self.cursor.execute("UPDATE test_cases SET test_steps = precondition WHERE test_steps IS NULL")
                self.conn.commit()
        except sqlite3.Error as e:
            print(f"迁移前置条件到测试步骤失败: {e}")

    def _migrate_add_case_collection_name(self):
        """为 test_cases 表增加 case_collection_name 列（如缺失）"""
        try:
            self.cursor.execute("PRAGMA table_info(test_cases)")
            columns = self.cursor.fetchall()
            has_col = any(col['name'] == 'case_collection_name' for col in columns)
            if not has_col:
                self.cursor.execute("ALTER TABLE test_cases ADD COLUMN case_collection_name TEXT")
                self.conn.commit()
        except sqlite3.Error as e:
            print(f"添加案例集名称列失败: {e}")
    
    def import_test_cases(self, cases_data, case_collection_name: Optional[str] = None):
        """
        导入测试用例数据
        
        Args:
            cases_data: 包含测试用例数据的列表，每个元素是一个字典
            case_collection_name: 可选的案例集名称
        
        Returns:
            tuple: (成功导入的数量, 总数量)
        """
        success_count = 0
        total_count = len(cases_data)
        
        # 首先检查是否有已存在的案例，并获取其案例集名称
        existing_collection_name = None
        for case in cases_data:
            try:
                case_id = case.get('用例ID', '')
                self.cursor.execute('SELECT case_collection_name FROM test_cases WHERE case_id = ?', (case_id,))
                row = self.cursor.fetchone()
                if row and row['case_collection_name']:
                    existing_collection_name = row['case_collection_name']
                    break
            except sqlite3.Error:
                continue

        # 如果没有在参数中指定案例集名称，但找到了已存在案例的集名称，就使用已存在的
        final_collection_name = case_collection_name or existing_collection_name
        
        for case in cases_data:
            try:
                # 如果案例中自带案例集名称，优先使用案例中的
                case_specific_collection = case.get('案例集名称')
                
                self.cursor.execute('''
                INSERT OR REPLACE INTO test_cases 
                (case_id, scenario, test_steps, expected_result, priority, case_collection_name)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    case.get('用例ID', ''),
                    case.get('测试场景', ''),
                    (case.get('测试步骤') or case.get('前置条件') or ''),
                    case.get('预期结果', ''),
                    case.get('优先级', ''),
                    case_specific_collection or final_collection_name  # 优先使用案例自带的集名称，其次使用统一的集名称
                ))
                success_count += 1
            except sqlite3.Error as e:
                print(f"导入用例失败: {e}, 用例: {case}")
        
        self.conn.commit()
        return success_count, total_count
    
    def get_all_test_cases(self):
        """获取所有测试用例，兼容旧数据，将 test_steps 标准化"""
        self.cursor.execute('SELECT * FROM test_cases')
        rows = self.cursor.fetchall()
        normalized = []
        for row in rows:
            row_dict = dict(row)
            # 兼容：优先使用 test_steps，其次使用 precondition
            row_dict['test_steps'] = row_dict.get('test_steps') or row_dict.get('precondition') or None
            normalized.append(row_dict)
        return normalized
    
    def get_test_case(self, case_id):
        """获取指定ID的测试用例，兼容旧数据，将 test_steps 标准化"""
        self.cursor.execute('SELECT * FROM test_cases WHERE case_id = ?', (case_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        row_dict = dict(row)
        row_dict['test_steps'] = row_dict.get('test_steps') or row_dict.get('precondition') or None
        return row_dict
    
    def save_test_record(self, case_id, status, actual_result='', notes='', image_paths=None, executor=''):
        """
        保存测试执行记录
        
        Args:
            case_id: 测试用例ID
            status: 执行状态（通过、失败、阻塞、跳过）
            actual_result: 实际结果
            notes: 备注
            image_paths: 图片路径列表
            executor: 执行人
            
        Returns:
            int: 新记录的ID
        """
        timestamp = int(datetime.now().timestamp())
        
        self.cursor.execute('''
        INSERT INTO test_records 
        (case_id, status, actual_result, notes, executor, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (case_id, status, actual_result, notes, executor, timestamp))
        
        record_id = self.cursor.lastrowid
        
        # 保存图片路径
        if image_paths:
            for i, path in enumerate(image_paths):
                if path:
                    self.cursor.execute('''
                    INSERT INTO record_images (record_id, image_path, order_index)
                    VALUES (?, ?, ?)
                    ''', (record_id, path, i))
        
        self.conn.commit()
        return record_id
    
    def update_test_record(self, record_id, status=None, actual_result=None, notes=None, image_paths=None, executor=None):
        """
        更新测试记录
        
        Args:
            record_id: 记录ID
            status: 执行状态
            actual_result: 实际结果
            notes: 备注
            image_paths: 图片路径列表
            executor: 执行人
            
        Returns:
            bool: 是否更新成功
        """
        update_fields = []
        params = []
        
        if status is not None:
            update_fields.append("status = ?")
            params.append(status)
        
        if actual_result is not None:
            update_fields.append("actual_result = ?")
            params.append(actual_result)
        
        if notes is not None:
            update_fields.append("notes = ?")
            params.append(notes)
        
        if executor is not None:
            update_fields.append("executor = ?")
            params.append(executor)
        
        # 总是更新时间戳为当前时间
        update_fields.append("timestamp = ?")
        params.append(int(datetime.now().timestamp()))
        
        if update_fields:
            # 添加记录ID到参数列表
            params.append(record_id)
            
            query = f"UPDATE test_records SET {', '.join(update_fields)} WHERE record_id = ?"
            self.cursor.execute(query, params)
        
        # 更新图片
        if image_paths is not None:
            # 删除旧图片记录
            self.cursor.execute("DELETE FROM record_images WHERE record_id = ?", (record_id,))
            
            # 添加新图片记录
            for i, path in enumerate(image_paths):
                if path:
                    self.cursor.execute('''
                    INSERT INTO record_images (record_id, image_path, order_index)
                    VALUES (?, ?, ?)
                    ''', (record_id, path, i))
        
        self.conn.commit()
        return True
    
    def get_record_images(self, record_id):
        """
        获取记录的所有图片
        
        Args:
            record_id: 记录ID
            
        Returns:
            list: 图片路径列表，按顺序排列
        """
        self.cursor.execute('''
        SELECT image_path FROM record_images 
        WHERE record_id = ? 
        ORDER BY order_index
        ''', (record_id,))
        
        return [row['image_path'] for row in self.cursor.fetchall()]
    
    def get_test_records(self, case_id=None, status=None, start_date=None, end_date=None):
        """
        获取测试记录，支持多种筛选条件
        
        Args:
            case_id: 可选，按用例ID筛选
            status: 可选，按状态筛选
            start_date: 可选，开始日期（时间戳）
            end_date: 可选，结束日期（时间戳）
            
        Returns:
            list: 测试记录列表
        """
        query = "SELECT * FROM test_records"
        conditions = []
        params = []
        
        if case_id:
            conditions.append("case_id = ?")
            params.append(case_id)
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC"
        
        self.cursor.execute(query, params)
        records = self.cursor.fetchall()
        
        # 转换为可修改的字典列表
        result = []
        for record in records:
            record_dict = dict(record)
            # 添加图片路径
            record_dict['images'] = self.get_record_images(record['record_id'])
            result.append(record_dict)
        
        return result
    
    def get_test_record(self, record_id):
        """获取指定ID的测试记录"""
        self.cursor.execute('SELECT * FROM test_records WHERE record_id = ?', (record_id,))
        record = self.cursor.fetchone()
        
        if record:
            # 转换为可修改的字典
            record_dict = dict(record)
            # 添加图片路径
            record_dict['images'] = self.get_record_images(record_id)
            return record_dict
        
        return None
    
    def get_statistics(self, start_date=None, end_date=None):
        """
        获取测试统计信息
        
        Args:
            start_date: 可选，开始日期（时间戳）
            end_date: 可选，结束日期（时间戳）
            
        Returns:
            dict: 包含统计信息的字典
        """
        conditions = []
        params = []
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 获取总记录数
        query = f"SELECT COUNT(*) as total FROM test_records{where_clause}"
        self.cursor.execute(query, params)
        total = self.cursor.fetchone()['total']
        
        # 获取各状态的记录数
        stats = {'total': total, '通过': 0, '失败': 0, '阻塞': 0, '跳过': 0}
        
        for status in ['通过', '失败', '阻塞', '跳过']:
            status_params = params.copy()
            status_conditions = conditions.copy()
            status_conditions.append("status = ?")
            status_params.append(status)
            
            status_where = " WHERE " + " AND ".join(status_conditions) if status_conditions else ""
            query = f"SELECT COUNT(*) as count FROM test_records{status_where}"
            
            self.cursor.execute(query, status_params)
            stats[status] = self.cursor.fetchone()['count']
        
        # 计算通过率
        if total > 0:
            stats['通过率'] = (stats['通过'] / total) * 100
        else:
            stats['通过率'] = 0
        
        return stats

    def get_all_collection_names(self):
        """获取所有案例集名称列表（去重）"""
        try:
            self.cursor.execute('''
                SELECT DISTINCT case_collection_name AS name
                FROM test_cases
                WHERE case_collection_name IS NOT NULL AND case_collection_name != ''
                ORDER BY case_collection_name
            ''')
            rows = self.cursor.fetchall()
            return [row['name'] for row in rows]
        except sqlite3.Error:
            return []
    
    def get_latest_records(self):
        """
        获取每个测试用例的最新执行记录
        
        Returns:
            dict: 以用例ID为键，最新记录为值的字典
        """
        self.cursor.execute('''
        SELECT r.* FROM test_records r
        INNER JOIN (
            SELECT case_id, MAX(timestamp) as max_time
            FROM test_records
            GROUP BY case_id
        ) m ON r.case_id = m.case_id AND r.timestamp = m.max_time
        ''')
        
        records = self.cursor.fetchall()
        result = {}
        
        for record in records:
            record_dict = dict(record)
            record_dict['images'] = self.get_record_images(record['record_id'])
            result[record['case_id']] = record_dict
        
        return result
    
    def get_cases_by_collection(self, collection_name):
        """获取指定案例集的所有测试用例"""
        self.cursor.execute('SELECT * FROM test_cases WHERE case_collection_name = ?', (collection_name,))
        rows = self.cursor.fetchall()
        normalized = []
        for row in rows:
            row_dict = dict(row)
            # 兼容：优先使用 test_steps，其次使用 precondition
            row_dict['test_steps'] = row_dict.get('test_steps') or row_dict.get('precondition') or None
            normalized.append(row_dict)
        return normalized
    
    def delete_test_case(self, case_id):
        """
        删除测试用例及其所有相关记录
        
        Args:
            case_id: 要删除的测试用例ID
        """
        try:
            # 获取所有相关的测试记录ID
            self.cursor.execute('SELECT record_id FROM test_records WHERE case_id = ?', (case_id,))
            record_ids = [row['record_id'] for row in self.cursor.fetchall()]
            
            # 删除所有相关的图片记录
            for record_id in record_ids:
                self.cursor.execute('DELETE FROM record_images WHERE record_id = ?', (record_id,))
            
            # 删除所有相关的测试记录
            self.cursor.execute('DELETE FROM test_records WHERE case_id = ?', (case_id,))
            
            # 删除测试用例
            self.cursor.execute('DELETE FROM test_cases WHERE case_id = ?', (case_id,))
            
            self.conn.commit()
            
        except sqlite3.Error as e:
            self.conn.rollback()
            raise Exception(f"删除测试用例失败: {str(e)}")
    
    def delete_collection(self, collection_name):
        """
        删除整个测试集及其所有相关记录
        
        Args:
            collection_name: 要删除的案例集名称
        """
        try:
            # 获取该案例集中的所有用例ID
            self.cursor.execute('SELECT case_id FROM test_cases WHERE case_collection_name = ?', (collection_name,))
            case_ids = [row['case_id'] for row in self.cursor.fetchall()]
            
            # 删除每个用例及其相关记录
            for case_id in case_ids:
                self.delete_test_case(case_id)
            
        except sqlite3.Error as e:
            self.conn.rollback()
            raise Exception(f"删除测试集失败: {str(e)}")
    
    def export_test_records(self, start_date=None, end_date=None, case_id=None, status=None, collection_name=None, search_text=None):
        """
        导出测试记录数据
        
        Args:
            start_date: 可选，开始日期（时间戳）
            end_date: 可选，结束日期（时间戳）
            case_id: 可选，按用例ID筛选
            status: 可选，按状态筛选
            collection_name: 可选，按案例集名称筛选
            search_text: 可选，和历史界面一致的搜索逻辑（中文匹配场景，否则匹配用例ID）
            
        Returns:
            list: 包含完整测试记录数据的列表
        """
        # 获取筛选后的记录
        records = self.get_test_records(case_id, status, start_date, end_date)
        
        # 获取对应的测试用例详情
        result = []
        for record in records:
            case = self.get_test_case(record['case_id'])
            if not case:
                continue

            # 按案例集筛选
            if collection_name:
                if (case.get('case_collection_name') or '') != collection_name:
                    continue

            # 按搜索关键字筛选（与历史记录界面逻辑一致）
            if search_text:
                has_chinese = any('\u4e00' <= char <= '\u9fff' for char in search_text)
                if has_chinese:
                    if not case.get('scenario') or search_text.lower() not in case['scenario'].lower():
                        continue
                else:
                    if search_text.lower() not in record['case_id'].lower():
                        continue

            # 合并用例和记录数据
            export_data = {
                '用例ID': case['case_id'],
                '测试场景': case['scenario'],
                '测试步骤': case.get('test_steps'),
                '预期结果': case['expected_result'],
                '优先级': case['priority'],
                '执行状态': record['status'],
                '实际结果': record['actual_result'],
                '备注': record['notes'],
                '执行时间': record['timestamp'],
                '图片': record['images']
            }
            result.append(export_data)
        
        return result