import sys
from copy import deepcopy
from itertools import chain
from random import choice

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from about import Ui_Dialog
from enums import GameStatus, GameDifficulty, CoordinatesMoves
from resources import Images, Sounds

from lines.path_explorer import GamePathExplorer


class AboutDialog(QDialog, Ui_Dialog):
    def __init__(self, *args, **kwargs):
        super(AboutDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)


class FieldItem(QPushButton):
    changed = pyqtSignal(QObject)
    rightButtonPressed = pyqtSignal()

    @property
    def active_state(self):
        return self._active_state

    @active_state.setter
    def active_state(self, toggled: bool):
        self._active_state = toggled
        self.changed.emit(self)
        if toggled:
            # print("Active state")
            self._active_state_timer.start(200)
        else:
            # print("Inactive state")
            self._active_state_timer.stop()
            if self.active_sprite_num:
                self._active_state_timer.singleShot(500, self.change_active_sprite)

    def change_active_sprite(self):
        if not self.active_sprite_num:
            self.parent().sounds.tick.play()
        self.active_sprite_num = not self.active_sprite_num
        self.update()
        # print(self, self.active_sprite_num)

    def __init__(self, y, x, *args, **kwargs):
        super(FieldItem, self).__init__(*args, **kwargs)
        self.y = y
        self.x = x
        self.not_empty = False

        self._active_state = False
        self._active_state_timer = QTimer(self)
        self.active_sprite_num = 0
        self._active_state_timer.timeout.connect(self.change_active_sprite)

        self.next_color = None
        self.color = None
        self.brief_override = None

        self.current_image = self.parent().images.empty

        size_policy = QSizePolicy.Expanding
        policy = QSizePolicy()
        policy.setHorizontalPolicy(size_policy)
        policy.setVerticalPolicy(size_policy)
        policy.setWidthForHeight(True)
        self.setSizePolicy(policy)

        self.pressed.connect(lambda item=self: item.parent().item_clicked(item))
        self.rightButtonPressed.connect(self.calculate_line)

    def spawn_item(self, color: str = None):
        if not color:
            if self.next_color:
                self.color = self.next_color
            else:
                self.color = choice(list(self.parent().images.colors))
        else:
            self.color = color

        self.current_image = self.parent().images.colors[self.color]
        self.not_empty = True
        self.changed.emit(self)
        self.update()

    def calculate_line(self) -> bool:

        # [x.value for x in CoordinatesMoves]
        moves = CoordinatesMoves
        horizontal_moves = [moves.LEFT, moves.RIGHT]
        vertical_moves = [moves.UP, moves.DOWN]
        diagonal1_moves = [moves.UP_LEFT, moves.DOWN_RIGHT]
        diagonal2_moves = [moves.UP_RIGHT, moves.DOWN_LEFT]

        directions = [horizontal_moves, vertical_moves, diagonal1_moves, diagonal2_moves]

        field_items = self.parent().fieldItems2D
        pw, ph = self.parent().width, self.parent().height
        y, x = self.y, self.x
        for direction in directions:
            line_elements_count = 1
            line_elements = [self]
            for move in direction:
                next_y, next_x = y, x
                while True:
                    next_y, next_x = next_y + move.value[0], next_x + move.value[1]
                    if 0 <= next_y < ph and 0 <= next_x < pw:
                        next_item = field_items[next_y][next_x]

                        if next_item.color == self.color and self.color is not None:
                            line_elements_count += 1
                            line_elements += [next_item]
                            continue
                        else:
                            break
                    else:
                        break

            if line_elements_count >= self.parent().ITEMS_IN_LINE:
                # print(f"There is a line {line_elements}")
                for line_element in line_elements:
                    line_element.reset()

                self.parent().sounds.line_cleared.play()
                self.parent().scores += 5 * line_elements_count
                return True
        return False

    def show_briefly(self, img: QImage):
        self.brief_override = img

    def cancel_override(self):
        self.brief_override = None

    def paintEvent(self, e: QPaintEvent):
        super().paintEvent(e)
        painter = QPainter(self)
        if self.brief_override:
            painter.drawImage(
                self.rect().marginsAdded(QMargins() - 5),
                self.brief_override
            )
            painter.end()
            return

        if self.active_state:
            # painter.fillRect(self.rect(), QColor("#f5f2eb"))
            painter.fillRect(self.rect(), QColor("#f0f0f0"))
            pass

        if self.parent().SHOW_NEXT_SPAWN:
            if self.next_color and not self.color:
                painter.drawImage(
                    self.rect().marginsAdded(QMargins() - 25),
                    self.parent().images.colors[self.next_color]
                )

        if self.color:
            painter.drawImage(
                self.rect().marginsAdded(QMargins() - (5 + int(self.active_sprite_num) * 2)),
                self.current_image
            )

        painter.end()

    def sizeHint(self):
        return QSize(70, 70)

    def minimumSizeHint(self):
        return QSize(self.sizeHint().width() // 2, self.sizeHint().height() // 2)

    def __str__(self):
        return f"Item ({self.y},{self.x})"

    def reset(self):
        self.current_image = self.parent().images.empty
        self.not_empty = False
        self.active_state = False
        self.color = None
        self.brief_override = None

        self.update()

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self.pressed.emit()
        elif e.button() == Qt.RightButton:
            self.rightButtonPressed.emit()
        else:
            pass


class GameField(QWidget):
    game_started = pyqtSignal()
    game_ended = pyqtSignal()
    game_reset = pyqtSignal()
    game_status_changed = pyqtSignal(GameStatus)
    item_changed = pyqtSignal(QObject)
    scores_updated = pyqtSignal(int)

    ITEMS_IN_LINE = 5
    SPAWN_PER_TURN = 3
    SHOW_NEXT_SPAWN = True

    @pyqtSlot(QObject)
    def item_changed_slot(self, item):
        # print("item_changed", item)
        self.item_changed.emit(item)

    def __init__(self, width=10, height=10, *args, **kwargs):
        super(GameField, self).__init__(*args, **kwargs)

        self.images = self.parent().images
        self.sounds = self.parent().sounds

        self.width = width
        self.height = height

        self._scores = 0
        self.next_spawn = []

        self.ready_to_move_item = False
        self.item_to_move = None

        self.fieldItems2D = []

        layout = QGridLayout(self)
        layout.setSpacing(0)
        layout.heightForWidth(True)

        for y in range(height):
            self.fieldItems2D.append([])
            for x in range(width):
                item = FieldItem(y, x, parent=self)
                item.changed.connect(self.item_changed_slot)
                self.fieldItems2D[y].append(item)
                layout.addWidget(item, y, x)

        self.fieldItems = list(chain.from_iterable(self.fieldItems2D))
        self.prepare_next_spawn(self.SPAWN_PER_TURN)
        self.game_ended.connect(self.stop_game)

    @property
    def scores(self):
        return self._scores

    @scores.setter
    def scores(self, count: int):
        self._scores = count
        self.scores_updated.emit(count)

    def resizeEvent(self, e: QResizeEvent):
        w, h = e.size().width(), e.size().height()
        wh = min(w, h)
        new_size = QSize(wh, wh)
        e.accept()
        self.resize(new_size)

    @property
    def empty_items_count(self) -> int:
        count = sum([not i.not_empty for i in self.fieldItems])
        return count

    def spawn_items(self):
        if len(self.next_spawn) < self.SPAWN_PER_TURN:
            self.prepare_next_spawn(self.SPAWN_PER_TURN - len(self.next_spawn))

        for item in self.next_spawn:
            item.spawn_item()
        self.next_spawn = []
        self.prepare_next_spawn(self.SPAWN_PER_TURN)

    def prepare_next_spawn(self, n: int = 0):
        if n == 0:
            n = srlf.SPAWN_PER_TURN
        empty_items_count = self.empty_items_count
        if self.empty_items_count == 0:
            print("No more room to spawn!")
            return
        elif n > empty_items_count > 0:
            n = empty_items_count

        positions = []
        while len(positions) < n:
            pos = choice(self.fieldItems)
            if not pos.not_empty:
                positions += [pos]
                pos.next_color = choice(list(self.images.colors))
                if self.SHOW_NEXT_SPAWN:
                    pos.update()

        self.next_spawn = positions

        if self.empty_items_count <= len(positions):
            self.loose()

    def item_clicked(self, item: FieldItem):
        if item.not_empty and not self.ready_to_move_item:
            print("Move it now")
            item.active_state = True
            self.ready_to_move_item = True
            self.item_to_move = item
            item.update()
        elif self.ready_to_move_item and item.not_empty and self.item_to_move is not None:
            self.item_to_move.active_state = False
            self.item_to_move.update()

            item.active_state = True
            self.ready_to_move_item = True
            self.item_to_move = item

        elif self.ready_to_move_item:
            path_to_take = self.find_paths(self.item_to_move, item)
            if len(path_to_take) > 0:
                timer = QTimer(self)
                self.move_timer = timer
                self.path_to_take = path_to_take
                self.move_timer_ticks_count = -1

                timer.setInterval(25)
                timer.timeout.connect(self.move_item_by_steps)
                timer.start()

    def move_item_by_steps(self):
        timer = self.move_timer
        self.move_timer_ticks_count += 1

        start_item_point = self.path_to_take[0]
        start_item = self.fieldItems2D[start_item_point.y()][start_item_point.x()]

        end_item_point = self.path_to_take[-1]
        end_item = self.fieldItems2D[end_item_point.y()][end_item_point.x()]

        # first iteration
        if self.move_timer_ticks_count == 0:
            current_point = self.path_to_take[0]
            next_point = self.path_to_take[1]
        # Normal transit move
        elif self.move_timer_ticks_count < len(self.path_to_take) - 1:
            current_point = self.path_to_take[self.move_timer_ticks_count]
            next_point = self.path_to_take[self.move_timer_ticks_count + 1]

        # Final step
        else:
            end_item.cancel_override()
            self.swap_items(start_item, end_item)
            start_item.reset()

            if not end_item.calculate_line():
                self.spawn_items()

            timer.stop()
            self.ready_to_move_item = False
            self.item_to_move = None
            self.path_to_take = None
            self.move_timer_ticks_count = 0
            return

        current_item = self.fieldItems2D[current_point.y()][current_point.x()]
        next_item = self.fieldItems2D[next_point.y()][next_point.x()]
        next_item.show_briefly(self.images.colors[start_item.color])
        if self.move_timer_ticks_count > 0:
            current_item.cancel_override()
            current_item.reset()
        current_item.update()
        next_item.update()
        pass
        # current_point = self.path_to_take[self.move_timer_ticks_count - 1]
        # next_point = self.path_to_take[self.move_timer_ticks_count]
        #
        # current_item = self.fieldItems2D[current_point.y()][current_point.x()]
        # next_item = self.fieldItems2D[next_point.y()][next_point.x()]
        #
        # next_item.show_briefly(self.images.colors[start_item.color])
        # if self.move_timer_ticks_count > 0:
        #     current_item.cancel_override()
        #     current_item.reset()
        # current_item.update()
        # next_item.update()

        # self.move_timer_ticks_count += 1

    def move_item_by_steps_o(self):
        timer = self.move_timer
        self.move_timer_ticks_count += 1
        if self.move_timer_ticks_count > len(self.path_to_take):
            item_point = self.path_to_take[-1]
            item = self.fieldItems2D[item_point.y()][item_point.x()]
            if not item.calculate_line():
                self.spawn_items()

            timer.stop()
            self.item_to_move = None
            self.path_to_take = None
            self.move_timer_ticks_count = 0
            return

        if self.move_timer_ticks_count == 1:
            current_point = self.path_to_take[0]
            next_point = self.path_to_take[1]
        else:
            current_point = self.path_to_take[self.move_timer_ticks_count - 2]
            next_point = self.path_to_take[self.move_timer_ticks_count - 1]

        current_item = self.fieldItems2D[current_point.y()][current_point.x()]
        next_item = self.fieldItems2D[next_point.y()][next_point.x()]
        self.swap_items(current_item, next_item)

    def find_paths(self, start: QObject, end: QObject = None):
        field_map = [[i.not_empty for i in row] for row in self.fieldItems2D]

        moves = CoordinatesMoves
        possible_moves = [moves.RIGHT, moves.DOWN, moves.LEFT, moves.UP]
        directions = [QPoint(*m.value) for m in possible_moves]
        field_rect = QRect(0, 0, self.width, self.height)

        start_point = QPoint(start.x, start.y)
        if end:
            end_point = QPoint(end.x, end.y)
        else:
            end_point = QPoint()

        paths = [[start_point]]
        last_paths = paths
        visited_points = set()
        path_found = False
        found_path = []

        while not path_found and len(last_paths) > 0:
            paths.sort(key=lambda x, end=end_point: (x[-1] - end).manhattanLength(), reverse=True)
            last_paths = []
            for path in paths:
                last_point = path[-1]
                for d in directions:
                    next_point = last_point + d
                    if (field_rect.contains(next_point) and
                            not field_map[next_point.y()][next_point.x()] and
                            not str(next_point) in visited_points
                        ):

                        visited_points.add(str(next_point))
                        new_path = deepcopy(path + [next_point])
                        last_paths.append(new_path)
                        if next_point == end_point:
                            return new_path
            else:
                paths = last_paths
                pass

            if len(last_paths) == 0 and not path_found:
                break
        return found_path

    def swap_items(self, item_from: FieldItem, item_to: FieldItem):
        if item_to.not_empty:
            print(f"{item_to} must be empty")
            return

        item_to.spawn_item(item_from.color)
        item_from.reset()
        item_from.update()
        self.ready_to_move_item = False
        self.update()

    def win(self):
        self.game_status = GameStatus.WON
        self.sounds.win.play()
        # print("You have won!")
        self.stop_game()
        self.game_ended.emit()
        self.game_status_changed.emit(self.game_status)

    def loose(self):
        self.game_status = GameStatus.LOST
        print("You loose!")
        self.game_run = False
        self.game_ended.emit()
        self.game_status_changed.emit(self.game_status)

    def start_game(self):
        self.game_reset.emit()
        self.game_status = GameStatus.RUNNING
        self.game_run = True
        self.game_started.emit()

    def stop_game(self):
        self.game_run = False
        self.timer = QTimer(self)
        self.timer.singleShot(3000, self.reset_game)

    def reset_game(self):
        try:
            del self.timer
        except Exception:
            pass
        list(map(FieldItem.reset, self.fieldItems))
        self.game_status = GameStatus.RUNNING
        list(map(FieldItem.reset, self.fieldItems))
        self.game_status_changed.emit(self.game_status)
        self.scores = 0
        self.game_reset.emit()
        self.ready_to_move_item = False
        self.item_to_move = None
        self.spawn_items()


# TODO
class StatusBar(QWidget):
    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        self.images = self.parent().images

        layout = QHBoxLayout()
        self.setLayout(layout)

        self.scores_counter = QLCDNumber(self)
        self.scores_counter.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.scores_counter, alignment=Qt.AlignLeft)

    def update_counter(self, value):
        self.scores_counter.display(value)


