# -*- coding: utf-8 -*-
import socket
import time
import os
import math
import pygame
from pygame.locals import *
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from sys import exit
from thread import *
import threading
import datetime
from threading import Timer
from PyQt4 import QtGui,QtCore

#===========const defines============
COLOR_WHITE = (255,255,255)
COLOR_RED = (255,0,0)
COLOR_YELLOW = (255,255,0)
COLOR_BLACK = (0,0,0)
COLOR_GREEN = (0,255,0)
COLOR_BLUE = (0,255,255)
COLOR_CHOCOLATE = (139,69,19)
COLOR_GRAY = (138,138,138)

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 750
MAX_REAL_X = None
MAX_REAL_Z = None
MAX_BLK_ROW = None
MAX_BLK_COL = None
MAX_AOI_ROW = None
MAX_AOI_COL = None

DOUBLE_CLICK_DELAY = 0.2
PKG_HEAD_LEN = 3
BIN_RECV_LEN = 512
SYS_LOGFILE = "syslog." + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#============global values============
g_DrawStartRealPos = None
g_DrawEndRealPos = None
g_DrawRealXLen = None
g_DrawRealZLen = None
g_PlayCtrl = False
g_ProcessExit = None
g_MapBlockDict = {}
g_NetStreamBuffer = ""
g_EntityObjectDict = {}
g_EntityColors = {"player":COLOR_RED, "monster":COLOR_GREEN, "npc":COLOR_CHOCOLATE}
g_ChineseFont = None
g_MouseClickListener = None
g_SingleClickPosList = []
g_DoubleClickPosList = []
g_Socketfd = None
g_DebugWin = None
g_SceneID = None
g_QTSignalMgr = None
#============load map=================
def load_map(path):
    print "----load map start----"
    global MAX_BLK_ROW,MAX_BLK_COL
    f = open(path, "rb")
    MAX_BLK_ROW = int(f.readline())
    MAX_BLK_COL = int(f.readline())
    cx = float(f.readline())
    cz = float(f.readline())
    scale = int(f.readline())
    dct = {}
    for i in xrange(MAX_BLK_ROW):
        for j in xrange(MAX_BLK_COL):
            ch = ord(f.read(1))
            if ch != 0:
                if not dct.get(i, None):
                    dct[i] = []
                dct[i].append(j)
    f.close()

    blk = {}
    for r,c in dct.items():
        c.sort()
        start = None
        end = None
        lst = []
        for i,v in enumerate(c):
            if i == 0:
                start = v
                end = v
                continue
            if v-end > 1:
                lst.append((start,end))
                start = v
                end = v
            else:
                end = v
        if start != None:
            lst.append((start,end))
        blk[r] = lst

    for r,clst in blk.items():
        sz = r*MAX_REAL_Z/MAX_BLK_ROW
        ez = (r+1)*MAX_REAL_Z/MAX_BLK_ROW
        g_MapBlockDict[(sz,ez)] = []
        for t in clst:
            sx = t[0]*MAX_REAL_X/MAX_BLK_COL
            ex = t[1]*MAX_REAL_X/MAX_BLK_COL + MAX_REAL_X/MAX_BLK_COL
            g_MapBlockDict[(sz,ez)].append((sx,ex))

    print "----load map end--row:%d-col:%d--"%(MAX_BLK_ROW,MAX_BLK_COL)

#============pos methods========
def x_real2screen(x):
    return int((float(x)-g_DrawStartRealPos[0])*SCREEN_WIDTH/g_DrawRealXLen)

def z_real2screen(z):
    return int((float(z)-g_DrawStartRealPos[1])*SCREEN_HEIGHT/g_DrawRealZLen)

def pos_real2screen(pos):
    screen_x = x_real2screen(pos[0])
    screen_z = z_real2screen(pos[1])
    return (screen_x,screen_z)

def x_screen2real(x):
    return int(float(x)*g_DrawRealXLen/SCREEN_WIDTH + g_DrawStartRealPos[0])

