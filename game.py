import sys, os
import pygame
import datetime
import math
import numpy as np
import operator

# PyGame Constants
from pygame.locals import *
from pygame.color import THECOLORS

# PyGame gui
from pgu import gui

# Import the vector class from a local module (in this same directory)
from vec2d_jdm import Vec2D

# Networking

import socket


# =====================================================================
# Classes
# =====================================================================
class ReturnValue(object):
  __slots__ = ["m", "p", "Gama"]
  def __init__(self, m, p, Gama):
     self.m= m
     self.p = p
     self.Gama = Gama

class Client:
    def __init__(self, cursor_color):
        self.cursor_location_px = (0, 0)  # x_px, y_px
        self.mouse_button = 1  # 1, 2, or 3
        self.buttonIsStillDown = False

        self.selected_puck = None
        self.cursor_color = cursor_color
        self.Qcount = 0

        # Define the nature of the cursor strings, one for each mouse button.
        self.mouse_strings = {'string1': {'c_drag': 2.0, 'k_Npm': 60.0},
                              'string2': {'c_drag': 0.2, 'k_Npm': 2.0},
                              'string3': {'c_drag': 20.0, 'k_Npm': 1000.0}}
        # 'string0':{'c_drag':   0.0, 'k_Npm':    0.0}}

    def calc_string_forces_on_pucks(self):
        # Calculated the string forces on the selected puck and add to the aggregate
        # that is stored in the puck object.

        # Only check for a selected puck if one isn't already selected. This keeps
        # the puck from unselecting if cursor is dragged off the puck!
        if (self.selected_puck == None):
            if self.buttonIsStillDown:
                self.selected_puck = air_table.checkForPuckAtThisPosition(self.cursor_location_px)

        else:
            if not self.buttonIsStillDown:
                # Unselect the puck and bomb out of here.
                self.selected_puck.selected = False
                self.selected_puck = None
                return None

            # Use dx difference to calculate the hooks law force being applied by the tether line. 
            # If you release the mouse button after a drag it will fling the puck.
            # This tether force will diminish as the puck gets closer to the mouse point.
            dx_2d_m = env.ConvertScreenToWorld(Vec2D(self.cursor_location_px)) - self.selected_puck.pos_2d_m
            if self.mouse_button == 1:
                #print " button ", self.mouse_button
                stringName = "string" + str(self.mouse_button)
                #print stringName
                self.selected_puck.cursorString_spring_force_2d_N += dx_2d_m * self.mouse_strings[stringName]['k_Npm']
                self.selected_puck.cursorString_puckDrag_force_2d_N += (self.selected_puck.vel_2d_mps *
                                                                        -1 * self.mouse_strings[stringName]['c_drag'])
                #print "puckDrag", self.mouse_strings[stringName]['c_drag']
            elif self.mouse_button == 3:
                #print " button ", self.mouse_button

                # print np.linalg.norm(dx_2d_m[:])
                self.selected_puck.AtractionBeacon_force_2d_N += dx_2d_m

                # # Limit the amount of force the cursor string can apply.
                # mouse_string_tension_limit_N = 1000
                # mouse_string_tension_magnitude = cursor_string.tension_2d_N.length()
                # if mouse_string_tension_magnitude > mouse_string_tension_limit_N:
                # cursor_string.tension_2d_N = (cursor_string.tension_2d_N / mouse_string_tension_magnitude) * mouse_string_tension_limit_N

    def draw_cursor_string(self):
        line_points = [env.ConvertWorldToScreen(self.selected_puck.pos_2d_m), self.cursor_location_px]
        if (self.selected_puck != None):
            pygame.draw.line(game_window.surface, self.cursor_color, line_points[0], line_points[1], 1)

    def draw_fancy_server_cursor(self):
        self.draw_server_cursor(self.cursor_color, 0)
        self.draw_server_cursor(THECOLORS["black"], 1)

    def draw_server_cursor(self, color, edge_px):
        cursor_outline_vertices = []
        cursor_outline_vertices.append(self.cursor_location_px)
        cursor_outline_vertices.append((self.cursor_location_px[0] + 10, self.cursor_location_px[1] + 10))
        cursor_outline_vertices.append((self.cursor_location_px[0] + 0, self.cursor_location_px[1] + 15))

        pygame.draw.polygon(game_window.surface, color, cursor_outline_vertices, edge_px)


class Puck:
    def __init__(self, pos_2d_m, radius_m, density_kgpm2, puck_color=THECOLORS["grey"]):
        self.radius_m = radius_m
        self.radius_px = int(round(env.px_from_m(self.radius_m * env.viewZoom)))

        self.density_kgpm2 = density_kgpm2  # mass per unit area
        self.mass_kg = self.density_kgpm2 * math.pi * self.radius_m ** 2
        self.pos_2d_m = pos_2d_m
        self.vel_2d_mps = Vec2D(0.0, 0.0)

        self.jet_force_2d_N = Vec2D(0.0, 0.0)
        self.cursorString_spring_force_2d_N = Vec2D(0.0, 0.0)
        self.cursorString_puckDrag_force_2d_N = Vec2D(0.0, 0.0)
        self.AtractionBeacon_force_2d_N = Vec2D(0.0, 0.0)
        self.WallsRepulsionForce = Vec2D(0.0, 0.0)

        self.impulse_2d_Ns = Vec2D(0.0, 0.0)

        self.selected = False

        self.color = puck_color

        self.client_name = None
        self.jet = None
        self.gun = None
        # self.hit = False

        # # Bullet data...
        # self.bullet = False
        # self.birth_time_s = env.time_s
        # self.age_limit_s = 3.0

    # If you print an object instance...
    def __str__(self):
        return "puck: x is %s, y is %s" % (self.pos_2d_m.x, self.pos_2d_m.y)

    def draw(self):
        # Convert x,y to pixel screen location and then draw.

        self.pos_2d_px = env.ConvertWorldToScreen(self.pos_2d_m)

        # Update based on zoom factor
        self.radius_px = int(round(env.px_from_m(self.radius_m)))
        if (self.radius_px < 3):
            self.radius_px = 3

            # # Just after a hit, fill the whole circle with RED (i.e., thickness = 0).
            # if self.hit:
            # puck_circle_thickness = 0
            # puck_color = THECOLORS["red"]
            # self.hit = False
            # else:
            # puck_circle_thickness = 3
            # puck_color = self.color

        puck_circle_thickness = 3
        puck_color = self.color

        # Draw main puck body.
        pygame.draw.circle(game_window.surface, puck_color, self.pos_2d_px, self.radius_px, puck_circle_thickness)


        # # Draw life (poor health) indicator circle.
        # if (self.client_name != None) and (not self.bullet):
        # spent_fraction = float(env.clients[self.client_name].bullet_hit_count) / float(env.clients[self.client_name].bullet_hit_limit)
        # life_radius = spent_fraction * self.radius_px
        # if (life_radius > 2.0):
        # life_radius_px = int(round(life_radius))
        # else:
        # life_radius_px = 2


        # pygame.draw.circle(game_window.surface, THECOLORS["red"], self.pos_2d_px, life_radius_px, 1)