# TODO
class GameActions(QObject):
    def __init__(self, *args, **kwargs):
        super(GameActions, self).__init__(*args, **kwargs)
        images = self.parent().images

        self.reset = QAction(QIcon(QPixmap.fromImage(images.restart)), "Restart", self)

        self.difficulty = QActionGroup(self)
        self.easy = QAction(QIcon(QPixmap.fromImage(images.easy)), "Easy", self)
        self.difficulty.addAction(self.easy)

        self.medium = QAction(QIcon(QPixmap.fromImage(images.medium)), "Medium", self)
        self.difficulty.addAction(self.medium)

        self.hard = QAction(QIcon(QPixmap.fromImage(images.hard)), "Hard", self)
        self.difficulty.addAction(self.hard)
        [a.setCheckable(True) for a in self.difficulty.actions()]
        self.easy.setChecked(True)

        self.toggleSound = QAction("Sounds", self)
        self.toggleSound.setIcon(QIcon(QPixmap.fromImage(images.audio_on)))
        self.toggleSound.setCheckable(True)
        self.toggleSound.setChecked(True)

        self.exit = QAction(QIcon(QPixmap.fromImage(images.close)), "Exit", self)

        self.aboutDialog = QAction(QIcon(QPixmap.fromImage(images.about)), "About", self)

    def bind(self):
        parent = self.parent()
        self.exit.triggered.connect(parent.close)
        self.reset.triggered.connect(parent.game_field.reset_game)
        self.toggleSound.triggered.connect(parent.sounds.toggle_sound)
        self.toggleSound.triggered.connect(self.change_sound_icon)
        self.easy.triggered.connect(lambda p=parent: parent.set_difficulty(GameDifficulty.EASY))
        self.medium.triggered.connect(lambda p=parent: parent.set_difficulty(GameDifficulty.MEDIUM))
        self.hard.triggered.connect(lambda p=parent: parent.set_difficulty(GameDifficulty.HARD))
        self.aboutDialog.triggered.connect(parent.show_about_dialog)

    def change_sound_icon(self, val):
        if val:
            self.toggleSound.setIcon(QIcon(QPixmap.fromImage(self.parent().images.audio_on)))
        else:
            self.toggleSound.setIcon(QIcon(QPixmap.fromImage(self.parent().images.audio_off)))


