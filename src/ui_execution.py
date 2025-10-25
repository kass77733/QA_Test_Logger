import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTextEdit, QLineEdit, QGroupBox, QMessageBox,
    QFileDialog, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt

from ui_components import ImageListWidget
from utils import ImageUtils

class TestCaseExecutionWidget(QWidget):
    """测试用例执行组件"""
    
    # 定义信号
    record_saved = pyqtSignal(int)  # 记录保存信号，参数为记录ID
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_case = None
        self.current_record = None
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        self.layout = QVBoxLayout(self)
        
        # 测试用例信息区域
        case_info_group = QGroupBox("测试用例信息")
        case_info_layout = QVBoxLayout(case_info_group)

        # 测试ID
        case_id_layout = QHBoxLayout()
        case_id_layout.addWidget(QLabel("测试ID:"))
        self.case_id_label = QLabel()
        self.case_id_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.case_id_label.setWordWrap(True)
        self.case_id_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        case_id_layout.addWidget(self.case_id_label)
        case_info_layout.addLayout(case_id_layout)

        # 测试场景
        scenario_layout = QHBoxLayout()
        scenario_layout.addWidget(QLabel("测试场景:"))
        self.scenario_label = QLabel()
        self.scenario_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.scenario_label.setWordWrap(True)
        self.scenario_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        scenario_layout.addWidget(self.scenario_label)
        case_info_layout.addLayout(scenario_layout)

        # 案例集名称
        collection_layout = QHBoxLayout()
        collection_layout.addWidget(QLabel("案例集名称:"))
        self.collection_label = QLabel()
        self.collection_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.collection_label.setWordWrap(True)
        self.collection_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        collection_layout.addWidget(self.collection_label)
        case_info_layout.addLayout(collection_layout)
        
        # 测试步骤
        precondition_layout = QHBoxLayout()
        precondition_layout.addWidget(QLabel("测试步骤:"))
        self.precondition_label = QLabel()
        self.precondition_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.precondition_label.setWordWrap(True)
        self.precondition_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        precondition_layout.addWidget(self.precondition_label)
        case_info_layout.addLayout(precondition_layout)
        
        # 预期结果
        expected_layout = QHBoxLayout()
        expected_layout.addWidget(QLabel("预期结果:"))
        self.expected_label = QLabel()
        self.expected_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.expected_label.setWordWrap(True)
        self.expected_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        expected_layout.addWidget(self.expected_label)
        case_info_layout.addLayout(expected_layout)
        
        # 优先级
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("优先级:"))
        self.priority_label = QLabel()
        self.priority_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.priority_label.setWordWrap(True)
        self.priority_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        priority_layout.addWidget(self.priority_label)
        case_info_layout.addLayout(priority_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(case_info_group)  # ✅ 把 groupBox 放进去
        # ✅ 设置 scroll 本身的最小高度和大小策略
        scroll.setMinimumHeight(200)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(scroll)
        
        # 执行结果区域
        execution_group = QGroupBox("执行结果")
        execution_layout = QVBoxLayout(execution_group)
        
        # 执行状态
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("执行状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["通过", "失败", "阻塞", "跳过"])
        status_layout.addWidget(self.status_combo)
        execution_layout.addLayout(status_layout)
        
        # 执行人（隐藏不展示，仍保留字段以兼容数据库）
        executor_layout = QHBoxLayout()
        executor_label = QLabel("执行人:")
        executor_label.setVisible(False)
        executor_layout.addWidget(executor_label)
        self.executor_edit = QLineEdit()
        self.executor_edit.setVisible(False)
        executor_layout.addWidget(self.executor_edit)
        execution_layout.addLayout(executor_layout)
        
        # 实际结果
        execution_layout.addWidget(QLabel("实际结果:"))
        self.actual_result_edit = QTextEdit()
        execution_layout.addWidget(self.actual_result_edit)
        
        # 备注
        execution_layout.addWidget(QLabel("备注:"))
        self.notes_edit = QTextEdit()
        execution_layout.addWidget(self.notes_edit)
        
        # 图片列表
        execution_layout.addWidget(QLabel("图片:"))
        self.image_list = ImageListWidget()
        self.image_list.paste_button.clicked.connect(self.paste_image)
        self.image_list.select_button.clicked.connect(self.select_image)
        execution_layout.addWidget(self.image_list)
        
        self.layout.addWidget(execution_group)
        
        # 保存按钮
        self.save_button = QPushButton("保存执行记录")
        self.save_button.clicked.connect(self.save_record)
        self.layout.addWidget(self.save_button)
    
    def set_test_case(self, case):
        """设置当前测试用例"""
        if not case:
            return
        
        self.current_case = case
        self.current_record = None
        
        # 更新UI
        self.case_id_label.setText(case['case_id'])
        self.scenario_label.setText(case['scenario'])
        self.collection_label.setText(case.get('case_collection_name') or "无")
        self.precondition_label.setText((case.get('test_steps') or case.get('precondition') or "无"))
        self.expected_label.setText(case['expected_result'])
        self.priority_label.setText(case['priority'] or "无")
        
        # 清空执行结果
        self.status_combo.setCurrentIndex(0)
        self.executor_edit.setText("")
        self.actual_result_edit.setText("")
        self.notes_edit.setText("")
        self.image_list.setImages([])
    
    def load_record(self, record):
        """加载已有的执行记录"""
        if not record or not self.current_case:
            return
        
        # 设置当前记录
        self.current_record = record
        
        # 更新UI
        status_index = self.status_combo.findText(record['status'])
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)
        
        self.executor_edit.setText(record.get('executor') or "")
        self.actual_result_edit.setText(record['actual_result'] or "")
        self.notes_edit.setText(record['notes'] or "")
        
        # 加载图片
        if 'images' in record and record['images']:
            self.image_list.setImages(record['images'])
        else:
            self.image_list.setImages([])
    
    def paste_image(self):
        """从剪贴板粘贴图片"""
        if not self.current_case:
            QMessageBox.warning(self, "警告", "请先选择一个测试用例")
            return
        
        # 保存图片
        image_path = ImageUtils.save_image_from_clipboard(self.current_case['case_id'])
        
        if not image_path:
            QMessageBox.warning(self, "警告", "剪贴板中没有图片")
            return
        
        # 添加到图片列表
        self.image_list.addImage(image_path)
        
        # 打印成功消息
        print("图片已成功添加到测试记录")
    
    def select_image(self):
        """选择图片文件"""
        if not self.current_case:
            QMessageBox.warning(self, "警告", "请先选择一个测试用例")
            return
        
        # 打开文件对话框
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if not file_paths:
            return
        
        # 保存图片
        for file_path in file_paths:
            image_path = ImageUtils.save_image_from_file(self.current_case['case_id'], file_path)
            self.image_list.addImage(image_path)
        
        # 打印成功消息
        print(f"已成功添加 {len(file_paths)} 张图片到测试记录")
    
    def save_record(self):
        """保存执行记录"""
        if not self.current_case:
            QMessageBox.warning(self, "警告", "请先选择一个测试用例")
            return
        
        # 获取输入数据
        status = self.status_combo.currentText()
        executor = self.executor_edit.text()
        actual_result = self.actual_result_edit.toPlainText()
        notes = self.notes_edit.toPlainText()
        image_paths = self.image_list.getImagePaths()
        
        try:
            # 如果是更新现有记录
            if self.current_record:
                self.db.update_test_record(
                    self.current_record['record_id'],
                    status=status,
                    actual_result=actual_result,
                    notes=notes,
                    image_paths=image_paths,
                    executor=executor
                )
                record_id = self.current_record['record_id']
                message = "执行记录已更新"
            else:
                # 创建新记录
                record_id = self.db.save_test_record(
                    self.current_case['case_id'],
                    status,
                    actual_result,
                    notes,
                    image_paths,
                    executor
                )
                message = "新执行记录已创建"
            
            # 发送记录保存信号
            self.record_saved.emit(record_id)
            
            # 打印成功消息
            print(f"保存成功: {message}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存记录失败: {str(e)}")