class Spring:
    def __init__(self, p1, p2, length_m=3.0, strength_Npm=0.5, spring_color=THECOLORS["yellow"], width_m=0.025):
        self.p1 = p1
        self.p2 = p2
        self.p1p2_separation_2d_m = Vec2D(0, 0)
        self.p1p2_separation_m = 0
        self.p1p2_normalized_2d = Vec2D(0, 0)

        self.length_m = length_m
        self.strength_Npm = strength_Npm
        self.damper_Ns2pm2 = 0.5  # 5.0 #0.05 #0.15
        self.unstretched_width_m = width_m  # 0.05

        self.spring_vertices_2d_m = []
        self.spring_vertices_2d_px = []

        self.spring_color = spring_color
        self.draw_as_line = False

    def width_to_draw_m(self):
        width_m = self.unstretched_width_m * (1 + 0.30 * (self.length_m - self.p1p2_separation_m))
        if width_m < (0.05 * self.unstretched_width_m):
            self.draw_as_line = True
            width_m = 0.0
        else:
            self.draw_as_line = False
        return width_m

class MazeWalls:
    def __init__(self):
        Rect1 = pygame.Rect(450, 0, 15, 220)
        Rect2 = pygame.Rect(300, 0, 15, 220)
        Rect3 = pygame.Rect(600, 100, 15, 210)
        Rect4 = pygame.Rect(0, 330, 270, 15)
        Rect5 = pygame.Rect(500, 300, 300, 15)
    def draw(self):
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect1)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect2)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect3)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect4)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect5)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect6)


