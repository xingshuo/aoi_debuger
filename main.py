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

SCREEN_WIDTH = 1200
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
#============global values============
g_DrawStartRealPos = None
g_DrawEndRealPos = None
g_DrawRealXLen = None
g_DrawRealZLen = None
g_MapInit = False
g_MapBlockDict = {}
g_NetStreamBuffer = ""
g_EntityObjectDict = {}
g_EntityColors = {"player":COLOR_RED, "monster":COLOR_GREEN, "npc":COLOR_CHOCOLATE}
g_ChineseFont = None
g_MouseClickListener = None
g_SingleClickPosList = []
g_DoubleClickPosList = []
g_Socketfd = None
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

def get_scnpos_aoirect(pos):
    pos = pos_screen2real(pos)
    sx = (pos[0]*MAX_AOI_COL/MAX_REAL_X)*(MAX_REAL_X/MAX_AOI_COL)
    ex = sx + MAX_REAL_X/MAX_AOI_COL
    sz = (pos[1]*MAX_AOI_ROW/MAX_REAL_Z)*(MAX_REAL_Z/MAX_AOI_ROW)
    ez = sz + MAX_REAL_Z/MAX_AOI_ROW
    return (sx,sz),(ex,ez)

def is_fullscreen_mode():
    return g_DrawStartRealPos==(0,0) and g_DrawEndRealPos==(MAX_REAL_X,MAX_REAL_Z)

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

def is_on_lefttop(posA, posB):
    if posA[0] < posB[0] and posA[1] < posB[1]:
        return True
    return False

def is_on_rightbelow(posA, posB):
    if posA[0] > posB[0] and posA[1] > posB[1]:
        return True
    return False

def trans_real_x(x):
    return int(x)

def trans_real_z(z):
    return MAX_REAL_Z - int(z)

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

def game_draw_circle(surface, color, center_pos, radius):
    center_pos = pos_real2screen(center_pos)
    pygame.draw.circle(surface, color, center_pos, radius)

#=========game class and methods========
class CObject:
    def __init__(self, id, x, z, stype, radius, name):
        self.m_ID = id
        self.m_X = x
        self.m_Z = z
        self.m_DirX = 0
        self.m_DirZ = 0
        self.m_Type = stype
        self.m_Radius = radius or 2
        self.m_Name = name or ""

    def name(self):
        return self.m_Name

    def radius(self):
        return self.m_Radius*MAX_REAL_X/g_DrawRealXLen

    def dir(self):
        return (self.m_DirX,self.m_DirZ)

    def setpos(self, x, z):
        self.m_DirX = (x-self.m_X)*5
        self.m_DirZ = (z-self.m_Z)*5
        self.m_X = x
        self.m_Z = z

    def draw(self, surface):
        color = g_EntityColors.get(self.m_Type, COLOR_GREEN)
        text = g_ChineseFont.render(u'%s'%self.name(), True, color)
        scn_pos = pos_real2screen((self.m_X-20,self.m_Z-20))
        surface.blit(text, scn_pos)
        radius = self.radius()
        game_draw_circle(surface, color, (self.m_X,self.m_Z), radius)
        dir_len = math.sqrt(self.m_DirX*self.m_DirX + self.m_DirZ*self.m_DirZ)
        dir_x = self.m_X
        dir_z = self.m_Z
        if dir_len > 0:
            K = 40*radius
            dir_x = self.m_X + self.m_DirX*K/dir_len
            dir_z = self.m_Z + self.m_DirZ*K/dir_len
        game_draw_line(surface, color, (self.m_X, self.m_Z), (dir_x, dir_z), MAX_REAL_X/g_DrawRealXLen)


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
            if is_fullscreen_mode():
                g_DoubleClickPosList.append(pos)
                if len(g_DoubleClickPosList) > 1:
                    g_DoubleClickPosList.pop(0)

#============socket methods============
def handle_socket():
    while True:
        data = g_Socketfd.recv(BIN_RECV_LEN)
        # print "recv data",data,"ok"
        if not data:
            print "socket disconnect!"
            break
        global g_NetStreamBuffer,MAX_AOI_ROW,MAX_AOI_COL,MAX_REAL_X,MAX_REAL_Z,g_MapInit
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
                x = trans_real_x(x)
                z = trans_real_z(z)
                obj = GetObject(id)
                if obj:
                    obj.setpos(x, z)
            elif lst[0] == "initmap":
                max_x,max_z,view_x,view_z,blkfile = lst[1:]
                MAX_REAL_X = int(max_x)
                MAX_REAL_Z = int(max_z)
                MAX_AOI_ROW = MAX_REAL_Z/int(view_z)
                MAX_AOI_COL = MAX_REAL_X/int(view_x)
                os.system("ln -s -f ~/BnHServer/build/block_map/ ./")
                path = "block_map/" + blkfile + ".bytes"
                load_map(path)
                init_draw_realpos()
                g_MapInit = True
                pygame.display.set_caption("Scene: "+blkfile)
            elif lst[0] == "addobj":
                stype,name,uuid,x,z = lst[1:]
                uuid = int(uuid)
                x = trans_real_x(x)
                z = trans_real_z(z)
                CreateObject(uuid, x, z, stype, name = name)
            elif lst[0] == "delobj":
                uuid = int(lst[1])
                DelObject(uuid)

        g_NetStreamBuffer = g_NetStreamBuffer[cur_idx:]
    print "socket disconnect!!!!!"

