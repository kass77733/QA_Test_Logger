from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QFileDialog, QSplitter,
    QHeaderView, QMessageBox, QSizePolicy, QComboBox, QDialog,
    QLineEdit, QFormLayout, QDialogButtonBox, QProgressDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
import requests
import json

from ui_execution import TestCaseExecutionWidget
from excel_parser import ExcelParser
from PyQt6.QtWidgets import QInputDialog, QPushButton
from utils import SettingsUtils


class ApiImportDialog(QDialog):
    """接口获取案例参数输入对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("接口获取案例")
        self.setModal(True)
        self.resize(300, 150)
        
        # 创建表单布局
        layout = QFormLayout(self)
        
        # 输入框
        self.project_id_edit = QLineEdit()
        self.subtask_name_edit = QLineEdit()
        self.round_edit = QLineEdit()
        
        layout.addRow("项目编号:", self.project_id_edit)
        layout.addRow("子任务名称:", self.subtask_name_edit)
        layout.addRow("轮次:", self.round_edit)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def get_params(self):
        """获取输入的参数"""
        return {
            'project_id': self.project_id_edit.text().strip(),
            'subtask_name': self.subtask_name_edit.text().strip(),
            'round': self.round_edit.text().strip()
        }


class TestCasesTab(QWidget):
    """测试用例标签页"""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.collection_imported = None  # 案例集导入回调函数
        self.initUI()
        # 默认进入时不加载任何用例，保持左侧空白
    
    def initUI(self):
        """初始化UI"""
        self.layout = QVBoxLayout(self)
        
        # 顶部按钮区域
        button_layout = QHBoxLayout()
        
        # 导入按钮
        self.import_button = QPushButton("导入Excel")
        self.import_button.clicked.connect(self.import_excel)
        button_layout.addWidget(self.import_button)
        
        # 接口获取案例按钮
        self.api_import_button = QPushButton("接口获取案例")
        self.api_import_button.clicked.connect(self.import_from_api)
        button_layout.addWidget(self.api_import_button)
        
        # 项目ID选择下拉框
        self.project_label = QLabel("选择项目ID:")
        button_layout.addWidget(self.project_label)
        
        self.project_combo = QComboBox()
        self.project_combo.addItem("-- 请选择项目ID --")
        self.project_combo.setFixedWidth(150)
        self.project_combo.currentTextChanged.connect(self.on_project_selected)
        button_layout.addWidget(self.project_combo)
        
        # 案例集选择下拉框
        self.collection_label = QLabel("选择案例集:")
        button_layout.addWidget(self.collection_label)
        
        self.collection_combo = QComboBox()
        self.collection_combo.addItem("-- 请选择案例集 --")
        self.collection_combo.setFixedWidth(200)
        self.collection_combo.currentTextChanged.connect(self.on_collection_selected)
        button_layout.addWidget(self.collection_combo)
        
        # 删除测试集按钮
        self.delete_collection_button = QPushButton("删除测试集")
        self.delete_collection_button.clicked.connect(self.delete_collection)
        button_layout.addWidget(self.delete_collection_button)
        
        # 清空列表按钮（仅UI清空，不删除数据库）
        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_cases_table)
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        self.layout.addLayout(button_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧用例列表
        self.cases_table = QTableWidget()
        self.cases_table.setColumnCount(5)
        self.cases_table.setHorizontalHeaderLabels(["用例ID", "测试场景", "测试步骤", "预期结果", "操作"])
        # 固定列宽，避免出现水平滚动条；刷新后保持
        header = self.cases_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        # 设置各列固定宽度（可按需微调）
        self.cases_table.setColumnWidth(0, 100)  # 用例ID
        self.cases_table.setColumnWidth(1, 100)  # 测试场景
        self.cases_table.setColumnWidth(2, 100)  # 测试步骤
        self.cases_table.setColumnWidth(3, 100)  # 预期结果
        self.cases_table.setColumnWidth(4, 40)   # 案例操作
        self.cases_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cases_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cases_table.itemClicked.connect(self.on_case_selected)
        splitter.addWidget(self.cases_table)

        # 左侧固定
        self.cases_table.setFixedWidth(455)

        # 右侧执行区固定宽度，并让内部控件自动换行
        self.execution_widget = TestCaseExecutionWidget(self.db)
        self.execution_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,  # 水平方向可扩展
            QSizePolicy.Policy.Expanding  # 垂直方向可扩展
        )

        # 设置分割器
        splitter.setStretchFactor(0, 0)  # 左侧固定
        splitter.setStretchFactor(1, 0)  # 右侧固定


        # 连接记录保存信号
        self.execution_widget.record_saved.connect(self.on_record_saved)
        splitter.addWidget(self.execution_widget)
        
        # 设置分割器初始大小
        splitter.setSizes([300, 500])
        
        self.layout.addWidget(splitter)
        
        # 在UI创建完成后加载数据
        self.refresh_project_combo()
        self.refresh_collection_combo()
    
    def load_test_cases(self):
        """加载测试用例列表"""
        try:
            cases = self.db.get_all_test_cases()
            
            # 获取所有已执行的测试用例ID及其状态
            executed_cases = {}
            try:
                records = self.db.get_latest_records()
                for case_id, record in records.items():
                    executed_cases[case_id] = record['status']
            except Exception as e:
                print(f"获取执行记录失败: {str(e)}")
            
            # 清空表格
            self.cases_table.setRowCount(0)
            
            # 填充数据
            for row, case in enumerate(cases):
                self.cases_table.insertRow(row)
                case_id = case['case_id']
                
                # 创建表格项
                id_item = QTableWidgetItem(case_id)
                scenario_item = QTableWidgetItem(case['scenario'])
                precondition_item = QTableWidgetItem((case.get('test_steps') or case.get('precondition') or ""))
                expected_item = QTableWidgetItem(case['expected_result'])
                
                # 创建删除按钮
                delete_button = QPushButton("删除")
                delete_button.clicked.connect(lambda checked, cid=case_id: self.delete_test_case(cid))
                delete_button.setMaximumWidth(50)
                
                # 如果是已执行的测试用例，设置背景色
                if case_id in executed_cases:
                    status = executed_cases[case_id]
                    # 根据状态设置不同的颜色
                    if status == "通过":
                        color = QColor(200, 255, 200)  # 浅绿色
                    elif status == "失败":
                        color = QColor(255, 200, 200)  # 浅红色
                    elif status == "阻塞":
                        color = QColor(255, 255, 200)  # 浅黄色
                    else:  # 跳过
                        color = QColor(200, 200, 255)  # 浅蓝色
                    
                    # 设置背景色
                    brush = QBrush(color)
                    id_item.setBackground(brush)
                    scenario_item.setBackground(brush)
                    precondition_item.setBackground(brush)
                    expected_item.setBackground(brush)
                    
                    # 存储最新记录ID，用于后续查询
                    id_item.setData(Qt.ItemDataRole.UserRole, records[case_id]['record_id'])
                
                # 添加到表格
                self.cases_table.setItem(row, 0, id_item)
                self.cases_table.setItem(row, 1, scenario_item)
                self.cases_table.setItem(row, 2, precondition_item)
                self.cases_table.setItem(row, 3, expected_item)
                self.cases_table.setCellWidget(row, 4, delete_button)
            
            # 不再自动调整列宽，保持固定设置
            
            # 打印加载成功消息
            if cases:
                print(f"已加载 {len(cases)} 条测试用例")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载测试用例失败: {str(e)}")
    
    def import_excel(self):
        """导入Excel文件"""
        # 打开文件对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Excel文件", "", "Excel文件 (*.xlsx *.xls)"
        )
        
        if not file_path:
            return
        
        try:
            # 解析Excel文件
            cases_data = ExcelParser.parse_excel(file_path)

            # 检查导入的案例情况
            existing = self.db.get_all_test_cases()
            existing_ids = set([row['case_id'] for row in existing])
            new_case_ids = [c.get('用例ID', '') for c in cases_data if c.get('用例ID')]
            existing_case_ids = [cid for cid in new_case_ids if cid in existing_ids]
            new_only_case_ids = [cid for cid in new_case_ids if cid not in existing_ids]
            
            collection_name = None
            
            # 如果有已存在的案例，获取其案例集名称
            if existing_case_ids:
                existing_case = self.db.get_test_case(existing_case_ids[0])
                if existing_case and existing_case.get('case_collection_name'):
                    collection_name = existing_case['case_collection_name']
            
            # 如果没有已存在的案例集名称，且有新案例，才询问用户
            if not collection_name and new_only_case_ids:
                text, ok = QInputDialog.getText(self, "案例集名称", "请输入本次导入的案例集名称：")
                if not ok:
                    return
                collection_name = text.strip() or None
                # 记录最近一次导入的集合名
                SettingsUtils.set_last_collection_name(collection_name)
            
            # 为所有案例设置案例集名称
            if collection_name:
                for c in cases_data:
                    c['案例集名称'] = collection_name
            
            # 导入数据库（传入collection_name以防Excel未写入对应列）
            success_count, total_count = self.db.import_test_cases(cases_data, collection_name)
            
            # 仅将本次导入的用例追加到当前表格（不全量刷新）
            imported_ids = [c.get('用例ID') for c in cases_data if c.get('用例ID')]
            new_cases = []
            for cid in imported_ids:
                case = self.db.get_test_case(cid)
                if case:
                    new_cases.append(case)
            self.add_cases_to_table(new_cases)
            
            # 如果导入了新的案例集，通知主窗口刷新历史记录界面的下拉框
            if collection_name and self.collection_imported:
                self.collection_imported()
            
            # 刷新项目ID和案例集下拉框
            self.refresh_project_combo()
            
            # 自动切换到对应的项目ID和案例集
            if collection_name and new_case_ids:
                # 获取项目ID（取第一个案例ID的前12位）
                project_id = new_case_ids[0][:12] if new_case_ids[0] else ''
                if project_id:
                    # 先切换项目ID
                    project_index = self.project_combo.findText(project_id)
                    if project_index >= 0:
                        self.project_combo.setCurrentIndex(project_index)
                    
                    # 再刷新和切换案例集
                    self.refresh_collection_combo(project_id)
                    collection_index = self.collection_combo.findText(collection_name)
                    if collection_index >= 0:
                        self.collection_combo.setCurrentIndex(collection_index)
            
            # 打印结果
            print(f"导入成功：已导入 {success_count}/{total_count} 条测试用例")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入Excel失败: {str(e)}")
    
    def on_case_selected(self, item):
        """处理用例选择事件"""
        # 每次点击左侧用例时，先重置右侧图片预览，避免保留上一次预览
        try:
            if hasattr(self.execution_widget, 'image_list'):
                self.execution_widget.image_list.setImages([])
        except Exception:
            pass
        row = item.row()
        id_item = self.cases_table.item(row, 0)
        case_id = id_item.text()
        
        # 获取用例详情
        case = self.db.get_test_case(case_id)
        
        # 检查是否有关联的执行记录
        record_id = id_item.data(Qt.ItemDataRole.UserRole)
        if record_id:
            # 获取执行记录详情
            record = self.db.get_test_record(record_id)
            if record:
                # 更新执行组件，显示历史记录
                self.execution_widget.set_test_case(case)
                self.execution_widget.load_record(record)
                return
        
        # 如果没有执行记录或获取失败，则正常显示用例
        self.execution_widget.set_test_case(case)
        # 选择新用例后，确保图片列表清空
        try:
            if hasattr(self.execution_widget, 'image_list'):
                self.execution_widget.image_list.setImages([])
        except Exception:
            pass
    
    def on_record_saved(self, record_id):
        """处理记录保存事件"""
        # 获取保存的记录
        record = self.db.get_test_record(record_id)
        if not record:
            return
            
        case_id = record['case_id']
        
        # 更新表格中对应的测试用例颜色
        for row in range(self.cases_table.rowCount()):
            id_item = self.cases_table.item(row, 0)
            if id_item and id_item.text() == case_id:
                # 设置记录ID
                id_item.setData(Qt.ItemDataRole.UserRole, record_id)
                
                # 设置背景色
                status = record['status']
                if status == "通过":
                    color = QColor(200, 255, 200)  # 浅绿色
                elif status == "失败":
                    color = QColor(255, 200, 200)  # 浅红色
                elif status == "阻塞":
                    color = QColor(255, 255, 200)  # 浅黄色
                else:  # 跳过
                    color = QColor(200, 200, 255)  # 浅蓝色
                
                # 设置所有列的背景色（跳过最后一列的删除按钮）
                brush = QBrush(color)
                for col in range(self.cases_table.columnCount() - 1):  # 跳过最后一列
                    cell_item = self.cases_table.item(row, col)
                    if cell_item:
                        cell_item.setBackground(brush)
                
                break

    def clear_cases_table(self):
        """仅清空左侧用例列表（不删除数据库数据）"""
        self.cases_table.setRowCount(0)

    def _get_displayed_case_ids(self):
        ids = set()
        for row in range(self.cases_table.rowCount()):
            item = self.cases_table.item(row, 0)
            if item:
                ids.add(item.text())
        return ids

    def add_cases_to_table(self, cases):
        """将给定用例列表追加到当前表格，避免重复并应用状态着色"""
        if not cases:
            return
        # 获取最新执行状态
        executed_cases = {}
        try:
            records = self.db.get_latest_records()
            for case_id, record in records.items():
                executed_cases[case_id] = record['status']
        except Exception as e:
            print(f"获取执行记录失败: {str(e)}")

        existing_ids = self._get_displayed_case_ids()
        for case in cases:
            case_id = case['case_id']
            if case_id in existing_ids:
                continue
            row = self.cases_table.rowCount()
            self.cases_table.insertRow(row)

            id_item = QTableWidgetItem(case_id)
            scenario_item = QTableWidgetItem(case['scenario'])
            precondition_item = QTableWidgetItem((case.get('test_steps') or case.get('precondition') or ""))
            expected_item = QTableWidgetItem(case['expected_result'])
            
            # 创建删除按钮
            delete_button = QPushButton("删除")
            delete_button.clicked.connect(lambda checked, cid=case_id: self.delete_test_case(cid))
            delete_button.setMaximumWidth(50)

            # 着色
            if case_id in executed_cases:
                status = executed_cases[case_id]
                if status == "通过":
                    color = QColor(200, 255, 200)
                elif status == "失败":
                    color = QColor(255, 200, 200)
                elif status == "阻塞":
                    color = QColor(255, 255, 200)
                else:
                    color = QColor(200, 200, 255)
                brush = QBrush(color)
                id_item.setBackground(brush)
                scenario_item.setBackground(brush)
                precondition_item.setBackground(brush)
                expected_item.setBackground(brush)
                # 记录最新记录ID，便于右侧反显结果
                try:
                    if case_id in records and 'record_id' in records[case_id]:
                        id_item.setData(Qt.ItemDataRole.UserRole, records[case_id]['record_id'])
                except Exception:
                    pass

            self.cases_table.setItem(row, 0, id_item)
            self.cases_table.setItem(row, 1, scenario_item)
            self.cases_table.setItem(row, 2, precondition_item)
            self.cases_table.setItem(row, 3, expected_item)
            self.cases_table.setCellWidget(row, 4, delete_button)
    
    def refresh_project_combo(self):
        """刷新项目ID下拉框"""
        current_text = self.project_combo.currentText()
        self.project_combo.clear()
        self.project_combo.addItem("-- 请选择项目ID --")
        
        project_ids = self.db.get_all_project_ids()
        for project_id in project_ids:
            self.project_combo.addItem(project_id)
        
        # 尝试恢复之前的选择
        index = self.project_combo.findText(current_text)
        if index >= 0:
            self.project_combo.setCurrentIndex(index)
    
    def refresh_collection_combo(self, project_id=None):
        """刷新案例集下拉框"""
        current_text = self.collection_combo.currentText()
        self.collection_combo.clear()
        self.collection_combo.addItem("-- 请选择案例集 --")
        
        if project_id and project_id != "-- 请选择项目ID --":
            collections = self.db.get_collections_by_project(project_id)
        else:
            collections = self.db.get_all_collection_names()
        
        for collection in collections:
            self.collection_combo.addItem(collection)
        
        # 尝试恢复之前的选择
        index = self.collection_combo.findText(current_text)
        if index >= 0:
            self.collection_combo.setCurrentIndex(index)
    
    def on_project_selected(self, project_id):
        """处理项目ID选择事件"""
        # 清空案例列表
        self.cases_table.setRowCount(0)
        
        # 刷新案例集下拉框
        self.refresh_collection_combo(project_id)
    
    def on_collection_selected(self, collection_name):
        """处理案例集选择事件"""
        if collection_name == "-- 请选择案例集 --" or not collection_name:
            return
        
        try:
            # 获取指定案例集的所有用例
            cases = self.db.get_cases_by_collection(collection_name)
            
            # 清空表格
            self.cases_table.setRowCount(0)
            
            # 添加用例到表格
            self.add_cases_to_table(cases)
            
            print(f"已加载案例集 '{collection_name}' 中的 {len(cases)} 个测试用例")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载案例集失败: {str(e)}")
    
    def delete_test_case(self, case_id):
        """删除测试用例"""
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除测试用例 '{case_id}' 吗？\n\n注意：这将同时删除该用例的所有执行记录！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 从数据库删除用例
                self.db.delete_test_case(case_id)
                
                # 从表格中移除
                for row in range(self.cases_table.rowCount()):
                    item = self.cases_table.item(row, 0)
                    if item and item.text() == case_id:
                        self.cases_table.removeRow(row)
                        break
                
                print(f"已删除测试用例: {case_id}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除测试用例失败: {str(e)}")
    
    def delete_collection(self):
        """删除测试集"""
        current_collection = self.collection_combo.currentText()
        if current_collection == "-- 请选择案例集 --" or not current_collection:
            QMessageBox.warning(self, "警告", "请先选择要删除的测试集")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除整个测试集 '{current_collection}' 吗？\n\n注意：这将删除该测试集中的所有用例及其执行记录！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 从数据库删除整个测试集
                self.db.delete_collection(current_collection)
                
                # 清空表格
                self.cases_table.setRowCount(0)
                
                # 刷新下拉框
                self.refresh_collection_combo()
                
                # 通知主窗口刷新历史记录界面
                if self.collection_imported:
                    self.collection_imported()
                
                print(f"已删除测试集: {current_collection}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除测试集失败: {str(e)}")
    
    def import_from_api(self):
        """从接口获取案例"""
        # 显示参数输入对话框
        dialog = ApiImportDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        params = dialog.get_params()
        
        # 验证参数
        if not all(params.values()):
            QMessageBox.warning(self, "警告", "请填写所有参数")
            return
        
        # 显示加载提示
        progress = QProgressDialog("正在从接口获取案例数据...", "取消", 0, 0, self)
        progress.setWindowTitle("请稍候")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumWidth(300)
        progress.setMinimumHeight(100)
        progress.show()
        
        try:
            # 发送GET请求
            url = "http://127.0.0.1/testarGetCase"
            response = requests.get(url, params={
                'projectId': params['project_id'],
                'subtaskName': params['subtask_name'],
                'round': params['round']
            }, timeout=60)
            
            # 检查是否被取消
            if progress.wasCanceled():
                return
            
            if response.status_code != 200:
                QMessageBox.critical(self, "错误", f"API请求失败: HTTP {response.status_code}")
                return
            
            # 解析响应
            data = response.json()
            
            if data.get('status') != 200:
                QMessageBox.critical(self, "错误", f"API返回错误: {data.get('message', '未知错误')}")
                return
            
            cases_data = data.get('data', [])
            if not cases_data:
                QMessageBox.information(self, "提示", "未获取到任何案例数据")
                return
            
            # 转换数据格式为与Excel导入一致的格式
            converted_cases = []
            for case in cases_data:
                converted_case = {
                    '用例ID': case.get('case_id', ''),
                    '测试场景': case.get('caseName', ''),
                    '测试步骤': case.get('test_steps', ''),
                    '预期结果': case.get('expected_result', ''),
                    '优先级': case.get('priority', '')
                }
                converted_cases.append(converted_case)
            
            # 检查导入的案例情况
            existing = self.db.get_all_test_cases()
            existing_ids = set([row['case_id'] for row in existing])
            new_case_ids = [c.get('用例ID', '') for c in converted_cases if c.get('用例ID')]
            existing_case_ids = [cid for cid in new_case_ids if cid in existing_ids]
            new_only_case_ids = [cid for cid in new_case_ids if cid not in existing_ids]
            
            collection_name = None
            
            # 如果有已存在的案例，获取其案例集名称
            if existing_case_ids:
                existing_case = self.db.get_test_case(existing_case_ids[0])
                if existing_case and existing_case.get('case_collection_name'):
                    collection_name = existing_case['case_collection_name']
            
            # 如果没有已存在的案例集名称，且有新案例，才询问用户
            if not collection_name and new_only_case_ids:
                # 生成默认案例集名称
                collection_name = f"{params['project_id']}_{params['subtask_name']}_{params['round']}"
                
                # 询问用户是否修改案例集名称
                text, ok = QInputDialog.getText(
                    self, "案例集名称", 
                    f"请确认或修改案例集名称：", 
                    text=collection_name
                )
                if not ok:
                    return
                collection_name = text.strip() or collection_name
                
                # 记录最近一次导入的集合名
                SettingsUtils.set_last_collection_name(collection_name)
            
            # 为所有案例设置案例集名称
            if collection_name:
                for c in converted_cases:
                    c['案例集名称'] = collection_name
            
            # 导入数据库
            success_count, total_count = self.db.import_test_cases(converted_cases, collection_name)
            
            # 将本次导入的用例追加到当前表格
            imported_ids = [c.get('用例ID') for c in converted_cases if c.get('用例ID')]
            new_cases = []
            for cid in imported_ids:
                case = self.db.get_test_case(cid)
                if case:
                    new_cases.append(case)
            self.add_cases_to_table(new_cases)
            
            # 如果导入了新的案例集，通知主窗口刷新历史记录界面的下拉框
            if collection_name and self.collection_imported:
                self.collection_imported()
            
            # 刷新项目ID和案例集下拉框
            self.refresh_project_combo()
            
            # 自动切换到对应的项目ID和案例集
            if collection_name and new_case_ids:
                # 获取项目ID（取第一个案例ID的前12位）
                project_id = new_case_ids[0][:12] if new_case_ids[0] else ''
                if project_id:
                    # 先切换项目ID
                    project_index = self.project_combo.findText(project_id)
                    if project_index >= 0:
                        self.project_combo.setCurrentIndex(project_index)
                    
                    # 再刷新和切换案例集
                    self.refresh_collection_combo(project_id)
                    collection_index = self.collection_combo.findText(collection_name)
                    if collection_index >= 0:
                        self.collection_combo.setCurrentIndex(collection_index)
            
            # 显示结果
            QMessageBox.information(
                self, "成功", 
                f"从接口获取成功！\n\n已导入 {success_count}/{total_count} 条测试用例"
            )
            
            print(f"从接口导入成功：已导入 {success_count}/{total_count} 条测试用例")
            
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "网络错误", f"请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "数据错误", f"JSON解析失败: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"从接口获取案例失败: {str(e)}")
        finally:
            # 关闭进度对话框
            progress.close()