def z_screen2real(z):
    return int(float(z)*g_DrawRealZLen/SCREEN_HEIGHT + g_DrawStartRealPos[1])

def pos_screen2real(pos):
    real_x = x_screen2real(pos[0])
    real_z = z_screen2real(pos[1])
    return (real_x,real_z)

def x_server2real(x):
    return int(x)

def z_server2real(z):
    return MAX_REAL_Z - int(z)

def x_real2server(x):
    return x

def z_real2server(z):
    return MAX_REAL_Z - z

def get_scnpos_aoirect(pos):
    pos = pos_screen2real(pos)
    sx = (pos[0]*MAX_AOI_COL/MAX_REAL_X)*(MAX_REAL_X/MAX_AOI_COL)
    ex = sx + MAX_REAL_X/MAX_AOI_COL
    sz = (pos[1]*MAX_AOI_ROW/MAX_REAL_Z)*(MAX_REAL_Z/MAX_AOI_ROW)
    ez = sz + MAX_REAL_Z/MAX_AOI_ROW
    return (sx,sz),(ex,ez)

def set_draw_realpos(stapos, endpos):
    global g_DrawStartRealPos,g_DrawEndRealPos,g_DrawRealXLen,g_DrawRealZLen
    g_DrawStartRealPos = stapos
    g_DrawEndRealPos = endpos
    g_DrawRealXLen = g_DrawEndRealPos[0] - g_DrawStartRealPos[0]
    g_DrawRealZLen = g_DrawEndRealPos[1] - g_DrawStartRealPos[1]
    global g_ChineseFont
    g_ChineseFont = pygame.font.Font("SIMSUN.TTC", 2*MAX_REAL_X/g_DrawRealXLen)

def init_draw_realpos():
    set_draw_realpos((0,0), (MAX_REAL_X,MAX_REAL_Z))

def set_draw_realpos_bymouse(sta_scnpos, end_scnpos):
    if is_on_lefttop(sta_scnpos, end_scnpos):
        stapos,_ = get_scnpos_aoirect(sta_scnpos)
        _,endpos = get_scnpos_aoirect(end_scnpos)
        set_draw_realpos(stapos, endpos)

def is_fullscreen_mode():
    return g_DrawStartRealPos==(0,0) and g_DrawEndRealPos==(MAX_REAL_X,MAX_REAL_Z)

def is_on_lefttop(posA, posB):
    if posA[0] < posB[0] and posA[1] < posB[1]:
        return True
    return False

def is_on_rightbelow(posA, posB):
    if posA[0] > posB[0] and posA[1] > posB[1]:
        return True
    return False

#============game draw methods=========
def game_draw_rect(surface, color, lt_pos, rb_pos, _width = 0):
    lt_pos = pos_real2screen(lt_pos)
    rb_pos = pos_real2screen(rb_pos)
    width = rb_pos[0] - lt_pos[0]
    height = rb_pos[1] - lt_pos[1]
    pygame.draw.rect(surface, color, (lt_pos,(width,height)), _width)

def game_draw_line(surface, color, sta_pos, end_pos, _width = 1):
    sta_pos = pos_real2screen(sta_pos)
    end_pos = pos_real2screen(end_pos)
    pygame.draw.line(surface, color, sta_pos, end_pos, _width)

def game_draw_circle(surface, color, center_pos, screen_radius):
    center_pos = pos_real2screen(center_pos)
    pygame.draw.circle(surface, color, center_pos, screen_radius)