def run_socket_thread():
    global g_Socketfd
    fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    fd.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    fd.bind(("0.0.0.0", 9203))
    fd.listen(1)
    print "Wait Server Connect..."
    g_Socketfd,addr = fd.accept()
    print 'Connected Succeed with ' + addr[0] + ':' + str(addr[1])
    start_new_thread(handle_socket,())

#============PyQt5================
class Example(QtGui.QWidget):

    def __init__(self):
        super(Example, self).__init__()

        self.initUI()

    def initUI(self):
        hbox = QtGui.QHBoxLayout() #水平的
        vbox1 = QtGui.QVBoxLayout() #竖直的
        vbox2 = QtGui.QVBoxLayout() #竖直的

        LabelA = QtGui.QLabel(u'选择主角:', self)
        ComboBoxA = QtGui.QComboBox(self)
        ComboBoxA.addItem("Ubuntu")
        ComboBoxA.addItem("Mandriva")
        ComboBoxA.addItem("Fedora")
        ComboBoxA.addItem("Red Hat")
        ComboBoxA.addItem("Gentoo")
        ComboBoxA.addItem("None")
        self.connect(ComboBoxA, QtCore.SIGNAL('activated(QString)'), self.onActivated)
        self.PushButtonA = QtGui.QPushButton(u'传送',self)
        self.PushButtonA.clicked.connect(self.onPushButtonA)
        PushButtonB = QtGui.QPushButton(u'主角信息',self)
        vbox1.addWidget(LabelA)
        vbox1.addWidget(ComboBoxA)
        vbox1.addStretch(2)
        vbox1.addWidget(self.PushButtonA)
        vbox1.addStretch(1)
        vbox1.addWidget(PushButtonB)
        vbox1.addStretch(1)

        LabelB = QtGui.QLabel(u'输出板', self)
        TextEditA = QtGui.QTextEdit()
        TextEditA.setReadOnly(True)
        TextEditA.setPlainText("hhhhhh\nbbb%sddd"%(u'输出'))
        vbox2.addWidget(LabelB)
        vbox2.addWidget(TextEditA)
        hbox.addLayout(vbox1,1)
        hbox.addLayout(vbox2,2)

        self.setLayout(hbox)
        self.setGeometry(100, 100, 400, 500)
        self.setWindowTitle('QT DebugWin')

    def onActivated(self, text):
        print "onactivated.. ",text

    def onPushButtonA(self):
        self.PushButtonA.setText('Hello World!')

#---for test qt---
print "start qt!!!!!"
app = QtGui.QApplication(sys.argv)
ex = Example()
ex.show()
sys.exit(app.exec_())

def handle_Qt():
    print "start qt!!!!!"
    app = QtGui.QApplication(sys.argv)
    ex = Example()
    ex.show()
    sys.exit(app.exec_())

#============main method==========
def run_test():
    global MAX_REAL_X,MAX_REAL_Z,MAX_AOI_ROW,MAX_AOI_COL,g_MapInit
    MAX_REAL_X = 108*SCREEN_WIDTH
    MAX_REAL_Z = 173*SCREEN_HEIGHT
    MAX_AOI_ROW = 32
    MAX_AOI_COL = 32
    blkfile = "TestMap.bytes"
    load_map(blkfile)
    init_draw_realpos()
    g_MapInit = True
    pygame.display.set_caption("Scene: "+blkfile)
    start_new_thread(handle_Qt,())

def main_loop():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT), 0, 32)
    clock = pygame.time.Clock()
    global g_SingleClickPosList,g_DoubleClickPosList
    global g_ChineseFont
    g_ChineseFont = pygame.font.Font("SIMSUN.TTC", 10)
    global g_MouseClickListener
    g_MouseClickListener = CMouseClickListener()

    if len(sys.argv) > 1:
        run_socket_thread()
    else:
        run_test()

    while True:
        if not g_MapInit:
            continue
        for event in pygame.event.get():
            if event.type == QUIT:
                exit()
            elif event.type == MOUSEBUTTONDOWN:
                g_MouseClickListener.add_pygame_event(event.button, event.pos)
            elif event.type == KEYDOWN:
                if event.key == ord('q'): #transfer
                    if g_Socketfd:
                        print "do send"
                        g_Socketfd.send("do transfer!!!")

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