class AirTable:
    def __init__(self, walls_dic):
        self.gON_mps2 = Vec2D(-0.0, -9.0)
        self.gOFF_mps2 = Vec2D(-0.0, -0.0)
        self.g_2d_mps2 = self.gOFF_mps2
        self.g_ON = False

        self.pucks = []
        self.controlled_pucks = []
        self.walls = walls_dic
        self.collision_count = 0
        self.coef_rest_puck = 0.90
        self.coef_rest_table = 0.90

        self.color_transfer = False




    def draw(self):
        # {"L_m":0.0, "R_m":10.0, "B_m":0.0, "T_m":10.0}
        topLeft_2d_px = env.ConvertWorldToScreen(Vec2D(self.walls['L_m'], self.walls['T_m']))
        topRight_2d_px = env.ConvertWorldToScreen(Vec2D(self.walls['R_m'] - 0.01, self.walls['T_m']))
        botLeft_2d_px = env.ConvertWorldToScreen(Vec2D(self.walls['L_m'], self.walls['B_m'] + 0.01))
        botRight_2d_px = env.ConvertWorldToScreen(Vec2D(self.walls['R_m'] - 0.01, self.walls['B_m'] + 0.01))

        Rect1 = pygame.Rect(450, 0, 15, 220)
        Rect2 = pygame.Rect(300, 0, 15, 220)
        Rect3 = pygame.Rect(600, 100, 15, 210)
        Rect4 = pygame.Rect(0, 330, 270, 15)
        Rect5 = pygame.Rect(500, 300, 300, 15)
        Rect6 = pygame.Rect(160, 120, 150, 15)

        fnt = pygame.font.SysFont("Serif", 20)
        pygame.draw.rect(game_window.surface, THECOLORS["darkblue"], Rect(700, 600, 70, 70))
        txt_surface = fnt.render("Destino", True, THECOLORS["black"])
        game_window.surface.blit(txt_surface, [703, 620])

        def isInRange(rectangle, circle):
            return (
                (rectangle.topleft.x - circle.centerx) ** 2 + (rectangle.topleft.y - circle.centery) ** 2 <= (
                    mindist + r_circle) ** 2 or  # circle in upper  left  quadrant of rectangle
                (rectangle.bottomleft.x - circle.centerx) ** 2 + (rectangle.bottomleft.y - circle.centery) ** 2 <= (
                    mindist + r_circle) ** 2 or  # circle in bottom left  quadrant of rectangle
                (rectangle.bottomright.x - circle.centerx) ** 2 + (rectangle.bottomright.y - circle.centery) ** 2 <= (
                    mindist + r_circle) ** 2 or  # circle in bottom right quadrant of rectangle
                (rectangle.topright.x - circle.centerx) ** 2 + (rectangle.topright.y - circle.centery) ** 2 <= (
                    mindist + r_circle) ** 2  # circle in top    right quadrant of rectangle
            )

        # Drawing the obstacle walls
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], topLeft_2d_px, topRight_2d_px, 1)
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], topRight_2d_px, botRight_2d_px, 1)
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], botRight_2d_px, botLeft_2d_px, 1)
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], botLeft_2d_px, topLeft_2d_px, 1)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect1)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect2)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect3)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect4)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect5)
        pygame.draw.rect(game_window.surface, THECOLORS["orangered1"], Rect6)

    def checkForPuckAtThisPosition(self, x_px_or_tuple, y_px=None):
        if y_px == None:
            self.x_px = x_px_or_tuple[0]
            self.y_px = x_px_or_tuple[1]
        else:
            self.x_px = x_px_or_tuple
            self.y_px = y_px

        test_position_m = env.ConvertScreenToWorld(Vec2D(self.x_px, self.y_px))
        for puck in self.pucks:
            vector_difference_m = test_position_m - puck.pos_2d_m
            # Use squared lengths for speed (avoid square root)
            mag_of_difference_m2 = vector_difference_m.length_squared()
            if mag_of_difference_m2 < puck.radius_m ** 2:
                puck.selected = True
                return puck
        return None

    def update_PuckSpeedAndPosition(self, puck, dt_s):
        # Net resulting force on the puck.
        puck_forces_2d_N = (self.g_2d_mps2 * puck.mass_kg) + (puck.jet_force_2d_N +
                                                              puck.cursorString_spring_force_2d_N +
                                                              puck.cursorString_puckDrag_force_2d_N +
                                                              puck.impulse_2d_Ns / dt_s +
                                                              puck.AtractionBeacon_force_2d_N+
                                                              puck.WallsRepulsionForce)

        # Acceleration from Newton's law.
        acc_2d_mps2 = puck_forces_2d_N / puck.mass_kg

        # Acceleration changes the velocity:  dv = a * dt
        # Velocity at the end of the timestep.
        puck.vel_2d_mps = puck.vel_2d_mps + (acc_2d_mps2 * dt_s)

        # Calculate the new physical puck position using the average velocity.
        # Velocity changes the position:  dx = v * dt
        puck.pos_2d_m = puck.pos_2d_m + (puck.vel_2d_mps * dt_s)

        # Now reset the aggregate forces.

        puck.cursorString_spring_force_2d_N = Vec2D(0.0, 0.0)
        puck.cursorString_puckDrag_force_2d_N = Vec2D(0.0, 0.0)
        puck.impulse_2d_Ns = Vec2D(0.0, 0.0)
        puck.WallsRepulsionForce = Vec2D(0.0, 0.0)

    def check_for_collisions(self):
        for i, puck in enumerate(self.pucks):


            #check for colision with walls of the maze
            Rect1b = pygame.Rect(400, 0, 115, 270)
            Rect2b = pygame.Rect(250, 0, 115, 270)
            Rect3b = pygame.Rect(550, 50, 115, 310)
            Rect4b = pygame.Rect(0, 280, 320, 115)
            Rect5b = pygame.Rect(450, 250, 400, 115)
            Rect6b = pygame.Rect(110, 70, 250, 115)

            

            Rect1 = pygame.Rect(450, 0, 15, 220)
            Rect2 = pygame.Rect(300, 0, 15, 220)
            Rect3 = pygame.Rect(600, 100, 15, 210)
            Rect4 = pygame.Rect(0, 330, 270, 15)
            Rect5 = pygame.Rect(500, 300, 300, 15)
            Rect6 = pygame.Rect(160, 120, 150, 15)

            #Rectb=pygame.Rect(Rect.x-50,Rect.y-50,Rect.width+100,Rect.height+100)

            test_position_m = env.ConvertWorldToScreen(Vec2D(puck.pos_2d_m.x, puck.pos_2d_m.y))
            ConstanteRepulsao = 60 ######################definir em outro lugar
            v = Vec2D(test_position_m)


            def AchandoForca(m1,m2,l,v):
                print "v="
                print v
                Gama=(m1-v).dot(m1-m2)/(l**2)
                p1=Vec2D.length(v-m1)
                p2 = Vec2D.length(v- m2)
                if Gama <=0:
                    m=m1
                    p=p1
                else:
                    if Gama>=1:
                        m=m2
                        p=p2
                    else:
                        m=m1+(m2-m1)*Gama
                        p=(p1**2-(Gama*l)**2)**0.5
                return ReturnValue(m,p,Gama)

            if Rect1b.collidepoint(test_position_m):
                Aresta1=AchandoForca(Vec2D(Rect1.topleft),Vec2D(Rect1.topright),Rect1.width,v)
                if Aresta1.Gama < 0 :
                    Aresta3 = AchandoForca(Vec2D(Rect1.topleft), Vec2D(Rect1.bottomleft), Rect1.height, v)
                    p=Aresta3.p
                    m=Aresta3.m
                else:
                    if Aresta1.Gama > 1:
                        Aresta4 = AchandoForca(Vec2D(Rect1.topright), Vec2D(Rect1.bottomright), Rect1.height, v)
                        p=Aresta4.p
                        m=Aresta4.m
                    else:
                        Aresta2 = AchandoForca(Vec2D(Rect1.bottomleft), Vec2D(Rect1.bottomright), Rect1.width, v)
                        if Aresta1.p <= Aresta2.p:
                            p = Aresta1.p
                            m = Aresta1.m
                        else:
                            p = Aresta2.p
                            m = Aresta2.m
                puck.WallsRepulsionForce += Vec2D.scale_vector((v-m), (ConstanteRepulsao/ (p * 0.01 * p  * Vec2D.length(v - m))))

            if Rect2b.collidepoint(test_position_m):
                Aresta1=AchandoForca(Vec2D(Rect2.topleft),Vec2D(Rect2.topright),Rect2.width,v)
                if Aresta1.Gama < 0 :
                    Aresta3 = AchandoForca(Vec2D(Rect2.topleft), Vec2D(Rect2.bottomleft), Rect2.height, v)
                    p=Aresta3.p
                    m=Aresta3.m
                else:
                    if Aresta1.Gama > 1:
                        Aresta4 = AchandoForca(Vec2D(Rect2.topright), Vec2D(Rect2.bottomright), Rect2.height, v)
                        p=Aresta4.p
                        m=Aresta4.m
                    else:
                        Aresta2 = AchandoForca(Vec2D(Rect2.bottomleft), Vec2D(Rect2.bottomright), Rect2.width, v)
                        if Aresta1.p <= Aresta2.p:
                            p = Aresta1.p
                            m = Aresta1.m
                        else:
                            p = Aresta2.p
                            m = Aresta2.m
                puck.WallsRepulsionForce += Vec2D.scale_vector((v - m),(ConstanteRepulsao / (p * 0.01 * p * Vec2D.length(v - m))))

            if Rect3b.collidepoint(test_position_m):
                Aresta1=AchandoForca(Vec2D(Rect3.topleft),Vec2D(Rect3.topright),Rect3.width,v)
                if Aresta1.Gama < 0 :
                    Aresta3 = AchandoForca(Vec2D(Rect3.topleft), Vec2D(Rect3.bottomleft), Rect3.height, v)
                    p=Aresta3.p
                    m=Aresta3.m
                else:
                    if Aresta1.Gama > 1:
                        Aresta4 = AchandoForca(Vec2D(Rect3.topright), Vec2D(Rect3.bottomright), Rect3.height, v)
                        p=Aresta4.p
                        m=Aresta4.m
                    else:
                        Aresta2 = AchandoForca(Vec2D(Rect3.bottomleft), Vec2D(Rect3.bottomright), Rect3.width, v)
                        if Aresta1.p <= Aresta2.p:
                            p = Aresta1.p
                            m = Aresta1.m
                        else:
                            p = Aresta2.p
                            m = Aresta2.m
                puck.WallsRepulsionForce += Vec2D.scale_vector((v - m),
                                                           (ConstanteRepulsao / (p * 0.01 * p * Vec2D.length(v - m))))


            if Rect4b.collidepoint(test_position_m):
                Aresta1=AchandoForca(Vec2D(Rect4.topleft),Vec2D(Rect4.topright),Rect4.width,v)
                if Aresta1.Gama < 0 :
                    Aresta3 = AchandoForca(Vec2D(Rect4.topleft), Vec2D(Rect4.bottomleft), Rect4.height, v)
                    p=Aresta3.p
                    m=Aresta3.m
                else:
                    if Aresta1.Gama > 1:
                        Aresta4 = AchandoForca(Vec2D(Rect4.topright), Vec2D(Rect4.bottomright), Rect4.height, v)
                        p=Aresta4.p
                        m=Aresta4.m
                    else:
                        Aresta2 = AchandoForca(Vec2D(Rect4.bottomleft), Vec2D(Rect4.bottomright), Rect4.width, v)
                        if Aresta1.p <= Aresta2.p:
                            p = Aresta1.p
                            m = Aresta1.m
                        else:
                            p = Aresta2.p
                            m = Aresta2.m
                puck.WallsRepulsionForce += Vec2D.scale_vector((v - m),
                                                           (ConstanteRepulsao / (p * 0.01 * p * Vec2D.length(v - m))))
            if Rect5b.collidepoint(test_position_m):
                Aresta1=AchandoForca(Vec2D(Rect5.topleft),Vec2D(Rect5.topright),Rect5.width,v)
                if Aresta1.Gama < 0 :
                    Aresta3 = AchandoForca(Vec2D(Rect5.topleft), Vec2D(Rect5.bottomleft), Rect5.height, v)
                    p=Aresta3.p
                    m=Aresta3.m
                else:
                    if Aresta1.Gama > 1:
                        Aresta4 = AchandoForca(Vec2D(Rect5.topright), Vec2D(Rect5.bottomright), Rect5.height, v)
                        p=Aresta4.p
                        m=Aresta4.m
                    else:
                        Aresta2 = AchandoForca(Vec2D(Rect5.bottomleft), Vec2D(Rect5.bottomright), Rect5.width, v)
                        if Aresta1.p <= Aresta2.p:
                            p = Aresta1.p
                            m = Aresta1.m
                        else:
                            p = Aresta2.p
                            m = Aresta2.m
                puck.WallsRepulsionForce += Vec2D.scale_vector((v - m),
                                                           (ConstanteRepulsao / (p * 0.01 * p * Vec2D.length(v - m))))


            if Rect6b.collidepoint(test_position_m):
                Aresta1=AchandoForca(Vec2D(Rect6.topleft),Vec2D(Rect6.topright),Rect6.width,v)
                if Aresta1.Gama < 0 :
                    Aresta3 = AchandoForca(Vec2D(Rect6.topleft), Vec2D(Rect6.bottomleft), Rect6.height, v)
                    p=Aresta3.p
                    m=Aresta3.m
                else:
                    if Aresta1.Gama > 1:
                        Aresta4 = AchandoForca(Vec2D(Rect6.topright), Vec2D(Rect6.bottomright), Rect6.height, v)
                        p=Aresta4.p
                        m=Aresta4.m
                    else:
                        Aresta2 = AchandoForca(Vec2D(Rect6.bottomleft), Vec2D(Rect6.bottomright), Rect6.width, v)
                        if Aresta1.p <= Aresta2.p:
                            p = Aresta1.p
                            m = Aresta1.m
                        else:
                            p = Aresta2.p
                            m = Aresta2.m
                puck.WallsRepulsionForce += Vec2D.scale_vector((v - m),
                                                           (ConstanteRepulsao / (p * 0.01 * p * Vec2D.length(v - m))))



            if Rect3.collidepoint(test_position_m):
                print "Colisao com paredes"
                puck.vel_2d_mps *= -1 * self.coef_rest_table
            if Rect4.collidepoint(test_position_m):
                print "Colisao com paredes"
                puck.vel_2d_mps *= -1 * self.coef_rest_table
                print "Inversao de Velocidade!V=", puck.vel_2d_mps
            if Rect5.collidepoint(test_position_m):
                print "Colisao com paredes"
                puck.vel_2d_mps *= -1 * self.coef_rest_table
            if Rect6.collidepoint(test_position_m):
                print "Colisao com paredes"
                puck.vel_2d_mps *= -1 * self.coef_rest_table

            if (((puck.pos_2d_m.y - puck.radius_m) < self.walls["B_m"]) or (
                        (puck.pos_2d_m.y + puck.radius_m) > self.walls["T_m"])):

                if self.correct_for_wall_penetration:
                    if (puck.pos_2d_m.y - puck.radius_m) < self.walls["B_m"]:
                        penetration_y_m = self.walls["B_m"] - (puck.pos_2d_m.y - puck.radius_m)
                        puck.pos_2d_m.y += 2 * penetration_y_m

                    if (puck.pos_2d_m.y + puck.radius_m) > self.walls["T_m"]:
                        penetration_y_m = (puck.pos_2d_m.y + puck.radius_m) - self.walls["T_m"]
                        puck.pos_2d_m.y -= 2 * penetration_y_m

                puck.vel_2d_mps.y *= -1 * self.coef_rest_table

            if (((puck.pos_2d_m.x - puck.radius_m) < self.walls["L_m"]) or (
                        (puck.pos_2d_m.x + puck.radius_m) > self.walls["R_m"])):

                if self.correct_for_wall_penetration:
                    if (puck.pos_2d_m.x - puck.radius_m) < self.walls["L_m"]:
                        penetration_x_m = self.walls["L_m"] - (puck.pos_2d_m.x - puck.radius_m)
                        puck.pos_2d_m.x += 2 * penetration_x_m

                    if (puck.pos_2d_m.x + puck.radius_m) > self.walls["R_m"]:
                        penetration_x_m = (puck.pos_2d_m.x + puck.radius_m) - self.walls["R_m"]
                        puck.pos_2d_m.x -= 2 * penetration_x_m

                puck.vel_2d_mps.x *= -1 * self.coef_rest_table

            # Collisions with other pucks. 
            for otherpuck in self.pucks[i + 1:]:

                # Check if the two puck circles are overlapping.

                # Parallel to the normal
                puck_to_puck_2d_m = otherpuck.pos_2d_m - puck.pos_2d_m
                # Parallel to the tangent
                tanget_p_to_p_2d_m = Vec2D.rotate90(puck_to_puck_2d_m)

                p_to_p_m2 = puck_to_puck_2d_m.length_squared()

                # Keep this check fast by avoiding square roots.
                if (p_to_p_m2 < (puck.radius_m + otherpuck.radius_m) ** 2):
                    self.collision_count += 1
                    # print "collision_count", self.collision_count

                    # If it's a bullet coming from another client, add to the
                    # hit count for non-bullet client.
                    if (puck.client_name != None) and (otherpuck.client_name != None):
                        if (puck.client_name != otherpuck.client_name):
                            if (otherpuck.bullet and (not puck.bullet)):
                                if not puck.gun.shield:
                                    env.clients[puck.client_name].bullet_hit_count += 1
                                    puck.hit = True
                                else:
                                    puck.gun.shield_hit_count += 1

                    if self.color_transfer == True:
                        # (puck.color, otherpuck.color) = (otherpuck.color, puck.color)
                        pass

                    # Use the p_to_p vector (between the two colliding pucks) as projection target for 
                    # normal calculation.

                    # The calculate velocity components along and perpendicular to the normal.
                    puck_normal_2d_mps = puck.vel_2d_mps.projection_onto(puck_to_puck_2d_m)
                    puck_tangent_2d_mps = puck.vel_2d_mps.projection_onto(tanget_p_to_p_2d_m)

                    otherpuck_normal_2d_mps = otherpuck.vel_2d_mps.projection_onto(puck_to_puck_2d_m)
                    otherpuck_tangent_2d_mps = otherpuck.vel_2d_mps.projection_onto(tanget_p_to_p_2d_m)

                    relative_normal_vel_2d_mps = otherpuck_normal_2d_mps - puck_normal_2d_mps

                    if self.correct_for_puck_penetration:
                        # Back out a total of 2x of the penetration along the normal. Back-out amounts for each puck is 
                        # based on the velocity of each puck time 2DT where DT is the time of penetration. DT is calculated
                        # from the relative speed and the penetration distance.

                        relative_normal_spd_mps = relative_normal_vel_2d_mps.length()
                        penetration_m = (puck.radius_m + otherpuck.radius_m) - p_to_p_m2 ** 0.5
                        if (relative_normal_spd_mps > 0.00001):
                            penetration_time_s = penetration_m / relative_normal_spd_mps

                            penetration_time_scaler = 1.0  # This can be useful for testing to amplify and see the correction.

                            # First, reverse the two pucks, to their collision point, along their incoming trajectory paths.
                            puck.pos_2d_m = puck.pos_2d_m - (
                                puck_normal_2d_mps * (penetration_time_scaler * penetration_time_s))
                            otherpuck.pos_2d_m = otherpuck.pos_2d_m - (
                                otherpuck_normal_2d_mps * (penetration_time_scaler * penetration_time_s))

                            # Calculate the velocities along the normal AFTER the collision. Use a CR (coefficient of restitution)
                            # of 1 here to better avoid stickiness.
                            CR_puck = 1
                            puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps = self.AandB_normal_AFTER_2d_mps(
                                puck_normal_2d_mps, puck.mass_kg, otherpuck_normal_2d_mps, otherpuck.mass_kg, CR_puck)

                            # Finally, travel another penetration time worth of distance using these AFTER-collision velocities.
                            # This will put the pucks where they should have been at the time of collision detection.
                            puck.pos_2d_m = puck.pos_2d_m + (
                                puck_normal_AFTER_mps * (penetration_time_scaler * penetration_time_s))
                            otherpuck.pos_2d_m = otherpuck.pos_2d_m + (
                                otherpuck_normal_AFTER_mps * (penetration_time_scaler * penetration_time_s))

                        else:
                            pass
                            # print "small relative speed"
                            # self.g_2d_mps2 = self.gOFF_mps2
                            # for puck in self.pucks:
                            # puck.vel_2d_mps = Vec2D(0,0)

                    # Assign the AFTER velocities (using the actual CR here) to the puck for use in the next frame calculation.
                    CR_puck = self.coef_rest_puck
                    puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps = self.AandB_normal_AFTER_2d_mps(
                        puck_normal_2d_mps, puck.mass_kg, otherpuck_normal_2d_mps, otherpuck.mass_kg, CR_puck)

                    # Now that we're done using the current values, set them to the newly calculated AFTERs.
                    puck_normal_2d_mps, otherpuck_normal_2d_mps = puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps

                    # Add the components back together to get total velocity vectors for each puck.
                    puck.vel_2d_mps = puck_normal_2d_mps + puck_tangent_2d_mps
                    otherpuck.vel_2d_mps = otherpuck_normal_2d_mps + otherpuck_tangent_2d_mps

    def normal_AFTER_2d_mps(self, A_normal_BEFORE_2d_mps, A_mass_kg, B_normal_BEFORE_2d_mps, B_mass_kg, CR_puck):
        # For inputs as defined here, this returns the AFTER normal for the first puck in the inputs. So if B
        # is first, it returns the result for the B puck.
        relative_normal_vel_2d_mps = B_normal_BEFORE_2d_mps - A_normal_BEFORE_2d_mps
        return (((relative_normal_vel_2d_mps * (CR_puck * B_mass_kg)) +
                 (A_normal_BEFORE_2d_mps * A_mass_kg + B_normal_BEFORE_2d_mps * B_mass_kg)) /
                (A_mass_kg + B_mass_kg))

    def AandB_normal_AFTER_2d_mps(self, A_normal_BEFORE_2d_mps, A_mass_kg, B_normal_BEFORE_2d_mps, B_mass_kg, CR_puck):
        A = self.normal_AFTER_2d_mps(A_normal_BEFORE_2d_mps, A_mass_kg, B_normal_BEFORE_2d_mps, B_mass_kg, CR_puck)
        # Make use of the symmetry in the physics to calculate the B normal (put the B data in the first inputs).
        B = self.normal_AFTER_2d_mps(B_normal_BEFORE_2d_mps, B_mass_kg, A_normal_BEFORE_2d_mps, A_mass_kg, CR_puck)
        return A, B


