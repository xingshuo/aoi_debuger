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
BLK_MAX_ROW = None
BLK_MAX_COL = None

pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT), 0, 32)
screen.fill(COLOR_CHOCOLATE)

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

conn, addr = s.accept()
addr = 'Connected with ' + addr[0] + ':' + str(addr[1])
print addr

PKG_HEAD_LEN = 3
BIN_RECV_LEN = 512
MAP_INIT = False

pygame.display.set_caption("Oh Aoi! "+addr)

ReadBuffer = ""
BlkDict = {}

def trans_x(x):
    return int(x)/SCALE_X

def trans_z(z):
    return SCREEN_HEIGHT - int(z)/SCALE_Z

def load_map(path):
    global BLK_MAX_ROW,BLK_MAX_COL
    f = open(path, "rb")
    BLK_MAX_ROW = int(f.readline())
    BLK_MAX_COL = int(f.readline())
    cx = float(f.readline())
    cz = float(f.readline())
    scale = int(f.readline())
    dct = {}
    debug = {}
    for i in xrange(BLK_MAX_ROW):
        for j in xrange(BLK_MAX_COL):
            ch = ord(f.read(1))
            if ch == 0:
                if not dct.get(i, None):
                    dct[i] = []
                dct[i].append(j)
            if not debug.get(ch):
                debug[ch] = 0
            debug[ch] = debug[ch] + 1
            if not BlkDict.get(i):
                BlkDict[i] = {}
            BlkDict[i][j] = ch
    print "debug",debug

    f.close()
    # for r,c in dct.items():
    #     c.sort()
    #     start = None
    #     end = None
    #     lst = []
    #     for i,v in enumerate(c):
    #         if i == 0:
    #             start = v
    #             end = v
    #             continue
    #         if v-end > 1:
    #             lst.append((start,end))
    #             start = v
    #             end = v
    #         else:
    #             end = v
    #     if start:
    #         lst.append((start,end))
    #     BlkDict[r] = lst
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

start_new_thread(handle_socket, (conn,))

while True:
    for event in pygame.event.get():
        if event.type == QUIT:
            exit()

    screen.fill(COLOR_CHOCOLATE)
    if not MAP_INIT:
        time.sleep(1)
        continue

    print("draw blk start---")
    # for r,clst in BlkDict.items():
    #     for t in clst:
    #         print "r",r,"t",t
    #         h1 = SCREEN_HEIGHT*r/BLK_MAX_ROW
    #         w1 = SCREEN_WIDTH*t[0]/BLK_MAX_COL
    #         h2 = SCREEN_HEIGHT*(r+1)/BLK_MAX_ROW
    #         w2 = SCREEN_WIDTH*(t[1]+1)/BLK_MAX_COL
    #         print "draw",(w1,h1,w2,h2)
    #         pygame.draw.rect(screen, COLOR_WHITE, (w1,h1,w2,h2))
    for r,d in BlkDict.items():
        for c,v in d.items():
            h1 = SCREEN_HEIGHT*r/BLK_MAX_ROW
            w1 = SCREEN_WIDTH*c/BLK_MAX_COL
            h2 = SCREEN_HEIGHT*(r+1)/BLK_MAX_ROW
            w2 = SCREEN_WIDTH*(c+1)/BLK_MAX_COL
            if v == 0:
                pygame.draw.rect(screen, COLOR_WHITE, (w1,h1,w2,h2))
            else:
                pygame.draw.rect(screen, COLOR_CHOCOLATE, (w1,h1,w2,h2))

    print("draw blk end---")

    # for i in xrange(1,MAX_ROW):
    #     height = SCREEN_HEIGHT*i/MAX_ROW
    #     pygame.draw.line(screen, COLOR_BLACK, (0, height), (SCREEN_WIDTH, height))
    # for j in xrange(1,MAX_COL):
    #     width = SCREEN_WIDTH*j/MAX_COL
    #     pygame.draw.line(screen, COLOR_BLACK, (width, 0), (width, SCREEN_HEIGHT))

    # for i in xrange(0,MAX_ROW):
    #     text = my_font.render(str(i+1), True, COLOR_BLUE)
    #     screen.blit(text, (0, SCREEN_HEIGHT*(MAX_ROW-i-1)/MAX_ROW))
    # for j in xrange(0,MAX_COL):
    #     text = my_font.render(str(j+1), True, COLOR_BLUE)
    #     screen.blit(text, (SCREEN_WIDTH*(j)/MAX_COL, SCREEN_HEIGHT*(MAX_ROW-1)/MAX_ROW))

    # for id,obj in ObjectList.items():
    #     obj.draw(screen)

    pygame.display.update()
    # time.sleep(0.1)