#=========all class========
class CObject:
    def __init__(self, id, x, z, stype, radius, name):
        self.m_ID = id
        self.m_X = x
        self.m_Z = z
        self.m_DirX = 0
        self.m_DirZ = 0
        self.m_Type = stype
        self.m_Radius = radius or 200
        self.m_Name = name or ""

    def name(self):
        return self.m_Name

    def screen_radius(self):
        return self.m_Radius*SCREEN_WIDTH/g_DrawRealXLen

    def radius(self):
        return self.m_Radius

    def dir(self):
        return (self.m_DirX,self.m_DirZ)

    def setpos(self, x, z):
        msg = u'%s'%self.name() + " move from (%d,%d) to (%d,%d)"%(self.m_X,self.m_Z,x,z)
        g_QTSignalMgr.m_SglEditText.emit(QtCore.QString(msg), "a+")
        self.m_DirX = (x-self.m_X)*5
        self.m_DirZ = (z-self.m_Z)*5
        self.m_X = x
        self.m_Z = z

    def draw(self, surface):
        color = g_EntityColors.get(self.m_Type, COLOR_GREEN)
        text = g_ChineseFont.render(u'%s'%self.name(), True, color)
        scn_pos = pos_real2screen((self.m_X-20,self.m_Z-20))
        surface.blit(text, scn_pos)
        game_draw_circle(surface, color, (self.m_X,self.m_Z), self.screen_radius())
        dir_len = math.sqrt(self.m_DirX*self.m_DirX + self.m_DirZ*self.m_DirZ)
        dir_x = self.m_X
        dir_z = self.m_Z
        if dir_len > 0:
            K = self.radius()*3
            dir_x = self.m_X + self.m_DirX*K/dir_len
            dir_z = self.m_Z + self.m_DirZ*K/dir_len
        game_draw_line(surface, color, (self.m_X, self.m_Z), (dir_x, dir_z), MAX_REAL_X/g_DrawRealXLen)
        if self.is_on_choose():
            scn_pos = pos_real2screen((self.m_X,self.m_Z))
            lt_pos,rb_pos = get_scnpos_aoirect(scn_pos)
            game_draw_rect(surface, COLOR_GRAY, lt_pos, rb_pos, 3)

    def is_pos_inbody(self, pos):
        return math.pow(self.m_X-pos[0],2) + math.pow(self.m_Z-pos[1],2) <= self.radius()*self.radius()

    def is_on_choose(self):
        return self.m_ID == g_DebugWin.m_RoleID

    def is_player(self):
        return self.m_Type == "player"

    def is_monster(self):
        return self.m_Type == "monster"

    def is_npc(self):
        return self.m_Type == "npc"

    def outinfo(self):
        text = "ID: %d\n"%(self.m_ID)
        text = text + "Name: " + u'%s'%self.name() + "\n"
        text = text + "ServerPos: (%d,%d)\n"%(self.m_X,self.m_Z)
        text = text + "AoiBlock: %d(row) x %d(col)\n"%(self.m_Z*MAX_AOI_ROW/MAX_REAL_Z+1,self.m_X*MAX_AOI_COL/MAX_REAL_X+1)
        return text

def CreateObject(id, x, z, stype, radius=None, name=None):
    if not g_EntityObjectDict.get(id):
        g_EntityObjectDict[id] = CObject(id, x, z, stype, radius, name)

def GetObject(id):
    return g_EntityObjectDict.get(id, None)

def DelObject(id):
    if g_EntityObjectDict.get(id, None):
        del g_EntityObjectDict[id]

