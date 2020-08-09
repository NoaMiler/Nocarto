import random
from PyQt5 import QtWidgets, QtCore, QtGui

import nodeWidget

# TODO: Add support for abitrary connections

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
    def __init__(self, map, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.nodes = {}
        self.edges = []
        self.map = map

        self.cachedTreeBounds = [[0, 0], [0, 0]]

        self.setMinimumSize(1000, 1000)

        for node in map:
            # TODO: implement positioning for mindmaps
            self.addNode(node["text"], [node["position"], 300], node["connections"], id=node["id"])

        for node in self.nodes.values():
            self.addConnections(node)

        self.overlay = OverlayWidget(self)

        self.snapMode = True

        print(self.nodes)

    def oldGen(self):
        self.root = self.addNode("1", (200, 300), None)

        for x in range(0,5):
            connections = []
            #print(self.nodes)
            for y in range(0, random.randint(0, len(self.nodes))):
                connections.append(random.choice(list(self.nodes.keys())))
            print(connections)
            self.addNode(str(x), (random.randint(0, 500), random.randint(0, 500)), connections)


    def addNode(self, text, position, connections, *data, id=None):
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
        newNode = nodeWidget.QNodeWidget(newId, text, position, connectionList, *data, parent=self)
        self.nodes[newId] = newNode
        return newNode

    def addConnections(self, node):
        nodeId = node.id
        connections = node.connections
        if connections is not None:
            for connection in connections:
                self.edges.append((nodeId, connection))
    
    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing, True)
        qp.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 5))
        self.drawMap(event, qp)
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

            if self.snapMode:

                if e1[0] <= e2[0] - n1.width():
                    horPos = 1
                elif e1[0] >= e2[0] + n1.width():
                    horPos = 0            

                if e1[1] <= e2[1] - n1.height():
                    vertPos = 1
                elif e1[1] >= e2[1] + n1.height():
                    vertPos = 0
            
            qp.drawLine(e1[0] + n1.width() * horPos, e1[1] + n1.height() * vertPos, e2[0] + n2.width() * (1-horPos), e2[1] + n2.height() * (1-vertPos))


        qp.setBrush(QtGui.QColor(255, 0, 0))