class Environment:
    def __init__(self, screenSize_px, length_x_m):
        self.screenSize_px = Vec2D(screenSize_px)
        self.viewOffset_px = Vec2D(0, 0)
        self.viewCenter_px = Vec2D(0, 0)
        self.viewZoom = 1
        self.viewZoom_rate = 0.01

        self.px_to_m = length_x_m / float(self.screenSize_px.x)
        self.m_to_px = (float(self.screenSize_px.x) / length_x_m)

        self.client_colors = {'C1': THECOLORS["orangered1"], 'C2': THECOLORS["tan"], 'C3': THECOLORS["cyan"],
                              'C4': THECOLORS["blue"],
                              'C5': THECOLORS["pink"], 'C6': THECOLORS["red"], 'C7': THECOLORS["coral"],
                              'C8': THECOLORS["green"],
                              'C9': THECOLORS["grey80"], 'C10': THECOLORS["rosybrown3"]}

        # Add a local (non-network) client to the client dictionary.
        self.clients = {'local': Client(THECOLORS["green"])}

        self.time_s = 0

    # Convert from meters to pixels 
    def px_from_m(self, dx_m):
        return dx_m * self.m_to_px * self.viewZoom

    # Convert from pixels to meters
    # Note: still floating values here)
    def m_from_px(self, dx_px):
        return float(dx_px) * self.px_to_m / self.viewZoom

    def ConvertScreenToWorld(self, point_2d_px):
        # self.viewOffset_px = self.viewCenter_px
        x_m = (point_2d_px.x + self.viewOffset_px.x) / (self.m_to_px * self.viewZoom)
        y_m = (self.screenSize_px.y - point_2d_px.y + self.viewOffset_px.y) / (self.m_to_px * self.viewZoom)
        return Vec2D(x_m, y_m)

    def ConvertWorldToScreen(self, point_2d_m):
        """
        Convert from world to screen coordinates (pixels).
        In the class instance, we store a zoom factor, an offset indicating where
        the view extents start at, and the screen size (in pixels).
        """

        # self.viewOffset = self.viewCenter - self.screenSize_px/2
        # self.viewOffset = self.viewCenter_px
        x_px = (point_2d_m.x * self.m_to_px * self.viewZoom) - self.viewOffset_px.x
        y_px = (point_2d_m.y * self.m_to_px * self.viewZoom) - self.viewOffset_px.y
        y_px = self.screenSize_px.y - y_px

        # Return a tuple of integers.
        return Vec2D(x_px, y_px, "int").tuple()

    def get_local_user_input(self):
        local_user = self.clients['local']

        # Get all the events since the last call to get().
        for event in pygame.event.get():
            if (event.type == pygame.QUIT):
                sys.exit()
            elif (event.type == pygame.KEYDOWN):
                if (event.key == K_ESCAPE):
                    sys.exit()
                elif (event.key == K_1):
                    return 1
                elif (event.key == K_2):
                    return 2
                elif (event.key == K_3):
                    return 3
                elif (event.key == K_4):
                    return 4
                elif (event.key == K_5):
                    return 5
                elif (event.key == K_6):
                    return 6
                elif (event.key == K_7):
                    return 7
                elif (event.key == K_8):
                    return 8
                elif (event.key == K_9):
                    return 9
                elif (event.key == K_0):
                    return 0

                elif (event.key == K_c):
                    # Toggle color option.
                    air_table.color_transfer = not air_table.color_transfer
                    # form['ColorTransfer'].value = air_table.color_transfer

                elif (event.key == K_f):
                    # make pucks freeze(take their velocity)
                    for puck in air_table.pucks:
                        puck.vel_2d_mps = Vec2D(0, 0)

                elif (event.key == K_g):
                    if air_table.g_ON:
                        air_table.g_2d_mps2 = air_table.gOFF_mps2
                        air_table.coef_rest_puck = 1.00
                        air_table.coef_rest_table = 1.00
                    else:
                        air_table.g_2d_mps2 = air_table.gON_mps2
                        air_table.coef_rest_puck = 0.90
                        air_table.coef_rest_table = 0.90
                    air_table.g_ON = not air_table.g_ON
                    print "g", air_table.g_ON

                elif (event.key == K_F2):
                    # Toggle menu on/off
                    # air_table.gui_menu = not air_table.gui_menu
                    pass

                elif (event.key == K_SPACE):
                    # Tira e coloca gravidade
                    if air_table.g_ON:
                        air_table.g_2d_mps2 = air_table.gOFF_mps2
                        air_table.coef_rest_puck = 1.00
                        air_table.coef_rest_table = 1.00
                    else:
                        air_table.g_2d_mps2 = air_table.gON_mps2
                        air_table.coef_rest_puck = 0.90
                        air_table.coef_rest_table = 0.90
                    air_table.g_ON = not air_table.g_ON
                    print "Atraction B", air_table.g_ON

                else:
                    return "nothing set up for this key"

            # elif (event.type == pygame.KEYUP):
            elif (event.type == pygame.MOUSEBUTTONDOWN):
                local_user.buttonIsStillDown = True

                (button1, button2, button3) = pygame.mouse.get_pressed()
                if button1:
                    local_user.mouse_button = 1
                elif button2:
                    local_user.mouse_button = 2
                elif button3:
                    local_user.mouse_button = 3
                else:
                    local_user.mouse_button = 0

            elif event.type == pygame.MOUSEBUTTONUP:
                local_user.buttonIsStillDown = False
                local_user.mouse_button = 0

                # In all cases, pass the event to the Gui.
                # app.event(event)

        if local_user.buttonIsStillDown:
            # This will select a puck when the puck runs into the cursor of the mouse with it's button still down.
            local_user.cursor_location_px = (mouseX, mouseY) = pygame.mouse.get_pos()

            # Only check for a selected puck if one isn't already selected. This keeps
            # the puck from unselecting if cursor is dragged off the puck!
            # if not local_user.selected_puck:
            # # Effectively waits for a puck to run over the cursor.
            # local_user.selected_puck = air_table.checkForPuckAtThisPosition(mouseX, mouseY)