# TODO
class GameMenu(QObject):
    def __init__(self, *args, **kwargs):
        super(GameMenu, self).__init__(*args, **kwargs)
        parent = self.parent()
        actions = parent.game_actions

        parent_menu = self.parent().menuBar().addMenu("&File")
        parent_menu.addAction(actions.reset)

        parent_menu.addAction(actions.toggleSound)

        difficulty_menu = parent_menu.addMenu("&Difficulty")
        difficulty_menu.addActions(actions.difficulty.actions())

        parent_menu.addMenu(difficulty_menu)
        parent_menu.addAction(actions.exit)

        help_menu = self.parent().menuBar().addMenu("&Help")
        about = actions.aboutDialog
        help_menu.addAction(about)


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.images = Images()
        self.sounds = Sounds()
        # self.setWindowIcon(QIcon(QPixmap.fromImage(self.images.dynamite)))
        self.setWindowTitle("Lines")
        # self.game_actions = GameActions(self)
        # self.menu = GameMenu(self)
        self.difficulty = GameDifficulty.EASY

        self.initialize()

    def initialize(self):
        self.mainWidget = QWidget(self)

        height, width = self.difficulty.value
        self.game_field = GameField(height=height, width=width, parent=self)
        self.game_field.reset_game()

        layout = QVBoxLayout(self.mainWidget)
        self.mainWidget.setLayout(layout)

        self.status_bar = StatusBar(self)
        layout.addWidget(self.status_bar)
        self.game_field.scores_updated.connect(self.status_bar.update_counter)

        # self.game_actions.bind()

        layout.addWidget(self.game_field)

        self.setCentralWidget(self.mainWidget)
        self.mainWidget.resize = self.game_field.resize
        self.resize = self.game_field.resize
        self.show()

    def set_difficulty(self, difficulty: GameDifficulty = GameDifficulty.EASY):
        self.difficulty = difficulty
        self.layout().removeWidget(self.mainWidget)
        self.mainWidget.setParent(None)
        self.initialize()

    def show_about_dialog(self):
        self.about_dialog = AboutDialog(self)
        self.about_dialog.exec_()


app = QApplication(sys.argv)
window = MainWindow()
explorer = GamePathExplorer(window)

# explorer.show()

app.exec_()
