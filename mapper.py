from PyQt5 import QtWidgets, QtCore, QtGui

import nodeWidget, edgeWidget
import stateMachine
import fileIO
import edgeDetailDialog
import anchor
import tools
import math

# TODO: seperate map actor and drawing into seperate classes

class FreeFormMap(QtWidgets.QWidget):
    def __init__(self, map=None, mapType=None, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.nodes = {} # List of all nodes, with their id as the key
        self.edges = {} # List of edges currently being drawn
        self.mapNodes = map["nodes"] if map is not None else []
        self.mapEdges = map["edges"] if map is not None else []

        self.enableAA = False
        self.gridEnabled = False
        self.gridSize = 100
        self.inEditMode = False

        self.selected = None # Holds selected node

        self.root = None # Holds root node in a mindmap

        self.polys = []

        self.offset = QtCore.QPoint()
        self.zoomLevel = 1

        self.textEdit = QtWidgets.QLineEdit(parent=self)
        self.textEdit.resize(100, 30)
        self.textEdit.editingFinished.connect(self.textEditFinish)
        self.textEdit.hide()

        # Set up state machine
        self.stateMachine = stateMachine.StateMachine(parent=self)

        self.anchor = anchor.QAnchorWidget(parent=self)

        if mapType == "mindmap":
            if map is not None:
                for node in self.mapNodes:
                    # TODO: implement positioning for mindmaps
                    pos = [300, 300]
                    if node["data"]["parent"] is None:
                        pos = [int(self.width()/2), int(self.height()/2)]
                    x = self.addNode(node["name"], pos, node["connections"], data=node["data"], id=node["id"])
                    if node["data"]["parent"] is None:
                        self.root = x
        elif mapType == "freemap":
            if map is not None:
                # Adds all of the nodes in the map to the mapper object
                for node in self.mapNodes:
                    self.addNode(node["name"], node["position"], node["connections"], data=node["data"], id=node["id"], push=False)
                # Loops over all edges in the map and applies their data to the correct edges in the mapper object
                for edge in self.mapEdges:
                    id = edge["id"] if "id" in edge else tools.generateId(self)
                    data = edge["data"] if "data" in edge else None
                    self.addConnection(self.nodes[edge["node1"]], self.nodes[edge["node2"]], id=id, data=data)

        if map is None:
            id1 = tools.generateId(self)
            id2 = tools.generateId(self)
            self.root = self.addNode(str(id1), [300, 300], None, id=id1)
            self.root1 = self.addNode(str(id2), [300, 400], [self.root.id], id=id2)
            self.addConnection(self.root, self.root1)

        #self.overlay = OverlayWidget(self)

        self.snapMode = False
        self.tempLine = None

        self.setFocus()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing, self.enableAA)
        qp.setPen(QtGui.QPen(QtGui.QColor(128, 255, 128), 10))

        for node in self.nodes.values():
            node.update()
        for edge in self.edges.values():
            edge.updatePositions()

        self.polys = []

        if self.gridEnabled:
            qp.setPen(QtGui.QPen(QtGui.QColor(64, 64, 64), 1))
            size = self.parent.size()
            localGridSize = self.gridSize * self.zoomLevel
            for x in range(math.ceil(size.width() / localGridSize)):
                lineOffset = (x*localGridSize) + (self.offset.x() % localGridSize)
                qp.drawLine(lineOffset, 0, lineOffset, size.height())
            
            for y in range(math.ceil(size.height() / localGridSize)):
                lineOffset = (y*localGridSize) + (self.offset.y() % localGridSize)
                qp.drawLine(0, lineOffset, size.width(), lineOffset)
            

        if self.tempLine is not None:
            qp.drawLine(self.tempLine[0], self.tempLine[1])

        qp.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 0), 15))

        for edge in self.edges.values():
            for poly in edge.generatePolys():
                path = QtGui.QPainterPath()
                color = QtGui.QColor(edge.color) if edge.color is not None else QtGui.QColor(128, 255, 128)
                color = QtGui.QColor(255, 255, 255) if self.selected is edge else color
                qp.setBrush(color)
                path.setFillRule(QtCore.Qt.WindingFill)
                path.addPolygon(poly[0].united(poly[1]))
                self.polys.append(poly)
                qp.drawPath(path)

        for node in self.nodes.values():
            if node == self.selected:
                qp.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
            else:
                qp.setBrush(QtGui.QBrush(QtGui.QColor(node.color)))
            path = QtGui.QPainterPath()
            path.addRoundedRect(node.pos().x(), node.pos().y(), 100 * self.zoomLevel, 100 * self.zoomLevel, 10, 10)
            qp.drawPath(path)

            if not (self.inEditMode and self.selected == node):
                qp.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 10))
                qp.drawText(node.pos().x(), node.pos().y(), 100*self.zoomLevel, 100*self.zoomLevel, QtCore.Qt.TextWordWrap | QtCore.Qt.AlignCenter, node.name)
                qp.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 0))

        qp.setPen(QtGui.QPen(QtGui.QColor(255, 128, 128), 10))
        qp.drawEllipse(self.offset, 10, 10)

        qp.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 10))
        qp.drawText(1000, 100, f"Zoom level: {self.zoomLevel}")
        qp.drawText(1000, 150, f"Anchor: {self.anchor.widgetPosition}")
        qp.drawText(1000, 200, f"Offset: {self.offset.x()}, {self.offset.y()}")
        node = list(self.nodes.values())[0]
        qp.drawText(1000, 250, f"Node X: {((node.position[0] + self.offset.x()) - self.anchor.widgetPosition[0]) * self.zoomLevel}")
        qp.drawText(1000, 300, f"Pos: {node.pos().x()}, {node.pos().y()}")

        qp.end()

    def updateSelection(self, newSelection):
        self.selected = newSelection
        self.update()

    def addNode(self, name, position, connections, data=None, id=None, push=True, fromExisting=True):
        if id is None:
            newId = tools.generateId(self)
        else:
            newId = id

        # Instantiate the node and update possible parents or add to roots list
        connectionList = connections if connections is not None else []
        newNode = nodeWidget.QNodeWidget(newId, name, position, connectionList, data, parent=self)
        self.nodes[newId] = newNode
        if not fromExisting:
            for connection in connectionList:
                if type(connection) == int:
                    connection = self.nodes[connection]
                self.addConnection(newNode, connection)

        if push:
            self.stateMachine.addNode(fileIO.serializeNode(self, newNode), origin="mapper.py:addNode")

        return newNode

    def addConnection(self, node1, node2, id=None, data=None):
        if id is None:
            newId = tools.generateId(self)
        else:
            newId = id

        for edge in self.edges.values():
            if edge == (node1, node2):
                return
        node1.connections.append(node2.id)
        node1.connections = list(dict.fromkeys(node1.connections))
        node2.connections.append(node1.id)
        node2.connections = list(dict.fromkeys(node2.connections))
        lineEdit = QtWidgets.QLineEdit(self)
        edge = edgeWidget.QEdgeWidget(newId, "", node1, node2, lineEdit, data=data, parent=self)
        self.edges[newId] = edge
        self.update()

    def createNewNode(self):
        connection = []
        # noinspection PyUnresolvedReferences
        if self.selected is None:
            pos = [self.mapFromGlobal(QtGui.QCursor.pos()).x(), self.mapFromGlobal(QtGui.QCursor.pos()).y()]
        elif type(self.selected) == nodeWidget.QNodeWidget:
            pos = [self.selected.widgetPosition[0], self.selected.widgetPosition[1] + 150]
            connection.append(self.selected.id)
        elif type(self.selected) == edgeWidget.QEdgeWidget:
            pos = [ self.selected.lineEdit.pos().x() + self.offset.x(), self.selected.lineEdit.pos().y() + self.offset.y() ]
        self.addNode("", pos, connection, fromExisting=False)

    def setEditNode(self, edit):
        if self.selected is not None:
            if edit is True:
                self.inEditMode = True
                if type(self.selected) == nodeWidget.QNodeWidget:
                    self.textEdit.move(
                        self.selected.pos().x(),
                        self.selected.pos().y() + 100*self.zoomLevel/2 - 10
                    )
                    self.textEdit.resize(100 * self.zoomLevel, 30)
                    self.textEdit.setText(self.selected.name)
                    self.textEdit.show()
                    self.textEdit.setFocus()
            else:
                self.inEditMode = False
                if type(self.selected) == nodeWidget.QNodeWidget:
                    self.textEdit.hide()
                else:
                    pass
            self.selected.update()
            self.update()

    def textEditFinish(self):
        self.selected.updateName(self.textEdit.text())

    def setEditEdge(self, edit):
        if self.selected is not None:
            if edit is True:
                self.inEditMode = True
                self.selected.label.hide()
                self.selected.textEdit.show()
                self.selected.textEdit.setFocus()
            else:
                self.inEditMode = False
                newText = self.selected.textEdit.text()
                self.selected.text = newText
                self.selected.label.setText(newText)
                self.selected.label.show()
                self.selected.textEdit.hide()
            self.selected.update()
            self.update()

    def deleteNode(self, node):
        self.nodes.pop(node.id)
        node.setParent(None)
        node.deleteLater()
        self.updateSelection(None)
    
    def deleteCurrentNode(self):
        if self.selected is not None:
            connections = []
            for node in self.nodes.values():
                if node is not self.selected:
                    if self.selected.id in node.connections:
                        connections.append(node.id)
            self.selected.connections = connections
            # When deleting a node, we save its serialized data to the state machine so we can rebuild it later
            newEdges = {}
            deletedEdges = {}
            for key, edge in self.edges.items():
                if edge.node1 != self.selected and edge.node2 != self.selected:
                    newEdges[key] = edge
                else:
                    deletedEdges[key] = edge
            self.edges = newEdges
            serialized = []
            for edge in deletedEdges.values():
                serialized.append(fileIO.serializeEdge(edge))
            self.stateMachine.deleteNode(fileIO.serializeNode(self, self.selected), serialized, origin="mapper.py:deleteCurrentNode")
            for edge in deletedEdges.values():
                edge.destroy()
                del edge
            self.deleteNode(self.selected)

    def deleteConnection(self, edge):
        edge.node1.connections = [connection for connection in edge.node1.connections if connection != edge.node2.id]
        edge.node2.connections = [connection for connection in edge.node2.connections if connection != edge.node1.id]
        self.edges.pop(edge.id)
        self.stateMachine.deleteEdge(fileIO.serializeEdge(edge), origin="mapper.py:deleteConnection")
        edge.destroy()
        del edge

    def dissolveRedirect(self, redirect):
        # TODO: add proper state machine atoms for redirects
        edge = self.edges[redirect.parentEdge]
        edge.data["redirects"] = [x for x in edge.data["redirects"] if x != redirect.id]
        self.deleteNode(redirect)

    def rebuildNode(self, data, edges=None):
        position = [
            data["position"][0] + self.offset.x(),
            data["position"][1] + self.offset.y()
        ]
        self.addNode(data["name"], position, data["connections"], data=data["data"], id=data["id"], push=False)
        if edges is not None:
            for edge in edges:
                self.addConnection(self.nodes[edge["node1"]], self.nodes[edge["node2"]], edge["id"], edge["data"])

    def undo(self):
        atom = self.stateMachine.undo()
        if atom is not None:
            print(atom)
            if atom["type"] == "editNode":
                self.nodes[atom["id"]].applyChange(atom["old"])
            elif atom["type"] == "addNode":
                self.deleteNode(self.nodes[atom["data"]["id"]])
            elif atom["type"] == "deleteNode":
                edges = atom["edges"] if "edges" in atom else None
                self.rebuildNode(atom["data"], edges)
            elif atom["type"] == "editEdge":
                atom["edge"].applyChange(atom["old"])
            elif atom["type"] == "addEdge":
                self.deleteEdge(atom["old"])
            elif atom["type"] == "deleteEdge":
                data = atom["edge"]["data"] if "data" in atom["edge"] else None
                self.addConnection(self.nodes[atom["edge"]["node1"]], self.nodes[atom["edge"]["node2"]], id=atom["edge"]["id"], data=data)
            else:
                raise NotImplementedError("Atom type not yet implemented")
            self.update()

    def redo(self):
        atom = self.stateMachine.redo()
        if atom is not None:
            print(atom)
            if atom["type"] == "editNode":
                self.nodes[atom["id"]].applyChange(atom["new"])
            elif atom["type"] == "deleteNode":
                self.deleteNode(self.nodes[atom["data"]["id"]])
            elif atom["type"] == "addNode":
                print(atom["data"])
                self.rebuildNode(atom["data"])
            elif atom["type"] == "editEdge":
                atom["edge"].applyChange(atom["new"])
            elif atom["type"] == "deleteEdge":
                self.deleteEdge(atom["old"])
            elif atom["type"] == "addEdge":
                self.rebuildEdge(atom["old"])
            else:
                raise NotImplementedError("Atom type not yet implemented")
            self.update()

    def mouseDoubleClickEvent(self, event):
        localPos = QtCore.QPoint(event.pos().x(), event.pos().y())
        for poly in self.polys:
            if poly[0].containsPoint(localPos, QtCore.Qt.OddEvenFill) or poly[1].containsPoint(localPos, QtCore.Qt.OddEvenFill):
                if event.buttons() == QtCore.Qt.LeftButton:
                    dialog = edgeDetailDialog.QEdgeDetailDialog(poly[2])
                    dialog.exec()
                    if dialog.apply:
                        self.stateMachine.editEdge(poly[2], dialog.edgeDeltaOld, dialog.edgeDeltaNew, origin="edgeWidget.py:mouseDoubleClickEvent")
                        poly[2].applyChange(dialog.edgeDeltaNew)
                    self.update()

    def mousePressEvent(self, event):
        localPos = QtCore.QPoint(event.pos().x(), event.pos().y())
        self.setFocus()
        self.setEditNode(False)
        self.updateSelection(None)
        for poly in self.polys:
            if poly[0].containsPoint(localPos, QtCore.Qt.OddEvenFill) or poly[1].containsPoint(localPos, QtCore.Qt.OddEvenFill):
                if event.buttons() == QtCore.Qt.LeftButton:
                    self.selected = poly[2]
        for node in self.nodes.values():
            if node.pos().x() < localPos.x() < node.pos().x() + 100 * self.zoomLevel:
                if node.pos().y() < localPos.y() < node.pos().y() + 100 * self.zoomLevel:
                    self.updateSelection(node)
                    self.selected.mousePressEvent(event)
                    break
        self.update()
        if self.selected is None and event.button() == QtCore.Qt.LeftButton:
            self.__mousePressPos = event.globalPos()
            self.__mouseMovePos = event.globalPos()
            self.startPos = event.globalPos()
            self.freeDrag = False

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.selected is None:
            # adjust offset from clicked point to origin of widget
            currPos = self.mapToGlobal(self.pos())
            globalPos = event.globalPos()
            if (globalPos - self.startPos).manhattanLength() > 5 or self.freeDrag:
                self.freeDrag = True
                diff = globalPos - self.__mouseMovePos
                delta = self.mapFromGlobal(currPos + diff)
                self.offset += diff
                for node in self.nodes.values():
                    node.moveDelta(diff.x(), diff.y())
                self.anchor.moveDelta(diff.x(), diff.y())
                self.__mouseMovePos = globalPos
        elif type(self.selected) == nodeWidget.QNodeWidget:
            self.selected.mouseMoveEvent(event)
        self.update()

    def wheelEvent(self, event):
        delta = round(event.angleDelta().y() / 1500, 3)
        print(delta)
        if 3 > self.zoomLevel + delta > 0.1:
            self.setZoomLevel(self.zoomLevel + delta)
            self.parent.zoomBox.setValue(self.zoomLevel)
    
    def setZoomLevel(self, level):
        s = (level - self.zoomLevel)
        self.zoomLevel = level
        for node in self.nodes.values():
            #node.updateZoomLevel(self.zoomLevel)
            x0 = ((((node.position[0] + self.offset.x()) - self.anchor.widgetPosition[0])) * self.zoomLevel) + self.offset.x()
            y0 = ((((node.position[1] + self.offset.y()) - self.anchor.widgetPosition[1])) * self.zoomLevel) + self.offset.y()
            node.moveNode(x0, y0, realPos=node.position)
            node.update()
        self.update()

    def handleAction(self, action, origin=None):
        if not self.inEditMode and self.hasFocus():
            if action == "createNode":
                self.createNewNode()
            elif action == "editNode":
                self.setEditNode(True)
            elif action == "deleteNode":
                self.deleteCurrentNode()
            elif action == "deleteSelected":
                if type(self.selected) == nodeWidget.QNodeWidget:
                    self.deleteCurrentNode()
                elif type(self.selected) == edgeWidget.QEdgeWidget:
                    self.deleteConnection(self.selected)
            else:
                raise NotImplementedError(f"Action {action} is not yet implemented.")
            self.update()

    def update(self):
        for edge in self.edges.values():
            edge.updatePositions()
        super().update()