class CMouseClickListener:
    def __init__(self):
        self.m_ClickList = {1:[],2:[],3:[]}

    def add_pygame_event(self, button, pos):
        info = {"pos":pos,"timestamp":time.time()}
        lst = self.m_ClickList[button]
        if len(lst)>0 and info["timestamp"]-lst[-1]["timestamp"]<DOUBLE_CLICK_DELAY and info["pos"]==lst[-1]["pos"]:
            lst.pop(-1)
            self.on_event_doubleclick(button, pos)
        else:
            lst.append(info)

    def update(self, curtime):
        bak = self.m_ClickList
        self.m_ClickList = {}
        for button,lst in bak.items():
            idx = 0
            for i,info in enumerate(lst):
                if curtime-info["timestamp"] >= DOUBLE_CLICK_DELAY:
                    idx = i+1
                    self.on_event_singleclick(button, info["pos"])
                else:
                    break
            self.m_ClickList[button] = lst[idx:]

    def on_event_singleclick(self, button, pos):
        global g_SingleClickPosList,g_DoubleClickPosList
        if button == 1: #left
            if is_fullscreen_mode():
                g_SingleClickPosList.append(pos)
                if len(g_SingleClickPosList) > 2:
                    g_SingleClickPosList.pop(0)
                    g_SingleClickPosList.pop(0)
        elif button == 2: #middle
            g_SingleClickPosList = []
            g_DoubleClickPosList = []
            init_draw_realpos()
        elif button == 3: #right
            if len(g_SingleClickPosList) == 2:
                sta_pos,end_pos = g_SingleClickPosList
                g_SingleClickPosList = []
                set_draw_realpos_bymouse(sta_pos,end_pos)

    def on_event_doubleclick(self, button, pos):
        global g_DoubleClickPosList
        if button == 1:
            g_DoubleClickPosList.append(pos)
            if len(g_DoubleClickPosList) > 1:
                g_DoubleClickPosList.pop(0)

            real_pos = pos_screen2real(pos)
            for id,oRole in g_EntityObjectDict.items():
                if oRole.is_pos_inbody(real_pos):
                    g_DebugWin.onChooseRoleOK(id)
                    break

#============socket methods============
def handle_socket():
    while True:
        data = g_Socketfd.recv(BIN_RECV_LEN)
        if not data:
            break
        global g_NetStreamBuffer,g_PlayCtrl,g_SceneID
        global MAX_AOI_ROW,MAX_AOI_COL,MAX_REAL_X,MAX_REAL_Z,SYS_LOGFILE
        g_NetStreamBuffer = g_NetStreamBuffer + data
        cur_idx = 0
        total_len = len(g_NetStreamBuffer)
        while cur_idx < total_len:
            if cur_idx+PKG_HEAD_LEN > total_len:
                break
            pkg_len = int(g_NetStreamBuffer[cur_idx: cur_idx+PKG_HEAD_LEN])
            if cur_idx+PKG_HEAD_LEN+pkg_len > total_len:
                break
            pkg_str = g_NetStreamBuffer[cur_idx+PKG_HEAD_LEN: cur_idx+PKG_HEAD_LEN+pkg_len]
            lst = str.split(pkg_str, " ")
            cur_idx = cur_idx + PKG_HEAD_LEN + pkg_len
            if lst[0] == "setpos":
                uuid,x,z = lst[1:]
                id = int(uuid)
                x = x_server2real(x)
                z = z_server2real(z)
                obj = GetObject(id)
                if obj:
                    obj.setpos(x, z)
            elif lst[0] == "initmap":
                scene_id,max_x,max_z,view_x,view_z,blkfile = lst[1:]
                g_SceneID = int(scene_id)
                SYS_LOGFILE = SYS_LOGFILE + ".%d"%(g_SceneID)
                MAX_REAL_X = int(max_x)
                MAX_REAL_Z = int(max_z)
                MAX_AOI_ROW = MAX_REAL_Z/int(view_z)
                MAX_AOI_COL = MAX_REAL_X/int(view_x)
                os.system("ln -s -f ~/BnHServer/build/block_map/ ./")
                path = "block_map/" + blkfile + ".bytes"
                load_map(path)
                init_draw_realpos()
                g_PlayCtrl = True
                pygame.display.set_caption("Scene: "+blkfile)
            elif lst[0] == "addobj":
                stype,name,uuid,x,z = lst[1:]
                uuid = int(uuid)
                x = x_server2real(x)
                z = z_server2real(z)
                CreateObject(uuid, x, z, stype, name = name)
            elif lst[0] == "delobj":
                uuid = int(lst[1])
                DelObject(uuid)

        g_NetStreamBuffer = g_NetStreamBuffer[cur_idx:]
    process_exit()
    print "socket disconnect!!!!!"

