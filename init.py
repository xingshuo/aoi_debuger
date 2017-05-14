# -*- coding: utf-8 -*-
import socket
import time
import os
import pygame
from pygame.locals import *
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from sys import exit
from thread import *


os.system("ln -s -f ~/BnHServer/build/block_map/ ./")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
s.bind(("0.0.0.0", 9203))
s.listen(1)

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 750

COLOR_WHITE = (255,255,255)
COLOR_RED = (255,0,0)
COLOR_YELLOW = (255,255,0)
COLOR_BLACK = (0,0,0)
COLOR_GREEN = (0,255,0)
COLOR_BLUE = (0,255,255)
COLOR_CHOCOLATE = (139,69,19)

SCALE_X = None
SCALE_Z = None
MAX_ROW = None
MAX_COL = None

SCALE_X = 108
SCALE_Z = 173
MAX_ROW = 32
MAX_COL = 32

BLK_MAX_ROW = None
BLK_MAX_COL = None

pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT), 0, 32)

my_font = pygame.font.SysFont("arial", 16)
chinese_font = pygame.font.Font("SIMSUN.TTC", 10)

DrawColors = {"player":COLOR_RED, "monster":COLOR_GREEN, "npc":COLOR_CHOCOLATE}
ObjectList = {}

class CObject:
    def __init__(self, id, x, z, stype, radius, name):
        self.m_ID = id
        self.m_X = x
        self.m_Z = z
        self.m_DirX = 0
        self.m_DirZ = 0
        self.m_Type = stype
        self.m_Radius = radius or 6
        self.m_Name = name or ""

    def setpos(self, x, z):
        print "recv setpos",x,z
        self.m_DirX = (x-self.m_X)*10
        self.m_DirZ = (z-self.m_Z)*10
        self.m_X = x
        self.m_Z = z
        print "dir ",self.m_DirX,self.m_DirZ

    def draw(self, surface):
        color = DrawColors.get(self.m_Type, COLOR_GREEN)
        text = chinese_font.render(u'%s'%self.m_Name, True, color)
        surface.blit(text, (self.m_X-20,self.m_Z-20))
        pygame.draw.circle(surface, color, (self.m_X,self.m_Z), self.m_Radius)
        pygame.draw.line(surface, color, (self.m_X, self.m_Z), (self.m_X+self.m_DirX, self.m_Z+self.m_DirZ), 2)

def CreateObject(id, x, z, stype, radius=None, name=None):
    if ObjectList.get(id, None):
        print "create obj %d repeat"%(id)
    else:
        ObjectList[id] = CObject(id, x, z, stype, radius, name)

def GetObject(id):
    return ObjectList.get(id, None)

def DelObject(id):
    if ObjectList.get(id, None):
        del ObjectList[id]

# conn, addr = s.accept()
# addr = 'Connected with ' + addr[0] + ':' + str(addr[1])
# print addr

PKG_HEAD_LEN = 3
BIN_RECV_LEN = 512
MAP_INIT = False

pygame.display.set_caption("Oh Aoi! ")

ReadBuffer = ""
BlkDict = {}

def trans_x(x):
    return int(x)/SCALE_X

def trans_z(z):
    return SCREEN_HEIGHT - int(z)/SCALE_Z

def trans_screen_x(x):
    return int(x)

def trans_screen_z(z):
    return int(z)

def load_map(path):
    global BLK_MAX_ROW,BLK_MAX_COL
    f = open(path, "rb")
    BLK_MAX_ROW = int(f.readline())
    BLK_MAX_COL = int(f.readline())
    cx = float(f.readline())
    cz = float(f.readline())
    scale = int(f.readline())
    dct = {}
    for i in xrange(BLK_MAX_ROW):
        for j in xrange(BLK_MAX_COL):
            ch = ord(f.read(1))
            if ch != 0:
                if not dct.get(i, None):
                    dct[i] = []
                dct[i].append(j)

    f.close()
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
        BlkDict[r] = lst

    print "----load map end-----",BLK_MAX_ROW,BLK_MAX_COL

