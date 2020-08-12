import random
from PyQt5 import QtWidgets, QtCore, QtGui

import nodeWidget

class OverlayWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setMinimumSize(1000, 1000)

        self.parent=parent

        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

        self.circleSize = 20
        self.hcs = int(self.circleSize / 2)

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        #qp.fillRect(0, 0, 1000, 1000, QtGui.QBrush(QtGui.QColor(0, 64, 0)))
        qp.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
        qp.setPen(0)
        for id in self.parent.nodes:
            node = self.parent.nodes[id]
            pos = node.position
            qp.drawEllipse(pos[0] - self.hcs,                   pos[1] + node.height()/2 - self.hcs,    self.circleSize,    self.circleSize)
            qp.drawEllipse(pos[0] + node.width() - self.hcs,    pos[1] + node.height()/2 - self.hcs,    self.circleSize, self.circleSize)
            qp.drawEllipse(pos[0] + node.width()/2 - self.hcs,  pos[1]- self.hcs,                       self.circleSize,    self.circleSize)
            qp.drawEllipse(pos[0] + node.width()/2 - self.hcs,  pos[1] + node.height() - self.hcs,      self.circleSize, self.circleSize)
        qp.end()

class FreeFormMap(QtWidgets.QWidget):
    def __init__(self, map=None, mapType=None, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.nodes = {} # List of all nodes, with their id as the key
        self.edges = [] # List of edges currently being drawn
        self.map = map

        self.enableAA = False

        self.selected = None # Holds selected node

        self.root = None # Holds root node in a mindmap

        if mapType == "mindmap":
            if map is not None:
                for node in map:
                    # TODO: implement positioning for mindmaps
                    pos = [300, 300]
                    if node["data"]["parent"] is None:
                        pos = [int(self.width()/2), int(self.height()/2)]
                    x = self.addNode(node["text"], pos, node["connections"], data=node["data"], id=node["id"])
                    if node["data"]["parent"] is None:
                        self.root = x
        elif mapType == "freemap":
            if map is not None:
                for node in map:
                    self.addNode(node["text"], node["position"], node["connections"], data=node["data"], id=node["id"])

        for node in self.nodes.values():
            self.addConnections(node)

        #self.overlay = OverlayWidget(self)

        if map is None:
            self.root = self.addNode("test", [300, 300], None)

        self.tempLine = None
        self.snapMode = False

    
    def updateSelection(self, newSelection):
        if self.selected is not None:
            self.selected.setSelected(False)
        if newSelection is not None:
            newSelection.setSelected(True)

        self.selected = newSelection


    def addNode(self, text, position, connections, data=None, id=None):
        # Generate a random id
        if id is None:
            newId = random.randint(0, 65535)

            # Check if it is unique, if not, generate a new one and repeat until unique is found
            idIsUnique = True
            for node in self.nodes.values():
                if node.id == newId:
                    idIsUnique = False
            while idIsUnique is False:
                newId = random.randint(0, 65535)
                for node in self.nodes.values():
                    if node.id == newId:
                        idIsUnique = False

        else:
            newId = id

        # Instantiate the node and update possible parents or add to roots list
        connectionList = connections if connections is not None else []
        newNode = nodeWidget.QNodeWidget(newId, text, position, connectionList, data, parent=self)
        self.nodes[newId] = newNode
        self.addConnections(newNode)
        return newNode

    def addConnections(self, node):
        nodeId = node.id
        connections = node.connections
        if connections is not None:
            for connection in connections:
                self.edges.append((nodeId, connection))
        
        #if node.data["parent"] is not None:
        #    self.nodes[node.data["parent"]].connections.append(nodeId)

    def addConnection(self, node1, node2):
        node1.connections.append(node2.id)
        node2.connections.append(node1.id)
        self.edges.append((node1.id, node2.id))
    
    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing, self.enableAA)
        qp.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 5))
        self.drawMap(event, qp)
        if self.tempLine is not None:
            qp.drawLine(self.tempLine[0], self.tempLine[1])
        qp.end()

    def drawMap(self, event, qp):
        #qp.fillRect(0, 0, self.width(), self.height()/2, QtGui.QBrush(QtGui.QColor(0, 64, 0)))
        #QtGui.QBrush(QtGui.QColor(0, 64, 0))
        linesToDraw = []
        for edges in self.edges:
            n1 = self.nodes[edges[0]]
            n2 = self.nodes[edges[1]]
            e1 = n1.position
            e2 = n2.position

            horPos = 0.5
            vertPos = 0.5
            
            qp.drawLine(e1[0] + n1.width() * horPos, e1[1] + n1.height() * vertPos, e2[0] + n2.width() * (1-horPos), e2[1] + n2.height() * (1-vertPos))


        qp.setBrush(QtGui.QColor(255, 0, 0))

    def mousePressEvent(self, event):
        self.setEditNode(False)
        self.updateSelection(None)

    def createNewNode(self):
        connection = [] if self.selected is None else [self.selected.id]
        pos = [300, 300] if self.selected is None else [self.selected.position[0], self.selected.position[1] + 150]
        self.addNode("", pos, connection)

    def setEditNode(self, edit):
        if self.selected is not None:
            if edit is True:
                self.selected.label.hide()
                self.selected.textEdit.show()
                self.selected.textEdit.setFocus()
            else:
                newText = self.selected.textEdit.text()
                self.selected.text = newText
                self.selected.label.setText(newText)
                self.selected.label.show()
                self.selected.textEdit.hide()
            self.selected.update()
            self.update()