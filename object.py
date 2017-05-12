import pygame
from pygame.locals import *

class CObject:
	def __init__(id, x, z, stype, radius=None):
		self.m_ID = id
		self.m_X = x
		self.m_Z = z
		self.m_Type = stype
		self.m_Radius = radius or 1

	def setpos(x,z):
		self.m_X = x
		self.m_Z = z

	def draw(surface):
		pygame.draw.circle(surface, COLOR_YELLOW, (self.m_X,self.m_Z), self.m_Radius)