class GameWindow:
    def __init__(self, screen_tuple_px, title):
        self.width_px = screen_tuple_px[0]
        self.height_px = screen_tuple_px[1]

        # The initial World position vector of the Upper Right corner of the screen.
        # Yes, that's right y_px = 0 for UR.
        self.UR_2d_m = env.ConvertScreenToWorld(Vec2D(self.width_px, 0))

        # Create a reference to the display surface object. This is a pygame "surface".
        # Screen dimensions in pixels (tuple)
        self.surface = pygame.display.set_mode(screen_tuple_px)

        self.update_caption(title)

        self.surface.fill(THECOLORS["black"])
        pygame.display.update()

    def update_caption(self, title):
        pygame.display.set_caption(title)
        self.caption = title

    def update(self):
        pygame.display.update()

    def clear(self):
        # Useful for shifting between the various demos.
        self.surface.fill(THECOLORS["black"])
        pygame.display.update()


# ===========================================================
# Functions
# ===========================================================

def make_some_pucks(resetmode):
    game_window.update_caption("Object Transportation : Test #" + str(resetmode))

    if resetmode == 3:
        #                                              ,radius,density
        air_table.pucks.append(Puck(Vec2D(2.5, 7.5), 0.25, 0.3, THECOLORS["orange"]))
        air_table.pucks.append(Puck(Vec2D(6.0, 2.5), 0.45, 0.3))  # maybe not.
        air_table.pucks.append(Puck(Vec2D(7.5, 2.5), 0.65, 0.3))
        air_table.pucks.append(Puck(Vec2D(2.5, 5.5), 1.65, 0.3))
        air_table.pucks.append(Puck(Vec2D(7.5, 7.5), 0.95, 0.3))

    elif resetmode == 1:
        # air_table.gON_mps2 = Vec2D(-0.0, -20.0)
        spacing_factor = 0.8
        grid_size = 12, 5  # 9,6
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j, k) == (2, 2)):
                    air_table.pucks.append(
                        Puck(Vec2D(spacing_factor * (j + 1), spacing_factor * (k + 1)), 0.25, 5.0, THECOLORS["orange"]))
                else:
                    air_table.pucks.append(Puck(Vec2D(spacing_factor * (j + 1), spacing_factor * (k + 1)), 0.25, 5.0))
                    # Nudge the first puck a little
                    # air_table.pucks[53].pos_2d_m = air_table.pucks[53].pos_2d_m + Vec2D(0.00001 , 0.0)
                    # air_table.pucks[3].pos_2d_m = air_table.pucks[3].pos_2d_m + Vec2D(0.00001 , 0.0)

    elif resetmode == 4:
        spacing_factor = 1.5
        grid_size = 5, 3
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j, k) == (2, 2)):
                    air_table.pucks.append(
                        Puck(Vec2D(spacing_factor * (j + 1), spacing_factor * (k + 1)), 0.55, 0.3, THECOLORS["orange"]))
                else:
                    air_table.pucks.append(Puck(Vec2D(spacing_factor * (j + 1), spacing_factor * (k + 1)), 0.55, 0.3))

    elif resetmode == 2:
        spacing_factor = 2.0
        grid_size = 4, 2
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j, k) == (1, 1)):
                    air_table.pucks.append(
                        Puck(Vec2D(spacing_factor * (j + 1), spacing_factor * (k + 1)), 0.75, 0.3, THECOLORS["orange"]))
                else:
                    air_table.pucks.append(Puck(Vec2D(spacing_factor * (j + 1), spacing_factor * (k + 1)), 0.75, 0.3))

    elif resetmode == 6:
        air_table.pucks.append(Puck(Vec2D(2.00, 3.00), 0.65, 0.3))
        air_table.pucks.append(Puck(Vec2D(3.50, 4.50), 0.65, 0.3))
        air_table.pucks.append(Puck(Vec2D(5.00, 3.00), 0.65, 0.3))
        air_table.pucks.append(Puck(Vec2D(3.50, 7.00), 0.95, 0.3))



    elif resetmode == 5:
        air_table.pucks.append(Puck(Vec2D(2.00, 3.00), 0.4, 0.3))
        air_table.pucks.append(Puck(Vec2D(3.50, 4.50), 0.4, 0.3))

        # No springs on this one.
        # air_table.pucks.append( Puck(Vec2D(3.50, 7.00),  0.95, 0.3) )

        # elif resetmode == 7:
        # air_table.coef_rest_puck =  0.85
        # air_table.coef_rest_table = 0.85

        # # Make user/client controllable pucks
        # # for all the clients.
        # y_puck_position_m = 1.0
        # for client_name in env.clients:
        # tempPuck = Puck(Vec2D(6.0, y_puck_position_m), 0.45, 0.3)
        # # Let the puck reference the jet and the jet reference the puck.
        # tempPuck.client_name = client_name
        # #tempPuck.jet = Jet( tempPuck)
        # #tempPuck.gun = Gun( tempPuck)

        # air_table.pucks.append( tempPuck)
        # air_table.controlled_pucks.append( tempPuck)
        # y_puck_position_m += 1.2

    else:
        print "Nothing set up for this key."


