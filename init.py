# -*- coding: utf-8 -*-
import socket
import time
import pygame
from pygame.locals import *
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from sys import exit

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

pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT), 0, 32)
screen.fill((255, 255, 255))

my_font = pygame.font.SysFont("arial", 16)
chinese_font = pygame.font.Font("SIMSUN.TTC", 20)

DrawColors = {"player":COLOR_RED, "monster":COLOR_GREEN, "npc":COLOR_CHOCOLATE}
ObjectList = {}

class CObject:
    def __init__(self, id, x, z, stype, radius, name):
        self.m_ID = id
        self.m_X = x
        self.m_Z = z
        self.m_Type = stype
        self.m_Radius = radius or 6
        self.m_Name = name or ""

    def setpos(self, x, z):
        print "recv setpos",x,z
        self.m_X = x
        self.m_Z = z

    def draw(self, surface):
        color = DrawColors.get(self.m_Type, COLOR_GREEN)
        text = chinese_font.render(u'%s'%self.m_Name, True, color)
        surface.blit(text, (self.m_X-10,self.m_Z-10))
        pygame.draw.circle(surface, color, (self.m_X,self.m_Z), self.m_Radius)

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

pygame.display.set_caption("Oh Aoi! "+addr)

ReadBuffer = ""
BlkList = {}

while True:
    for event in pygame.event.get():
        if event.type == QUIT:
            exit()
    data = conn.recv(BIN_RECV_LEN)

    print "recv data",data,"ok"
    if not data:
        break
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
            x = int(x)/SCALE_X
            z = int(z)/SCALE_Z
            obj = GetObject(id)
            if obj:
                obj.setpos(x, z)
        elif lst[0] == "init":
            max_x,max_z,view_x,view_z = lst[1:]
            MAX_ROW = int(max_z)/int(view_z)
            MAX_COL = int(max_x)/int(view_x)
            SCALE_X = int(max_x)/int(SCREEN_WIDTH)
            SCALE_Z = int(max_z)/int(SCREEN_HEIGHT)
        elif lst[0] == "setblk":
            row,col = lst[1:]
            row = int(row)
            col = int(col)
            BlkList[row] = col
        elif lst[0] == "addobj":
            stype,name,uuid,x,z = lst[1:]
            uuid = int(uuid)
            x = int(x)/SCALE_X
            z = int(z)/SCALE_Z
            CreateObject(uuid, x, z, stype, name = name)
        elif lst[0] == "delobj":
            uuid = int(lst[1])
            DelObject(uuid)

    ReadBuffer = ReadBuffer[cur_idx:]

    screen.fill(COLOR_WHITE)

    for i in xrange(1,MAX_ROW):
        height = SCREEN_HEIGHT*i/MAX_ROW
        pygame.draw.line(screen, COLOR_BLACK, (0, height), (SCREEN_WIDTH, height))
    for j in xrange(1,MAX_COL):
        width = SCREEN_WIDTH*j/MAX_COL
        pygame.draw.line(screen, COLOR_BLACK, (width, 0), (width, SCREEN_HEIGHT))

    for i in xrange(0,MAX_ROW):
        text = my_font.render(str(i+1), True, COLOR_BLUE)
        screen.blit(text, (0, SCREEN_HEIGHT*i/MAX_ROW))
    for j in xrange(0,MAX_COL):
        text = my_font.render(str(j+1), True, COLOR_BLUE)
        screen.blit(text, (SCREEN_WIDTH*j/MAX_COL, 0))

    for r,c in BlkList.items():
        h1 = SCREEN_HEIGHT*r/MAX_ROW
        w1 = SCREEN_WIDTH*c/MAX_COL
        h2 = h1 + SCREEN_HEIGHT/MAX_ROW
        w2 = w1 + SCREEN_WIDTH/MAX_COL
        pygame.draw.rect(screen, COLOR_CHOCOLATE, (w1,h1,w2,h2))

    for id,obj in ObjectList.items():
        obj.draw(screen)

    pygame.display.update()