def run_socket_thread():
    global g_Socketfd
    fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    fd.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    fd.bind(("0.0.0.0", 9203))
    fd.listen(1)
    print "Wait Server Connect...\n"
    g_Socketfd,addr = fd.accept()
    print 'Connected Succeed with ' + addr[0] + ':' + str(addr[1])
    start_new_thread(handle_socket,())

#============PyQt4================
class CQTSignalMgr(QtCore.QObject):
    m_SglEditText = QtCore.pyqtSignal(QtCore.QString, str, name="editext")

class CDebugWin(QtGui.QWidget):

    def __init__(self):
        super(CDebugWin, self).__init__()
        self.initAttr()
        self.initUI()

    def initAttr(self):
        self.m_RoleID = None
        self.m_ChooseRoleStatus = 0

    def initUI(self):
        hbox = QtGui.QHBoxLayout() #水平的
        vbox1 = QtGui.QVBoxLayout() #竖直的
        vbox2 = QtGui.QVBoxLayout()
        vbox3 = QtGui.QVBoxLayout()

        self.m_ChooseRoleButton = QtGui.QPushButton(u'选取主角',self)
        self.m_ChooseRoleButton.clicked.connect(self.onClickChooseRole)
        self.m_TransRoleButton = QtGui.QPushButton(u'传送',self)
        self.m_TransRoleButton.clicked.connect(self.onTransRole)
        self.m_PauseButton = QtGui.QPushButton(u'暂停',self)
        self.m_PauseButton.clicked.connect(self.onPause)
        self.m_ChooseShowComBox = QtGui.QComboBox(self)
        self.m_ChooseShowComBox.addItem(u'场景信息')
        self.m_ChooseShowComBox.addItem(u'主角信息')
        self.connect(self.m_ChooseShowComBox, QtCore.SIGNAL('activated(QString)'), self.onChooseShow)
        vbox1.addWidget(self.m_ChooseRoleButton)
        vbox1.addStretch(1)
        vbox1.addWidget(self.m_TransRoleButton)
        vbox1.addStretch(1)
        vbox1.addWidget(self.m_ChooseShowComBox)
        vbox1.addStretch(1)
        vbox1.addWidget(self.m_PauseButton)
        vbox1.addStretch(1)

        LabelA = QtGui.QLabel(u'信息板', self)
        self.m_OutTextEdit = QtGui.QTextEdit()
        self.m_OutTextEdit.setReadOnly(True)
        self.m_OutTextEdit.setPlainText("...")
        vbox2.addWidget(LabelA)
        vbox2.addWidget(self.m_OutTextEdit)

        LabelB = QtGui.QLabel(u'调试窗', self)
        self.m_DebugTextEdit = QtGui.QTextEdit()
        self.m_DebugTextEdit.setReadOnly(True)
        self.m_DebugTextEdit.setPlainText("...")
        self.m_LogDebugButton = QtGui.QPushButton(u'打印Log',self)
        self.m_LogDebugButton.clicked.connect(self.onLogDebug)
        self.m_ClearDebugButton = QtGui.QPushButton(u'清屏',self)
        self.m_ClearDebugButton.clicked.connect(self.onClearDebug)
        vbox3.addWidget(LabelB)
        vbox3.addWidget(self.m_DebugTextEdit)
        vbox3.addWidget(self.m_LogDebugButton)
        vbox3.addWidget(self.m_ClearDebugButton)

        hbox.addLayout(vbox1,1)
        hbox.addLayout(vbox2,2)
        hbox.addLayout(vbox3,2)
        self.setLayout(hbox)
        self.setGeometry(100, 100, 800, 500)
        self.setWindowTitle('DebugWin')

    def closeEvent(self, event):
        super(CDebugWin, self).closeEvent(event)
        process_exit()

    def onPause(self):
        global g_PlayCtrl
        g_PlayCtrl = not g_PlayCtrl
        if g_PlayCtrl:
            self.m_PauseButton.setText(u'暂停')
        else:
            self.m_PauseButton.setText(u'播放')

    def onLogDebug(self):
        self.m_LogDebugButton.setText(u'打印中...')
        txt = self.m_DebugTextEdit.toPlainText()
        self.m_DebugTextEdit.setPlainText("")
        syslog_file(txt)
        self.m_LogDebugButton.setText(u'打印Log')

    def onClearDebug(self):
        self.m_DebugTextEdit.setPlainText("")

    def onChooseShow(self, text):
        if text == u'主角信息':
            oRole = self.getRole()
            if oRole:
                self.m_OutTextEdit.setPlainText(oRole.outinfo())
            else:
                self.m_OutTextEdit.setPlainText(u"主角暂无")
        elif text == u'场景信息':
            if not g_SceneID:
                self.m_OutTextEdit.setPlainText(u'服务器未连接')
                return
            text = u"场景ID:%d\n"%(g_SceneID)
            text = text + u"地图真实尺寸: %d(x) x %d(z)\n"%(MAX_REAL_X,MAX_REAL_Z)
            text = text + u"地图阻挡格个数: %d(row) * %d(col)\n"%(MAX_BLK_ROW,MAX_BLK_COL)
            text = text + u"地图AOI化块: %d(row) * %d(col)\n"%(MAX_AOI_ROW,MAX_AOI_COL)
            text = text + u"实体总数:%d\n"%(len(g_EntityObjectDict))
            player_num = 0
            monster_num = 0
            npc_num = 0
            other_num = 0
            for id,obj in g_EntityObjectDict.items():
                if obj.is_player():
                    player_num += 1
                elif obj.is_monster():
                    monster_num += 1
                elif obj.is_npc():
                    npc_num += 1
                else:
                    other_num += 1
            text = text + u"玩家:%d\n怪物:%d\nNPC:%d\n其他:%d\n"%(player_num,monster_num,npc_num,other_num)
            self.m_OutTextEdit.setPlainText(text)

    def onClickChooseRole(self):
        if self.m_ChooseRoleStatus == 0:
            self.m_ChooseRoleStatus = 1
            self.m_ChooseRoleButton.setText(u'请在屏幕上双击主角')
        elif self.m_ChooseRoleStatus == 2:
            self.onClearRole()

    def onChooseRoleOK(self, role_id):
        if self.m_ChooseRoleStatus == 1:
            self.m_ChooseRoleStatus = 2
            self.m_RoleID = role_id
            self.m_ChooseRoleButton.setText(u'取消主角')

    def onClearRole(self):
        self.m_ChooseRoleStatus = 0
        self.m_RoleID = None
        self.m_ChooseRoleButton.setText(u'选取主角')

    def getRole(self):
        if self.m_RoleID:
            return GetObject(self.m_RoleID)
        return None

    def onTransRole(self):
        oRole = self.getRole()
        if oRole and g_Socketfd:
            if g_DoubleClickPosList:
                real_pos = pos_screen2real(g_DoubleClickPosList[0])
                x,z = real_pos
                x = x_real2server(x)
                z = z_real2server(z)
                g_Socketfd.send("teleport %d %d %d"%(self.m_RoleID,x,z))

    def writeDebugText(self,txt,mod="w"):
        txt = txt + "\n"
        if mod == "a+":
            txt = self.m_DebugTextEdit.toPlainText() + txt
        self.m_DebugTextEdit.setPlainText(txt)