def handle_socket(conn):
    while True:
        data = conn.recv(BIN_RECV_LEN)
        print "recv data",data,"ok"
        if not data:
            print "socket disconnect!"
            break
        global ReadBuffer,SCALE_X,SCALE_Z,MAX_ROW,MAX_COL,MAP_INIT
        ReadBuffer = ReadBuffer + data
        cur_idx = 0
        total_len = len(ReadBuffer)
        while cur_idx < total_len:
            if cur_idx+PKG_HEAD_LEN > total_len:
                break
            pkg_len = int(ReadBuffer[cur_idx: cur_idx+PKG_HEAD_LEN])
            if cur_idx+PKG_HEAD_LEN+pkg_len > total_len:
                break
            pkg_str = ReadBuffer[cur_idx+PKG_HEAD_LEN: cur_idx+PKG_HEAD_LEN+pkg_len]
            lst = str.split(pkg_str, " ")
            cur_idx = cur_idx + PKG_HEAD_LEN + pkg_len
            if lst[0] == "setpos":
                uuid,x,z = lst[1:]
                id = int(uuid)
                x = trans_x(x)
                z = trans_z(z)
                obj = GetObject(id)
                if obj:
                    obj.setpos(x, z)
            elif lst[0] == "initmap":
                max_x,max_z,view_x,view_z,blkfile = lst[1:]
                MAX_ROW = int(max_z)/int(view_z)
                MAX_COL = int(max_x)/int(view_x)
                SCALE_X = int(max_x)/int(SCREEN_WIDTH)
                SCALE_Z = int(max_z)/int(SCREEN_HEIGHT)
                os.system("pwd")
                path = "block_map/" + blkfile + ".bytes"
                load_map(path)
                MAP_INIT = True
            elif lst[0] == "addobj":
                stype,name,uuid,x,z = lst[1:]
                uuid = int(uuid)
                x = trans_x(x)
                z = trans_z(z)
                CreateObject(uuid, x, z, stype, name = name)
            elif lst[0] == "delobj":
                uuid = int(lst[1])
                DelObject(uuid)

        ReadBuffer = ReadBuffer[cur_idx:]
    print "handle socket end!!!!!"

# start_new_thread(handle_socket, (conn,))

load_map("block_map/jingzhou.bytes")

g_Clock = pygame.time.Clock()

g_MouseClickList = []

g_lt_row = 0
g_lt_col = 0
g_rb_row = MAX_ROW - 1
g_rb_col = MAX_COL - 1

