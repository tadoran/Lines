from PyQt5.QtCore import QSize, QMargins, QRect, QObject, QPoint
from PyQt5.QtGui import QResizeEvent, QPainter, QBrush, QColor
from PyQt5.QtWidgets import QMainWindow
from itertools import chain

from enums import CoordinatesMoves
from random import randint


class pt(QPoint):
    def __repr__(self):
        return f"({self.x()},{self.y()})"


class GamePathExplorer(QMainWindow):
    def __init__(self, monitoredWidget, *args, **kwargs):
        super(GamePathExplorer, self).__init__(*args, **kwargs)
        self.monitoredWidget = monitoredWidget
        self.monitoredWidget.game_field.item_changed.connect(self.update_map)
        self.pts_w, self.pts_h = self.monitoredWidget.game_field.width, self.monitoredWidget.game_field.height
        self.get_monitored_widget_fill()
        self.block_size = 30
        QPoint.__repr__ = pt.__repr__
        self.found_path = []

    def sizeHint(self):
        return QSize(self.block_size * self.pts_w, self.block_size * self.pts_w)

    def update_map(self, item):
        # print("Update!", item)
        if item.active_state:
            self.found_path = item.parent().find_paths(item,
                                              self.monitoredWidget.game_field.fieldItems2D[randint(0, self.pts_h - 1)][
                                                  randint(0, self.pts_w - 1)])
        self.get_monitored_widget_fill()
        self.update()


    def get_monitored_widget_fill(self):
        self.field_map = self.monitoredWidget.game_field.fieldItems2D

    def paintEvent(self, *args, **kwargs):
        painter = QPainter(self)
        margin = QMargins() + 5
        w, h = self.width(), self.height()
        cur_brush = QBrush(QColor("white"))
        default_brush = QBrush()

        block_size_y = h // len(self.field_map)
        for y, row in enumerate(self.field_map):
            block_size_x = w // len(row)
            for x, item in enumerate(row):
                painter.setBrush(default_brush)
                rect = QRect(x * block_size_x, y * block_size_y, block_size_x, block_size_y)
                painter.drawRect(rect)

                item = self.field_map[y][x]
                if item.active_state:
                    cur_brush.setColor(QColor("magenta"))
                elif item.color:
                    cur_brush.setColor(QColor(item.color))
                else:
                    # cur_brush.setColor(QColor("white"))
                    # continue
                    pass

                painter.setBrush(cur_brush)
                # painter.drawRect(rect)

                if len(self.found_path) > 0:
                    if QPoint(x, y) in self.found_path:
                        cur_brush.setColor(QColor("yellow"))
                        painter.setBrush(cur_brush)
                        painter.drawRect(rect)

                painter.drawEllipse(rect - margin)
                cur_brush.setColor(QColor("white"))

        painter.end()

    # def paintEvent(self, *args, **kwargs):
    #     # super().paintEvent(*args, **kwargs)
    #     painter = QPainter(self)
    #     w, h = self.pts_w, self.pts_h
    #     block_size = self.block_size
    #     brush1 = QBrush(QColor("red"))
    #     brush2 = QBrush(QColor("blue"))
    #     cur_brush = QBrush(QColor("blue"))
    #
    #     for y, row in enumerate(self.field_map):
    #         for x, item in enumerate(row):
    #             rect = QRect(x * block_size, y * block_size, self.block_size , self.block_size)
    #             # rect -= QMargins() - 5
    #             # if self.field_map[y][x].color:
    #             #     cur_brush = brush1
    #             # else:
    #             #     cur_brush = brush2
    #             color = self.field_map[y][x].color
    #             if color:
    #                 cur_brush.setColor(QColor(self.field_map[y][x].color))
    #             else:
    #                 cur_brush.setColor(QColor("white"))
    #             painter.fillRect(rect, cur_brush)
    #
    #     painter.end()