def handle_Qt():
    print "QT4 init!\n"
    global g_DebugWin
    app = QtGui.QApplication(sys.argv)
    g_DebugWin = CDebugWin()
    g_DebugWin.show()
    g_QTSignalMgr.m_SglEditText.connect(g_DebugWin.writeDebugText)
    sys.exit(app.exec_())

def run_Qt():
    start_new_thread(handle_Qt,())

#============tool method==========
def syslog_file(txt, mod="a+"):
    f = open(SYS_LOGFILE, mod)
    txt = "[" + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "] " + txt + "\n"
    f.write(txt)
    f.close()

def log_file(filename, txt, mod="a+"):
    f = open(filename, mod)
    txt = "[" + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "] " + txt + "\n"
    f.write(txt)
    f.close()

#============main method==========
def init_globals():
    global g_ChineseFont
    g_ChineseFont = pygame.font.Font("SIMSUN.TTC", 10)
    global g_MouseClickListener
    g_MouseClickListener = CMouseClickListener()
    global g_QTSignalMgr
    g_QTSignalMgr = CQTSignalMgr()

def run_test():
    global MAX_REAL_X,MAX_REAL_Z,MAX_AOI_ROW,MAX_AOI_COL,g_PlayCtrl
    MAX_REAL_X = 108*SCREEN_WIDTH
    MAX_REAL_Z = 173*SCREEN_HEIGHT
    MAX_AOI_ROW = 32
    MAX_AOI_COL = 32
    blkfile = "TestMap.bytes"
    load_map(blkfile)
    init_draw_realpos()
    g_PlayCtrl = True
    pygame.display.set_caption("Scene: "+blkfile)