while True:
    global g_lt_row,g_lt_col,g_rb_row,g_rb_col
    for event in pygame.event.get():
        if event.type == QUIT:
            exit()
        elif event.type == MOUSEBUTTONDOWN:
            if event.button == 1: #left
                if (g_lt_row==0 and g_lt_col==0 and g_rb_row==MAX_ROW-1 and g_rb_col==MAX_COL-1):
                    g_MouseClickList.append(event.pos)
                    if len(g_MouseClickList) > 2:
                        g_MouseClickList.pop(0)
            elif event.button == 2:
                g_MouseClickList = []
                g_lt_row = 0
                g_lt_col = 0
                g_rb_row = MAX_ROW - 1
                g_rb_col = MAX_COL - 1
            elif event.button == 3: #right
                if len(g_MouseClickList) == 2:
                    sta_pos,end_pos = g_MouseClickList
                    g_MouseClickList = []                    
                    if sta_pos[0]<end_pos[0] and sta_pos[1]<end_pos[1]:
                        g_lt_col = trans_screen_x(sta_pos[0])*MAX_COL/SCREEN_WIDTH
                        g_lt_row = trans_screen_z(sta_pos[1])*MAX_ROW/SCREEN_HEIGHT
                        g_rb_col = trans_screen_x(end_pos[0])*MAX_COL/SCREEN_WIDTH
                        g_rb_row = trans_screen_z(end_pos[1])*MAX_ROW/SCREEN_HEIGHT
    screen.fill(COLOR_WHITE)
    # print("draw blk start---")
    # print "rc is: ",g_lt_col,g_lt_row,g_rb_col,g_rb_row
    min_r = g_lt_row*BLK_MAX_ROW/MAX_ROW
    max_r = g_rb_row*BLK_MAX_ROW/MAX_ROW
    min_c = g_lt_col*BLK_MAX_COL/MAX_COL
    max_c = g_rb_col*BLK_MAX_COL/MAX_COL
    # print "range r ",min_r,max_r,"range c ",min_c,max_c
    dr = max_r - min_r + 1
    dc = max_c - min_c + 1
    # print "dr ",dr,"dc ",dc
    #debug line
    # pygame.draw.line(screen, COLOR_BLUE, (min_c*SCREEN_WIDTH/BLK_MAX_COL, min_r*SCREEN_HEIGHT/BLK_MAX_ROW), (max_c*SCREEN_WIDTH/BLK_MAX_COL, max_r*SCREEN_HEIGHT/BLK_MAX_ROW))
    for r,clst in BlkDict.items():
        if r < min_r or r > max_r:
            continue
        h1 = (r-min_r)*SCREEN_HEIGHT/dr
        h2 = (r-min_r+1)*SCREEN_HEIGHT/dr
        for t in clst:
            if t[1] < min_c:
                continue
            if t[0] > max_c:
                break
            s = max(t[0],min_c)
            e = min(t[1],max_c)
            w1 = (s-min_c)*SCREEN_WIDTH/dc
            w2 = (e-min_c)*SCREEN_WIDTH/dc
            pygame.draw.rect(screen, COLOR_CHOCOLATE, (w1,h1,w2-w1,h2-h1+1))

    # print("draw blk end---")

    for i in xrange(1,MAX_ROW):
        if i < g_lt_row:
            continue
        if i > g_rb_row:
            break
        height = SCREEN_HEIGHT*(i-g_lt_row)/(g_rb_row-g_lt_row+1)
        pygame.draw.line(screen, COLOR_BLACK, (0, height), (SCREEN_WIDTH, height))
        text = my_font.render(str(i+1), True, COLOR_BLUE)
        screen.blit(text, (0, height))
    for j in xrange(1,MAX_COL):
        if j < g_lt_col:
            continue
        if j > g_rb_col:
            continue
        width = SCREEN_WIDTH*(j-g_lt_col)/(g_rb_col-g_lt_col+1)
        pygame.draw.line(screen, COLOR_BLACK, (width, 0), (width, SCREEN_HEIGHT))
        text = my_font.render(str(j+1), True, COLOR_BLUE)
        screen.blit(text, (width, SCREEN_HEIGHT*(g_rb_col-g_lt_col)/(g_rb_col-g_lt_col+1)))

    # for i in xrange(0,MAX_ROW):
    #     text = my_font.render(str(i+1), True, COLOR_BLUE)
    #     screen.blit(text, (0, SCREEN_HEIGHT*(MAX_ROW-i-1)/MAX_ROW))
    # for j in xrange(0,MAX_COL):
    #     text = my_font.render(str(j+1), True, COLOR_BLUE)
    #     screen.blit(text, (SCREEN_WIDTH*(j)/MAX_COL, SCREEN_HEIGHT*(MAX_ROW-1)/MAX_ROW))

    if g_MouseClickList:
        sta_pos = g_MouseClickList[0]
        ltc = trans_screen_x(sta_pos[0])*MAX_COL/SCREEN_WIDTH
        ltr = trans_screen_z(sta_pos[1])*MAX_ROW/SCREEN_HEIGHT
        pygame.draw.rect(screen, COLOR_BLUE, (ltc*SCREEN_WIDTH/MAX_COL,ltr*SCREEN_HEIGHT/MAX_ROW,SCREEN_WIDTH/MAX_COL,SCREEN_HEIGHT/MAX_ROW), 3)
        if len(g_MouseClickList) > 1:
            end_pos = g_MouseClickList[1]
            rbc = trans_screen_x(end_pos[0])*MAX_COL/SCREEN_WIDTH
            rbr = trans_screen_z(end_pos[1])*MAX_ROW/SCREEN_HEIGHT
            pygame.draw.rect(screen, COLOR_RED, (rbc*SCREEN_WIDTH/MAX_COL,rbr*SCREEN_HEIGHT/MAX_ROW,SCREEN_WIDTH/MAX_COL,SCREEN_HEIGHT/MAX_ROW), 3)

    for id,obj in ObjectList.items():
        obj.draw(screen)

    pygame.display.update()
    g_Clock.tick(10)