# ============================================================
# Main procedural script.
# ============================================================

def main():
    # A few globals.
    global env, game_window, air_table

    pygame.init()

    myclock = pygame.time.Clock()

    window_dimensions_px = (800, 700)  # window_width_px, window_height_px

    # Create the first user/client and the methods for moving between the screen and the world.
    env = Environment(window_dimensions_px, 10.0)  # 10m in along the x axis.

    game_window = GameWindow(window_dimensions_px, 'Air Table Server V.2')

    # Define the Left, Right, Bottom, and Top boundaries of the game window.
    air_table = AirTable({"L_m": 0.0, "R_m": game_window.UR_2d_m.x, "B_m": 0.0, "T_m": game_window.UR_2d_m.y})
    air_table.correct_for_wall_penetration = True
    air_table.correct_for_puck_penetration = True

    # Add some pucks to the table.
    make_some_pucks(1)

    # Font object for rendering text onto display surface.
    fnt = pygame.font.SysFont("Arial", 14)

    # Limit the framerate, but let it float below this limit.
    framerate_limit = 500
    dt_render_s = 0.0
    dt_render_limit_s = 1.0 / 120.0  # = 1.0/render_framerate

    qCount_limit = 100

    while True:
        dt_physics_s = float(myclock.tick(framerate_limit) * 1e-3)
        # dt_physics_s = 1/120.0
        # print dt_physics_s, myclock.get_fps()

        # This check avoids problem when dragging the game window.
        if (dt_physics_s < 0.10):

            # Get input from local user.
            resetmode = env.get_local_user_input()

            # Reset the game based on local user control.
            if resetmode in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
                print resetmode
                # This should remove all references to the pucks and effectively kill them off. If there were other
                # variables refering to this list, this would not stop the pucks.

                # Delete all the objects on the table. Cleaning out these list reference to these objects effectively
                # deletes the objects. Notice the contolled list must be cleared also.
                air_table.pucks = []
                air_table.controlled_pucks = []

                # Now just black out the screen.
                game_window.clear()

                # Reinitialize the demo.
                make_some_pucks(resetmode)

            for client_name in env.clients:
                # Calculate client related forces.
                env.clients[client_name].calc_string_forces_on_pucks()

            if (dt_render_s > dt_render_limit_s):

                for controlled_puck in air_table.controlled_pucks:
                    # Rotate based on keyboard of the controlling client.
                    # controlled_puck.jet.rotate( controlled_puck.client_name)
                    # controlled_puck.gun.rotate( controlled_puck.client_name)

                    # Turn shield on/off
                    # controlled_puck.gun.control_shield( controlled_puck.client_name)
                    pass

            # Calculate jet forces on pucks...
            for controlled_puck in air_table.controlled_pucks:
                # controlled_puck.jet.turn_jet_forces_onoff( controlled_puck.client_name)
                pass

            # Apply forces to the pucks and calculate movements.
            for eachpuck in air_table.pucks:
                air_table.update_PuckSpeedAndPosition(eachpuck, dt_physics_s)

            # Check for puck-wall and puck-puck collisions and make penetration corrections.
            air_table.check_for_collisions()

            if (dt_render_s > dt_render_limit_s):

                # Erase the blackboard. Change color if stickiness correction is off.
                if air_table.correct_for_puck_penetration:
                    game_window.surface.fill((0, 0, 0))
                else:
                    grey_level = 40
                    game_window.surface.fill((grey_level, grey_level, grey_level))

                # Small background rectangle for FPS text
                pygame.draw.rect(game_window.surface, THECOLORS["white"], pygame.Rect(10, 10, 35, 20))
                # The text
                fps_string = "%.0f" % myclock.get_fps()
                txt_surface = fnt.render(fps_string, True, THECOLORS["black"])
                game_window.surface.blit(txt_surface, [18, 11])

                # # Clean out old bullets.
                # puck_list_copy = air_table.pucks[:]
                # for thisPuck in puck_list_copy:
                # if (thisPuck.bullet) and ((env.time_s - thisPuck.birth_time_s) > thisPuck.age_limit_s):
                # air_table.pucks.remove(thisPuck)
                # del puck_list_copy       

                # Now draw pucks, mouse tethers, and jets.

                # Draw boundaries of table.
                air_table.draw()

                for eachpuck in air_table.pucks:
                    eachpuck.draw()
                    if (eachpuck.jet != None):
                        if ((env.clients[eachpuck.client_name].Qcount < qCount_limit) or (
                                    eachpuck.client_name == 'local')):
                            eachpuck.jet.draw()
                            # eachpuck.gun.draw()

                for client_name in env.clients:
                    if (env.clients[client_name].selected_puck != None):
                        env.clients[client_name].draw_cursor_string()

                    # Draw cursors for network clients.
                    if ((client_name != 'local') and (env.clients[client_name].Qcount < qCount_limit)):
                        env.clients[client_name].draw_fancy_server_cursor()

                pygame.display.flip()
                dt_render_s = 0

            # Limit the rendering framerate to be below that of the physics calculations.
            dt_render_s += dt_physics_s

            # Keep track of time for deleting old bullets.
            env.time_s += dt_physics_s


# ============================================================
# Run the main program.    
# ============================================================

main()