def process_exit():
    global g_ProcessExit
    g_ProcessExit = True
    if not g_PlayCtrl:
        exit()

def main_loop():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT), 0, 32)
    clock = pygame.time.Clock()
    init_globals()
    run_Qt()
    if len(sys.argv) > 1:
        run_socket_thread()
    else:
        run_test()

    while True:
        if g_ProcessExit:
            break
        for event in pygame.event.get():
            if event.type == QUIT:
                process_exit()
            elif event.type == MOUSEBUTTONDOWN:
                g_MouseClickListener.add_pygame_event(event.button, event.pos)
            elif event.type == KEYDOWN:
                if event.key:
                    g_QTSignalMgr.m_SglEditText.emit(QtCore.QString(chr(event.key)), "a+")

        if not g_PlayCtrl:
            continue
        g_MouseClickListener.update(time.time())
        #draw background
        t1 = time.time()
        screen.fill(COLOR_WHITE)
        #draw map block
        for tz,xlst in g_MapBlockDict.items():
            for tx in xlst:
                game_draw_rect(screen, COLOR_CHOCOLATE, (tx[0],tz[0]), (tx[1],tz[1]))
        t2 = time.time()
        #draw aoi line
        for i in xrange(MAX_AOI_ROW):
            z = MAX_REAL_X*i/MAX_AOI_ROW
            game_draw_line(screen, COLOR_BLACK, (0,z), (MAX_REAL_X,z))
        for j in xrange(MAX_AOI_COL):
            x = MAX_REAL_Z*j/MAX_AOI_COL
            game_draw_line(screen, COLOR_BLACK, (x,0), (x,MAX_REAL_Z))
        #draw mouse click aoi rect
        for i,pos in enumerate(g_SingleClickPosList):
            if i == 0:
                lt_pos,rb_pos = get_scnpos_aoirect(pos)
                game_draw_rect(screen, COLOR_BLUE, lt_pos, rb_pos, 3)
            elif i == 1:
                lt_pos,rb_pos = get_scnpos_aoirect(pos)
                game_draw_rect(screen, COLOR_RED, lt_pos, rb_pos, 3)
        if g_DoubleClickPosList:
            lt_pos,rb_pos = get_scnpos_aoirect(g_DoubleClickPosList[0])
            game_draw_rect(screen, COLOR_YELLOW, lt_pos, rb_pos, 3)
        #draw entity objects
        for id,obj in g_EntityObjectDict.items():
            obj.draw(screen)
        t3 = time.time()
        pygame.display.update()
        t4 = time.time()
        # print "---draw cost time block:%f other:%f | update cost time:%f | total cost:%f | total entitys:%d--"%(t2-t1,t3-t2,t4-t3,t4-t1,len(g_EntityObjectDict))
        #每秒5帧
        clock.tick(30)

main_loop()