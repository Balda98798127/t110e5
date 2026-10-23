import os, sys, json
from PyQt5 import QtCore, QtGui, QtWidgets, uic
import random, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(HERE, "..", "..", "resources", "media")

KINDS = {
    "Дорога": (0, "Rcrossroads.png", {}),
    "Дорога с обочиной": (0, "Rvertical.png", {"Обочина": "справа"}),
    "Пешеходный переход": (0, "Zvertical.png", {"Ориентация": "вертикальный"}),
    "Автомобиль": (1, "BCright.png", {"Цвет": "синий", "Направление": "вправо", "Скорость": "3"}),
    "Пешеход": (1, "Pedestrain.png", {}),
    "Светофор": (1, "TLgreen.png", {"Сигнал": "зелёный"}),
    "Знак 3.1 'Въезд запрещён'": (1, "Stop.png", {}),
    "Знак 3.2 'Движение запрещено'": (1, "Block.png", {}),
    "Пункт назначения": (1, "Start.png", {}),
}
CAR = {"вверх": "vertical", "вниз": "bottom", "влево": "left", "вправо": "right"}
LIGHT = {"зелёный": "TLgreen", "жёлтый": "TLyellow", "красный": "TLred"}
SIDE = {"справа": 0, "снизу": 90, "слева": 180, "сверху": 270}
CHOICES = {"Обочина": list(SIDE), "Ориентация": ["вертикальный", "горизонтальный"], "Цвет": ["синий", "красный"], "Направление": ["вверх", "вправо", "вниз", "влево"], "Скорость": ["1", "2", "3", "4", "5"], "Сигнал": ["зелёный", "жёлтый", "красный"]}
TURN = {"Автомобиль": "Направление", "Дорога с обочиной": "Обочина", "Пешеходный переход": "Ориентация", "Светофор": "Сигнал"}
CELL, ROWS, COLS = 35, 12, 20

def picture(obj):
    t, p = obj["type"], obj["props"]
    name = KINDS[t][1]
    if t == "Автомобиль":
        color = "BC" if p["Цвет"] == "синий" else "C"
        name = color + CAR.get(p["Направление"], "right") + ".png"
    elif t == "Светофор":
        name = LIGHT.get(p["Сигнал"], "TLgreen") + ".png"
    elif t == "Пешеходный переход" and p["Ориентация"] == "горизонтальный":
        name = "Zhorizontal.png"
    pix = QtGui.QPixmap(os.path.join(MEDIA, name))
    if t == "Дорога с обочиной":
        pix = pix.transformed(QtGui.QTransform().rotate(SIDE.get(p["Обочина"], 0)))
    return pix

################################################################################################

BIN = os.path.join(HERE, "..", "..", "bin")
os.makedirs(BIN, exist_ok=True)
db = sqlite3.connect(os.path.join(BIN, "training.db"))
db.executescript("""
CREATE TABLE IF NOT EXISTS runs (          
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started TEXT DEFAULT (datetime('now','localtime')),
    episodes INTEGER, alpha REAL, gamma REAL,
    result TEXT);
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES runs(id),
    episode INTEGER, steps INTEGER, reward REAL, reached INTEGER);
""")
MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1)]

################################################################################################

class Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(HERE, "city.ui"), self)
        self.setWindowIcon(QtGui.QIcon(os.path.join(MEDIA, "GCicon.ico")))
        self.layers = [{}, {}]
        self.current = None
        self.listObjects.addItems(["Выбор объекта", "Ластик"])
        for name, (_, img, _) in KINDS.items():
            icon = QtGui.QIcon(os.path.join(MEDIA, img))
            self.listObjects.addItem(QtWidgets.QListWidgetItem(icon, name))
        self.listObjects.setCurrentRow(0)
        self.scene = QtWidgets.QGraphicsScene(0, 0, COLS * CELL, ROWS * CELL)
        self.viewMap.setScene(self.scene)
        self.viewMap.viewport().installEventFilter(self)
        QtWidgets.QShortcut(QtGui.QKeySequence("R"), self, self.turn_object)
        QtWidgets.QShortcut(QtGui.QKeySequence("Delete"), self, self.delete_object)
        self.tableProps.itemChanged.connect(self.props_changed)
        self.btnSave.clicked.connect(self.save_map)
        self.btnLoad.clicked.connect(self.load_map)
        self.btnClear.clicked.connect(self.clear_map)
        self.start = None
        self.btnTrain.clicked.connect(self.start_training)
        self.show_runs()
        self.redraw()


    def top(self, cell):
        return self.layers[1].get(cell) or self.layers[0].get(cell)

    def eventFilter(self, obj, ev):
        if ev.type() in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseMove) \
                and ev.buttons() & QtCore.Qt.LeftButton:
            p = self.viewMap.mapToScene(ev.pos())
            r, c = int(p.y() // CELL), int(p.x() // CELL)
            if 0 <= r < ROWS and 0 <= c < COLS and (ev.type() == QtCore.QEvent.MouseButtonPress or (r, c) != self.current):
                self.click_cell(r, c)
        return False

    def click_cell(self, r, c):
        tool = self.listObjects.currentItem().text()
        self.current = (r, c)
        if tool == "Ластик":
            return self.delete_object()
        if tool in KINDS:
            layer = self.layers[KINDS[tool][0]]
            n = sum(o["type"] == tool for o in layer.values()) + 1
            props = {"Имя": f"{tool}{n}"}
            props.update(KINDS[tool][2])
            layer[(r, c)] = {"type": tool, "props": props}
            self.redraw()
            self.show_props()

    def delete_object(self):
        if self.current:
            layer = self.layers[1] if self.current in self.layers[1] else self.layers[0]
            layer.pop(self.current, None)
            self.redraw()
            self.show_props()

    def turn_object(self):
        obj = self.top(self.current)
        if obj and obj["type"] in TURN:
            key = TURN[obj["type"]]
            values = CHOICES[key]
            i = values.index(obj["props"][key]) if obj["props"][key] in values else -1
            obj["props"][key] = values[(i + 1) % len(values)]
            self.redraw()
            self.show_props()

    def redraw(self):
        self.scene.clear()
        pen = QtGui.QPen(QtGui.QColor("#dde3dd"))
        for c in range(COLS + 1):
            self.scene.addLine(c * CELL, 0, c * CELL, ROWS * CELL, pen)
        for r in range(ROWS + 1):
            self.scene.addLine(0, r * CELL, COLS * CELL, r * CELL, pen)
        for layer in self.layers:
            for (r, c), obj in layer.items():
                if obj["type"] == "Пешеходный переход":
                    asphalt = QtGui.QPixmap(os.path.join(MEDIA, "Rcrossroads.png"))
                    self.scene.addPixmap(asphalt).setPos(c * CELL, r * CELL)
                self.scene.addPixmap(picture(obj)).setPos(c * CELL, r * CELL)
        if self.current:
            r, c = self.current
            self.scene.addRect(c * CELL, r * CELL, CELL, CELL, QtGui.QPen(QtGui.QColor("red"), 2))

    def show_props(self):
        obj = self.top(self.current)
        self.labelSelected.setText(f"{obj['type']}, клетка {self.current}" if obj else "Пусто")
        self.tableProps.blockSignals(True)
        self.tableProps.setRowCount(0)
        for key, value in (obj["props"].items() if obj else []):
            row = self.tableProps.rowCount()
            self.tableProps.insertRow(row)
            name = QtWidgets.QTableWidgetItem(key)
            name.setFlags(QtCore.Qt.ItemIsEnabled)
            self.tableProps.setItem(row, 0, name)
            if key in CHOICES:
                box = QtWidgets.QComboBox()
                box.addItems(CHOICES[key])
                box.setCurrentText(value)
                box.currentTextChanged.connect(lambda v, k=key: self.set_prop(k, v))
                self.tableProps.setCellWidget(row, 1, box)
            else:
                self.tableProps.setItem(row, 1, QtWidgets.QTableWidgetItem(value))
        self.tableProps.blockSignals(False)

    def props_changed(self, item):
        self.set_prop(self.tableProps.item(item.row(), 0).text(), item.text().strip())

    def set_prop(self, key, value):
        self.top(self.current)["props"][key] = value
        self.redraw()

    def save_map(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить", "", "JSON (*.json)")
        if path:
            cells = [{"r": r, "c": c, "layer": i, **obj} for i, layer in enumerate(self.layers)
                     for (r, c), obj in layer.items()]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cells, f, ensure_ascii=False, indent=1)

    def load_map(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Открыть", "", "JSON (*.json)")
        if path:
            self.layers = [{}, {}]
            with open(path, encoding="utf-8") as f:
                for d in json.load(f):
                    self.layers[d["layer"]][(d["r"], d["c"])] = {"type": d["type"], "props": d["props"]}
            self.redraw()

    def clear_map(self):
        self.layers = [{}, {}]
        self.redraw()
        self.show_props()
#########################################################################################################
    def passable(self,cell):
        if cell not in self.layers[0]:
            return False
        thing = self.layers[1].get(cell)
        if not thing or cell == self.start:
            return True
        if thing["type"] == "Светофор":
            return thing["props"]["Сигнал"] != "красный"
        return thing["type"] == "Пункт назначения"

    def locate(self, kind):
        return next((cell for cell, o in self.layers[1].items() if o["type"] == kind), None)
#########################################################################################################
    def start_training(self):
        self.start, goal = self.locate("Автомобиль"), self.locate("Пункт назначения")
        if not self.start or not goal:
            QtWidgets.QMessageBox.warning(self, "Обучение", "Нужны автомобиль и пункт назначения")
            return
        episodes = self.spinEpisodes.value()
        alpha, gamma = self.spinAlpha.value(), self.spinGamma.value()
        run = db.execute("INSERT INTO runs(episodes, alpha, gamma, result) VALUES (?, ?, ?, ?)",
                        (episodes, alpha, gamma, "идёт обучение")).lastrowid
        db.commit()
        self.show_runs()
        q = {}
        for ep in range(1, episodes + 1):
            eps = max(0.05, 1 - ep/episodes)
            cell, total, reached = self.start, 0, False
            for step in range(1, 301):
                values = q.setdefault(cell, [0.0] * 4)
                if random.random() < eps:
                    a = random.randrange(4)
                else:
                    a = values.index(max(values))
                nxt = (cell[0] + MOVES[a][0], cell[1] + MOVES[a][1])
                if nxt == goal:
                    reward, reached = 100, True
                elif self.passable(nxt):
                    reward = -1
                else:
                    reward, nxt = -10, cell
                future = 0 if reached else gamma * max(q.setdefault(nxt, [0.0] * 4))
                values[a] += alpha * (reward + future - values[a])
                cell, total = nxt, total + reward
                if reached:
                    break
            db.execute("INSERT INTO episodes(run_id, episode, steps, reward, reached) "
                        "VALUES (?, ?, ?, ?, ?)", (run, ep, step, total, int(reached)))
            self.labelTrain.setText(f"Эпизод {ep} из {episodes}: шагов {step}, награда {total}")
            QtWidgets.QApplication.processEvents()
        self.redraw()
        path = self.show_path(q, goal)
        result = f"доехал за {len(path) - 1} шагов" if path[-1] == goal else "не доехал"
        db.execute("UPDATE runs SET result = ? WHERE id = ?", (result, run))
        db.commit()
        self.show_runs()
        self.labelTrain.setText("Обучени завершено: " + result)

    def show_path(self, q, goal):
        path, cell = [self.start], self.start
        while cell != goal and cell in q and len(path) < 300:
            values = q[cell]
            a = values.index(max(values))
            cell = (cell[0] + MOVES[a][0], cell[1] + MOVES[a][1])
            if cell in path or not (cell == goal or self.passable(cell)):
                break
            path.append(cell)
        brush = QtGui.QBrush(QtGui.QColor(255, 140, 0, 220))
        for r,c in path:
            self.scene.addEllipse(c * CELL + 12, r * CELL + 12, 11, 11, QtGui.QPen(QtCore.Qt.NoPen), brush)
        return path
    
    def show_runs(self):
        rows = db.execute(
            "SELECT r.id, r.started, r.episodes, r.alpha, r.gamma, r.result, "
            "COALESCE(SUM(e.reached), 0) FROM runs r LEFT JOIN episodes e ON e.run_id = r.id "
            "GROUP BY r.id ORDER BY r.id DESC LIMIT 20").fetchall()
        self.tableRuns.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                self.tableRuns.setItem(i, j, QtWidgets.QTableWidgetItem(str(value)))

app = QtWidgets.QApplication(sys.argv)
window = Window()
window.show()
sys.exit(app.exec_())


#sipPyTypeDict
#sipPyTypeDictRef