import os
import tempfile
import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QComboBox, QTableWidget, QTableWidgetItem, QFileDialog, 
    QDateEdit, QLineEdit, QGroupBox, QHeaderView, QProgressBar,
    QMessageBox
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QThread, QTimer

from utils import DateUtils

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


class ExportThread(QThread):
    """导出线程，用于后台处理导出操作"""
    
    # 定义信号
    progress_updated = pyqtSignal(int)  # 进度更新信号
    export_completed = pyqtSignal(str)  # 导出完成信号，参数为导出文件路径
    export_failed = pyqtSignal(str)     # 导出失败信号，参数为错误信息
    
    def __init__(self, db, export_type, file_path, filters=None):
        super().__init__()
        self.db = db
        self.export_type = export_type  # "pdf" 或 "excel"
        self.file_path = file_path
        self.filters = filters or {}  # 筛选条件
    
    def run(self):
        """线程执行函数"""
        try:
            # 获取记录数据
            records = self.db.export_test_records(
                self.filters.get('start_date'),
                self.filters.get('end_date'),
                self.filters.get('case_id'),
                self.filters.get('status')
            )
            
            if not records:
                self.export_failed.emit("没有符合条件的记录可导出")
                return
            
            # 更新进度
            self.progress_updated.emit(10)
            
            # 根据类型导出
            if self.export_type == "pdf":
                self._export_to_pdf(records)
            elif self.export_type == "excel":
                self._export_to_excel(records)
            else:
                self.export_failed.emit("不支持的导出类型")
                return
            
            # 导出完成
            self.export_completed.emit(self.file_path)
            
        except Exception as e:
            self.export_failed.emit(f"导出失败: {str(e)}")
    
    def _export_to_pdf(self, records):
        """导出为PDF"""
        # 创建临时目录用于存放图片
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 创建PDF文档
            doc = SimpleDocTemplate(self.file_path, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []
            
            # 添加标题
            title_style = styles["Title"]
            elements.append(Paragraph("测试执行报告", title_style))
            elements.append(Spacer(1, 20))
            
            # 添加统计信息
            stats = self.db.get_statistics(
                self.filters.get('start_date'),
                self.filters.get('end_date')
            )
            
            stats_data = [
                ["总记录数", "通过", "失败", "阻塞", "跳过", "通过率"],
                [
                    str(stats['total']),
                    str(stats['通过']),
                    str(stats['失败']),
                    str(stats['阻塞']),
                    str(stats['跳过']),
                    f"{stats['通过率']:.2f}%"
                ]
            ]
            
            stats_table = Table(stats_data)
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(stats_table)
            elements.append(Spacer(1, 20))
            
            # 更新进度
            self.progress_updated.emit(30)
            
            # 复制图片到临时目录
            image_paths = []
            for record in records:
                if 'images' in record and record['images']:
                    for img_path in record['images']:
                        if img_path and os.path.exists(img_path):
                            # 复制图片到临时目录
                            img_name = os.path.basename(img_path)
                            temp_img_path = os.path.join(temp_dir, img_name)
                            shutil.copy2(img_path, temp_img_path)
                            image_paths.append((record['用例ID'], temp_img_path))
            
            # 更新进度
            self.progress_updated.emit(50)
            
            # 添加详细记录
            for i, record in enumerate(records):
                # 添加用例信息
                elements.append(Paragraph(f"用例ID: {record['用例ID']}", styles["Heading2"]))
                elements.append(Paragraph(f"测试场景: {record['测试场景']}", styles["Normal"]))
                elements.append(Paragraph(f"测试步骤: {record.get('测试步骤') or '无'}", styles["Normal"]))
                elements.append(Paragraph(f"预期结果: {record['预期结果']}", styles["Normal"]))
                elements.append(Paragraph(f"优先级: {record['优先级'] or '无'}", styles["Normal"]))
                elements.append(Spacer(1, 10))
                
                # 添加执行结果
                elements.append(Paragraph("执行结果", styles["Heading3"]))
                elements.append(Paragraph(f"状态: {record['执行状态']}", styles["Normal"]))
                elements.append(Paragraph(f"实际结果: {record['实际结果'] or '无'}", styles["Normal"]))
                elements.append(Paragraph(f"备注: {record['备注'] or '无'}", styles["Normal"]))
                # 不展示执行人
                
                # 添加执行时间
                timestamp = record['执行时间']
                date_str = DateUtils.timestamp_to_string(timestamp)
                elements.append(Paragraph(f"执行时间: {date_str}", styles["Normal"]))
                
                # 添加图片
                if 'images' in record and record['images']:
                    elements.append(Paragraph("图片:", styles["Normal"]))
                    for img_path in record['images']:
                        if img_path and os.path.exists(img_path):
                            # 使用临时目录中的图片
                            img_name = os.path.basename(img_path)
                            temp_img_path = os.path.join(temp_dir, img_name)
                            if os.path.exists(temp_img_path):
                                img = Image(temp_img_path)
                                # 设置最大宽度
                                max_width = 400
                                if img.drawWidth > max_width:
                                    ratio = max_width / img.drawWidth
                                    img.drawWidth = max_width
                                    img.drawHeight *= ratio
                                elements.append(img)
                                elements.append(Spacer(1, 5))
                
                # 添加分隔线
                if i < len(records) - 1:
                    elements.append(Spacer(1, 20))
                    elements.append(Paragraph("_" * 70, styles["Normal"]))
                    elements.append(Spacer(1, 20))
                
                # 更新进度
                progress = 50 + int((i + 1) / len(records) * 40)
                self.progress_updated.emit(progress)
            
            # 构建PDF
            doc.build(elements)
            self.progress_updated.emit(100)
            
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _export_to_excel(self, records):
        """导出为Excel"""
        # 创建导出目录
        export_dir = os.path.dirname(self.file_path)
        os.makedirs(export_dir, exist_ok=True)
        
        # 创建图片目录
        images_dir = os.path.join(export_dir, 'images')
        os.makedirs(images_dir, exist_ok=True)
        
        # 准备数据
        export_data = []
        for record in records:
            # 复制图片
            image_refs = []
            if 'images' in record and record['images']:
                for img_path in record['images']:
                    if img_path and os.path.exists(img_path):
                        # 复制图片到导出目录
                        img_name = os.path.basename(img_path)
                        export_img_path = os.path.join(images_dir, img_name)
                        shutil.copy2(img_path, export_img_path)
                        # 添加相对路径引用
                        image_refs.append(f"images/{img_name}")
            
            # 创建记录数据
            row_data = {
                '用例ID': record['用例ID'],
                '测试场景': record['测试场景'],
                '测试步骤': record.get('测试步骤') or '',
                '预期结果': record['预期结果'],
                '优先级': record['优先级'] or '',
                '执行状态': record['执行状态'],
                '实际结果': record['实际结果'] or '',
                '备注': record['备注'] or '',
                '执行时间': DateUtils.timestamp_to_string(record['执行时间']),
                '图片': ', '.join(image_refs)
            }
            export_data.append(row_data)
            
            # 更新进度
            progress = 10 + int((records.index(record) + 1) / len(records) * 80)
            self.progress_updated.emit(progress)
        
        # 创建DataFrame并导出
        df = pd.DataFrame(export_data)
        df.to_excel(self.file_path, index=False)
        
        self.progress_updated.emit(100)


class HistoryTab(QWidget):
    """历史记录标签页"""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.export_thread = None
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        self.layout = QVBoxLayout(self)
        
        # 筛选区域
        filter_group = QGroupBox("筛选条件")
        filter_layout = QHBoxLayout(filter_group)
        
        # 开始日期
        filter_layout.addWidget(QLabel("开始日期:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        filter_layout.addWidget(self.start_date)
        
        # 结束日期
        filter_layout.addWidget(QLabel("结束日期:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        filter_layout.addWidget(self.end_date)
        
        # 状态筛选
        filter_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部", "通过", "失败", "阻塞", "跳过"])
        filter_layout.addWidget(self.status_combo)
        
        # 搜索框（支持ID和测试场景）
        filter_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入用例ID或测试场景关键字")
        self.search_edit.returnPressed.connect(self.search_records)
        filter_layout.addWidget(self.search_edit)
        
        # 查询按钮
        self.search_button = QPushButton("查询")
        self.search_button.clicked.connect(self.search_records)
        filter_layout.addWidget(self.search_button)
        
        self.layout.addWidget(filter_group)
        
        # 统计信息区域
        stats_group = QGroupBox("统计信息")
        stats_layout = QHBoxLayout(stats_group)
        
        # 总数
        stats_layout.addWidget(QLabel("总记录数:"))
        self.total_label = QLabel("0")
        stats_layout.addWidget(self.total_label)
        
        # 通过数
        stats_layout.addWidget(QLabel("通过:"))
        self.pass_label = QLabel("0")
        stats_layout.addWidget(self.pass_label)
        
        # 失败数
        stats_layout.addWidget(QLabel("失败:"))
        self.fail_label = QLabel("0")
        stats_layout.addWidget(self.fail_label)
        
        # 阻塞数
        stats_layout.addWidget(QLabel("阻塞:"))
        self.block_label = QLabel("0")
        stats_layout.addWidget(self.block_label)
        
        # 跳过数
        stats_layout.addWidget(QLabel("跳过:"))
        self.skip_label = QLabel("0")
        stats_layout.addWidget(self.skip_label)
        
        # 通过率
        stats_layout.addWidget(QLabel("通过率:"))
        self.rate_label = QLabel("0%")
        stats_layout.addWidget(self.rate_label)
        
        self.layout.addWidget(stats_group)
        
        # 记录列表
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(7)
        self.records_table.setHorizontalHeaderLabels([
            "记录ID", "用例ID", "测试场景", "案例集名称", "实际结果", "执行状态", "执行时间"
        ])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.records_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.records_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.records_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.records_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # 添加双击事件
        self.records_table.cellDoubleClicked.connect(self.on_record_double_clicked)
        self.layout.addWidget(self.records_table)
        
        # 导出按钮区域
        export_layout = QHBoxLayout()
        
        # 导出PDF按钮
        self.export_pdf_button = QPushButton("导出PDF报告")
        self.export_pdf_button.clicked.connect(self.export_pdf)
        export_layout.addWidget(self.export_pdf_button)
        
        # 导出Excel按钮
        self.export_excel_button = QPushButton("导出Excel报告")
        self.export_excel_button.clicked.connect(self.export_excel)
        export_layout.addWidget(self.export_excel_button)
        
        # 导出进度条
        self.export_progress = QProgressBar()
        self.export_progress.setVisible(False)
        export_layout.addWidget(self.export_progress)
        
        self.layout.addLayout(export_layout)
        
        # 初始查询
        self.search_records()
    
    def search_records(self):
        """查询记录"""
        try:
            # 获取筛选条件
            start_date = DateUtils.string_to_timestamp(self.start_date.date().toString("yyyy-MM-dd"))
            end_date = DateUtils.string_to_timestamp(self.end_date.date().addDays(1).toString("yyyy-MM-dd"))
            
            status = self.status_combo.currentText()
            if status == "全部":
                status = None
            
            # 获取搜索关键字
            search_text = self.search_edit.text().strip()
            
            # 查询记录
            records = self.db.get_test_records(None, status, start_date, end_date)
            
            # 如果有搜索关键字，进行过滤
            if search_text:
                filtered_records = []
                
                # 检查搜索文本是否包含汉字
                has_chinese = any('\u4e00' <= char <= '\u9fff' for char in search_text)
                
                for record in records:
                    # 如果包含汉字，则模糊查询测试场景
                    if has_chinese:
                        # 获取测试用例信息并匹配测试场景
                        case = self.db.get_test_case(record['case_id'])
                        if case and 'scenario' in case and case['scenario']:
                            if search_text.lower() in case['scenario'].lower():
                                filtered_records.append(record)
                    # 如果不包含汉字，则直接查询用例ID
                    else:
                        if search_text.lower() in record['case_id'].lower():
                            filtered_records.append(record)
                
                records = filtered_records
                print(f"搜索结果：找到 {len(records)} 条记录")
            
            # 清空表格
            self.records_table.setRowCount(0)
            
            # 填充数据
            for row, record in enumerate(records):
                self.records_table.insertRow(row)
                
                # 创建记录ID项并存储完整记录数据
                record_id_item = QTableWidgetItem(str(record['record_id']))
                record_id_item.setData(Qt.ItemDataRole.UserRole, record)
                self.records_table.setItem(row, 0, record_id_item)
                
                # 设置其他列
                self.records_table.setItem(row, 1, QTableWidgetItem(record['case_id']))
                case = self.db.get_test_case(record['case_id'])
                self.records_table.setItem(row, 2, QTableWidgetItem((case['scenario'] if case else "")))
                self.records_table.setItem(row, 3, QTableWidgetItem((case.get('case_collection_name') if case else "") or ""))
                self.records_table.setItem(row, 4, QTableWidgetItem(record['actual_result'] or ""))
                self.records_table.setItem(row, 5, QTableWidgetItem(record['status']))
                
                # 格式化时间戳
                timestamp = record['timestamp']
                date_str = DateUtils.timestamp_to_string(timestamp)
                self.records_table.setItem(row, 6, QTableWidgetItem(date_str))
            
            # 更新统计信息
            stats = self.db.get_statistics(start_date, end_date)
            self.total_label.setText(str(stats['total']))
            self.pass_label.setText(str(stats['通过']))
            self.fail_label.setText(str(stats['失败']))
            self.block_label.setText(str(stats['阻塞']))
            self.skip_label.setText(str(stats['跳过']))
            self.rate_label.setText(f"{stats['通过率']:.2f}%")
            
            # 更新状态栏显示查询结果
            print(f"查询成功：找到 {len(records)} 条记录")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询失败: {str(e)}")
    
    def export_pdf(self):
        """导出PDF报告"""
        # 打开文件对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存PDF报告", "", "PDF文件 (*.pdf)"
        )
        
        if not file_path:
            return
        
        # 确保文件扩展名
        if not file_path.lower().endswith('.pdf'):
            file_path += '.pdf'
        
        # 获取筛选条件
        filters = {
            'start_date': DateUtils.string_to_timestamp(self.start_date.date().toString("yyyy-MM-dd")),
            'end_date': DateUtils.string_to_timestamp(self.end_date.date().addDays(1).toString("yyyy-MM-dd")),
            'case_id': self.search_edit.text().strip() or None,
            'status': self.status_combo.currentText() if self.status_combo.currentText() != "全部" else None
        }
        
        # 创建并启动导出线程
        self.export_thread = ExportThread(self.db, "pdf", file_path, filters)
        self.export_thread.progress_updated.connect(self.update_export_progress)
        self.export_thread.export_completed.connect(self.on_export_completed)
        self.export_thread.export_failed.connect(self.on_export_failed)
        
        # 显示进度条
        self.export_progress.setValue(0)
        self.export_progress.setVisible(True)
        self.export_pdf_button.setEnabled(False)
        self.export_excel_button.setEnabled(False)
        
        # 启动线程
        self.export_thread.start()
    
    def export_excel(self):
        """导出Excel报告"""
        # 打开文件对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存Excel报告", "", "Excel文件 (*.xlsx)"
        )
        
        if not file_path:
            return
        
        # 确保文件扩展名
        if not file_path.lower().endswith('.xlsx'):
            file_path += '.xlsx'
        
        # 获取筛选条件
        filters = {
            'start_date': DateUtils.string_to_timestamp(self.start_date.date().toString("yyyy-MM-dd")),
            'end_date': DateUtils.string_to_timestamp(self.end_date.date().addDays(1).toString("yyyy-MM-dd")),
            'case_id': self.search_edit.text().strip() or None,
            'status': self.status_combo.currentText() if self.status_combo.currentText() != "全部" else None
        }
        
        # 创建并启动导出线程
        self.export_thread = ExportThread(self.db, "excel", file_path, filters)
        self.export_thread.progress_updated.connect(self.update_export_progress)
        self.export_thread.export_completed.connect(self.on_export_completed)
        self.export_thread.export_failed.connect(self.on_export_failed)
        
        # 显示进度条
        self.export_progress.setValue(0)
        self.export_progress.setVisible(True)
        self.export_pdf_button.setEnabled(False)
        self.export_excel_button.setEnabled(False)
        
        # 启动线程
        self.export_thread.start()
    
    def update_export_progress(self, value):
        """更新导出进度"""
        self.export_progress.setValue(value)
    
    def on_export_completed(self, file_path):
        """导出完成处理"""
        self.export_progress.setVisible(False)
        self.export_pdf_button.setEnabled(True)
        self.export_excel_button.setEnabled(True)
        
        # 显示导出成功消息
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("导出成功")
        msg.setText(f"报告已保存至: {os.path.basename(file_path)}")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
    
    def on_export_failed(self, error_message):
        """导出失败处理"""
        self.export_progress.setVisible(False)
        self.export_pdf_button.setEnabled(True)
        self.export_excel_button.setEnabled(True)
        
        # 显示导出失败消息
        QMessageBox.critical(self, "导出失败", error_message)
    
    def on_record_double_clicked(self, row, column):
        """双击记录查看详情"""
        try:
            # 获取记录数据
            record_item = self.records_table.item(row, 0)
            if record_item and record_item.data(Qt.ItemDataRole.UserRole):
                record = record_item.data(Qt.ItemDataRole.UserRole)
                
                # 获取测试用例信息
                case = self.db.get_test_case(record['case_id'])
                
                # 创建详情对话框
                dialog = QMessageBox(self)
                dialog.setWindowTitle("执行记录详情")
                dialog.setIcon(QMessageBox.Icon.Information)
                
                # 构建详情文本
                details = f"记录ID: {record['record_id']}\n"
                details += f"用例ID: {record['case_id']}\n"
                
                # 添加测试用例信息（如果可用）
                if case:
                    details += f"测试场景: {case['scenario']}\n"
                    details += f"测试步骤: {(case.get('test_steps') or case.get('precondition') or '无')}\n"
                    details += f"预期结果: {case['expected_result']}\n"
                    details += f"优先级: {case['priority'] or '无'}\n\n"
                
                details += f"执行状态: {record['status']}\n"
                details += f"实际结果: {record['actual_result'] or '无'}\n"
                details += f"备注: {record['notes'] or '无'}\n"
                # 不展示执行人
                details += f"执行时间: {DateUtils.timestamp_to_string(record['timestamp'])}\n"
                
                # 设置详情文本
                dialog.setText(details)
                
                # 如果有图片，添加查看图片按钮
                if 'images' in record and record['images'] and len(record['images']) > 0:
                    dialog.setInformativeText(f"该记录包含 {len(record['images'])} 张图片")
                    view_images_button = dialog.addButton("查看图片", QMessageBox.ButtonRole.ActionRole)
                    dialog.addButton(QMessageBox.StandardButton.Close)
                    
                    result = dialog.exec()
                    
                    # 如果点击了查看图片按钮
                    if dialog.clickedButton() == view_images_button:
                        self.show_record_images(record)
                else:
                    dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查看记录详情失败: {str(e)}")
    
    def show_record_images(self, record):
        """显示记录的图片"""
        if 'images' not in record or not record['images']:
            return
        
        # 创建图片查看对话框
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QLabel
        from PyQt6.QtGui import QPixmap
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"执行记录 {record['record_id']} 的图片")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # 创建内容窗口
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # 添加图片
        for img_path in record['images']:
            if img_path and os.path.exists(img_path):
                # 创建图片标签
                img_label = QLabel()
                pixmap = QPixmap(img_path)
                
                # 如果图片太大，调整大小
                if pixmap.width() > 750:
                    pixmap = pixmap.scaledToWidth(750, Qt.TransformationMode.SmoothTransformation)
                
                img_label.setPixmap(pixmap)
                img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # 添加图片路径标签
                path_label = QLabel(f"图片路径: {img_path}")
                path_label.setWordWrap(True)
                
                content_layout.addWidget(path_label)
                content_layout.addWidget(img_label)
                content_layout.addWidget(QLabel(""))  # 添加间隔
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        dialog.exec()
