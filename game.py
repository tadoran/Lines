import sys
from itertools import chain, dropwhile, repeat
from random import randint, choice

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from enums import GameStatus, GameDifficulty, CoordinatesMoves
from resources import Images, Sounds

from about import Ui_Dialog


# TODO
class AboutDialog(QDialog, Ui_Dialog):
    def __init__(self, *args, **kwargs):
        super(AboutDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)


class FieldItem(QPushButton):
    changed = pyqtSignal(QObject)
    rightButtonPressed = pyqtSignal()

    def __init__(self, y, x, *args, **kwargs):
        super(FieldItem, self).__init__(*args, **kwargs)
        self.y = y
        self.x = x
        self.not_empty = False
        self.active_state = False
        self.color = None

        self.current_image = self.parent().images.empty

        sizePolicy = QSizePolicy.Expanding
        policy = QSizePolicy()
        policy.setHorizontalPolicy(sizePolicy)
        policy.setVerticalPolicy(sizePolicy)
        policy.setWidthForHeight(True)
        self.setSizePolicy(policy)

        self.pressed.connect(lambda item=self: item.parent().item_clicked(item))
        self.rightButtonPressed.connect(self.calculate_line)
        # self.parent().items_block_released.connect(self.release_block)

    def spawn_item(self, color: str = None):
        if not color:
            color = choice(list(self.parent().images.colors))

        self.color = color
        self.current_image = self.parent().images.colors[color]

        # print(color)
        self.not_empty = True
        self.update()

    def calculate_line(self):

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

            if line_elements_count >= 5:
                # print(f"There is a line {line_elements}")
                for line_element in line_elements:
                    line_element.reset()
                return

    def paintEvent(self, e: QPaintEvent):
        super().paintEvent(e)
        painter = QPainter(self)


        painter.drawImage(
            self.rect().marginsAdded(QMargins() - 5),
            self.current_image
        )
        if self.active_state:
            # brush = QBrush()
            pen = QPen()
            pen.setColor(QColor("#f5f2eb"))
            painter.setPen(pen)
            painter.drawRect(self.rect())
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

    def resizeEvent(self, e: QResizeEvent):
        w, h = e.size().width(), e.size().height()
        wh = min(w, h)
        new_size = QSize(wh, wh)
        e.accept()
        self.resize(new_size)

    @property
    def empty_items_count(self) -> int:
        count = sum([not i.not_empty for i in self.fieldItems])
        # print(count)
        return count

    def spawn_items(self, n: int = 5):
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

        for item in positions:
            item.spawn_item()

        if self.empty_items_count == 0:
            self.loose()

    def __init__(self, width=10, height=10, *args, **kwargs):
        super(GameField, self).__init__(*args, **kwargs)

        self.images = self.parent().images
        self.sounds = self.parent().sounds

        self.width = width
        self.height = height
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
                self.fieldItems2D[y].append(item)
                layout.addWidget(item, y, x)

        self.fieldItems = list(chain.from_iterable(self.fieldItems2D))
        # list(map(FieldItem.find_neighbours, self.fieldItems))

        self.game_ended.connect(self.stop_game)

    def item_clicked(self, item: FieldItem):
        # print(item)
        if item.not_empty and not self.ready_to_move_item:
            print("Move it now")
            item.active_state = True
            self.ready_to_move_item = True
            self.item_to_move = item
            item.update()

        elif self.ready_to_move_item:
            self.swap_items(self.item_to_move, item)
            self.spawn_items(5)

    # if self.game_run:
    #     if item.status != FieldItemState.EMPTY:
    #         return
    #     if item.has_mine and self.first_turn:
    #         self.sounds.pop.play()
    #         item.has_mine = False
    #         found_new_mine_spot = False
    #         while not found_new_mine_spot:
    #             current_item = choice(self.fieldItems)
    #             if not current_item.has_mine:
    #                 # print(f"Ha-ha, found mine on first turn! Ok, that mine was moved to {current_item}")
    #                 index = self.items_with_mines.index(item)
    #                 self.items_with_mines[index] = current_item
    #                 current_item.has_mine = True
    #                 found_new_mine_spot = True
    #         item.calculate()
    #
    #     elif item.has_mine:
    #         item.was_fatal_item = True
    #         self.sounds.blow.play()
    #         item.update()
    #         self.loose()
    #     elif item.visible:
    #         pass
    #     else:
    #         self.sounds.pop.play()
    #         item.calculate()
    #
    #     item.update()
    #     self.items_block_released.emit()
    #     self.first_turn = False
    #
    # elif self.game_status == GameStatus.RUNNING:
    #     self.first_turn = False
    #     self.start_game()
    #     self.item_clicked(item)

    def swap_items(self, item_from:FieldItem, item_to:FieldItem):
        if item_to.not_empty:
            print(f"{item_to} must be empty")
            raise ValueError(f"{item_to} must be empty")

        item_to.spawn_item(item_from.color)
        item_from.reset()
        item_from.update()
        item_to.calculate_line()
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
        self.game_reset.emit()
        self.ready_to_move_item = False
        self.item_to_move = None
        self.spawn_items(5)


# TODO
class StatusBar(QWidget):
    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        self.images = self.parent().images

        layout = QHBoxLayout()
        self.setLayout(layout)

        self.mines_counter = QLCDNumber(self)
        self.mines_counter.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.mines_counter, alignment=Qt.AlignLeft)

        self.img = QLabel(self)
        self.pixmaps = {"smile": QPixmap().fromImage(self.images.smile, Qt.AutoColor),
                        "dead": QPixmap().fromImage(self.images.dead, Qt.AutoColor),
                        "won": QPixmap().fromImage(self.images.win_smile, Qt.AutoColor)}
        self.set_smile(GameStatus.RUNNING)

        self.img.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.img)

        self.timer_counter = QLCDNumber(self)
        self.timer_counter.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.timer_counter, alignment=Qt.AlignRight)
        self.timer = QTimer(self)

    def set_smile(self, game_status: GameStatus):
        if game_status == GameStatus.RUNNING:
            self.img.setPixmap(self.pixmaps["smile"])
        elif game_status == GameStatus.WON:
            self.img.setPixmap(self.pixmaps["won"])
        elif game_status == GameStatus.LOST:
            self.img.setPixmap(self.pixmaps["dead"])
        self.img.update()

    def start_timer(self):
        self.end_timer()
        self.timer = QTimer(self)
        self.timer_counter.display(0)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(lambda x=self.timer_counter: x.display(x.value() + 1))
        self.timer.start()

    def end_timer(self):
        try:
            self.timer.stop()
            self.timer.disconnect()
            del self.timer
        except Exception:
            pass

    def update_counter(self, value):
        self.mines_counter.display(value)

    def reset(self):
        self.timer_counter.display(0)
        self.mines_counter.display(0)

    # def sizeHint(self):
    #     return QSize(40, 60)


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
        # self.status_bar = StatusBar(self)
        # layout.addWidget(self.status_bar)

        # self.game_actions.bind()

        layout.addWidget(self.game_field)

        # self.game_field.mines_count_changed.connect(self.status_bar.mines_counter.display)
        # self.game_field.game_started.connect(self.status_bar.start_timer)
        # self.game_field.game_ended.connect(self.status_bar.end_timer)
        # self.game_field.game_reset.connect(self.status_bar.reset)
        # self.game_field.game_status_changed.connect(self.status_bar.set_smile)

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

app.exec_()
