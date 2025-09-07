from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QFileDialog, QSplitter,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush

from ui_execution import TestCaseExecutionWidget
from excel_parser import ExcelParser


class TestCasesTab(QWidget):
    """测试用例标签页"""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.initUI()
        self.load_test_cases()
    
    def initUI(self):
        """初始化UI"""
        self.layout = QVBoxLayout(self)
        
        # 顶部按钮区域
        button_layout = QHBoxLayout()
        
        # 导入按钮
        self.import_button = QPushButton("导入Excel")
        self.import_button.clicked.connect(self.import_excel)
        button_layout.addWidget(self.import_button)
        
        # 刷新按钮
        self.refresh_button = QPushButton("刷新列表")
        self.refresh_button.clicked.connect(self.load_test_cases)
        button_layout.addWidget(self.refresh_button)
        
        button_layout.addStretch()
        self.layout.addLayout(button_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧用例列表
        self.cases_table = QTableWidget()
        self.cases_table.setColumnCount(5)
        self.cases_table.setHorizontalHeaderLabels(["用例ID", "测试场景", "前置条件", "预期结果", "优先级"])
        self.cases_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.cases_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.cases_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.cases_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cases_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cases_table.itemClicked.connect(self.on_case_selected)
        splitter.addWidget(self.cases_table)
        
        # 右侧执行区域
        self.execution_widget = TestCaseExecutionWidget(self.db)
        # 连接记录保存信号
        self.execution_widget.record_saved.connect(self.on_record_saved)
        splitter.addWidget(self.execution_widget)
        
        # 设置分割器初始大小
        splitter.setSizes([300, 500])
        
        self.layout.addWidget(splitter)
    
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
                precondition_item = QTableWidgetItem(case['precondition'] or "")
                expected_item = QTableWidgetItem(case['expected_result'])
                priority_item = QTableWidgetItem(case['priority'] or "")
                
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
                    priority_item.setBackground(brush)
                    
                    # 存储最新记录ID，用于后续查询
                    id_item.setData(Qt.ItemDataRole.UserRole, records[case_id]['record_id'])
                
                # 添加到表格
                self.cases_table.setItem(row, 0, id_item)
                self.cases_table.setItem(row, 1, scenario_item)
                self.cases_table.setItem(row, 2, precondition_item)
                self.cases_table.setItem(row, 3, expected_item)
                self.cases_table.setItem(row, 4, priority_item)
            
            # 调整列宽
            self.cases_table.resizeColumnsToContents()
            
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
            
            # 导入数据库
            success_count, total_count = self.db.import_test_cases(cases_data)
            
            # 刷新列表
            self.load_test_cases()
            
            # 打印结果
            print(f"导入成功：已导入 {success_count}/{total_count} 条测试用例")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入Excel失败: {str(e)}")
    
    def on_case_selected(self, item):
        """处理用例选择事件"""
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
                
                # 设置所有列的背景色
                brush = QBrush(color)
                for col in range(self.cases_table.columnCount()):
                    cell_item = self.cases_table.item(row, col)
                    if cell_item:
                        cell_item.setBackground(brush)
                
                break
