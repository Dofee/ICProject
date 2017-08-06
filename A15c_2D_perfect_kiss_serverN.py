# Filename: A15c_2D_perfect_kiss_serverN.py
# Author: James D. Miller; Gustavus Adolphus College.
# 11:32 AM Thu January 21, 2016

import sys, os
import pygame
import datetime
import math
import random
import time

import commands, platform

import inspect

# PyGame Constants
from pygame.locals import *
from pygame.color import THECOLORS

# PyGame gui
from pgu import gui

# Import the vector class from a local module (in this same directory)
from vec2d_jdm import Vec2D

# Networking
from PodSixNet.Server import Server
from PodSixNet.Channel import Channel
import socket

# Argument parsing...
import argparse

#=====================================================================
# Classes
#=====================================================================

class ClientChannel(Channel):
    def __init__(self, *args, **kwargs):
        Channel.__init__(self, *args, **kwargs)
    
    # def Network(self, data):
        # #print "Client State Dictionary:", data
        # #print "Network, data['ID']", data['ID']
        # pass
    
    def Network_CN(self, data):
        #global env
        
        # Store incoming data in the client objects.
        speaking_client_name = 'C' + str(data['ID'])
        
        # Check to make sure that this client is still in the client dictionary.
        if speaking_client_name in env.clients:
            # Mouse controls.
        
            env.clients[speaking_client_name].cursor_location_px = data['mXY']  # mouse x,y
            env.clients[speaking_client_name].buttonIsStillDown = data['mBd']   # mouse button down (true/false)
            env.clients[speaking_client_name].mouse_button = data['mB']         # mouse button number (1,2,3,0)
            
            # Jet controls.
            
            # Make the s key behave as a toggle.
            # If key is up, make it ready to accept the down ('D') event.
            if (data['s'] == 'U'):
                env.clients[speaking_client_name].key_s_onoff = 'ON'
                env.clients[speaking_client_name].key_s = data['s']
            # If getting 'D' from network client and the key is enabled.
            elif (env.clients[speaking_client_name].key_s_onoff == 'ON'):
                env.clients[speaking_client_name].key_s = data['s']
                
            env.clients[speaking_client_name].key_a = data['a']
            env.clients[speaking_client_name].key_d = data['d']
            env.clients[speaking_client_name].key_w = data['w']
            
            # Control for stopping all objects (f for freeze).
            env.clients[speaking_client_name].key_f = data['f']
            
            # Gun controls.
            
            # Make the k key behave as a toggle.
            # If key is up, make it ready to accept the down ('D') event.
            if (data['k'] == 'U'):
                env.clients[speaking_client_name].key_k_onoff = 'ON'
                env.clients[speaking_client_name].key_k = data['k']
            # If getting 'D' from network client and the key is enabled.
            elif (env.clients[speaking_client_name].key_k_onoff == 'ON'):
                env.clients[speaking_client_name].key_k = data['k']
            
            env.clients[speaking_client_name].key_j = data['j']
            env.clients[speaking_client_name].key_l = data['l']
            env.clients[speaking_client_name].key_i = data['i']
            env.clients[speaking_client_name].key_space = data[' ']
            
            # Keep track of client activity...
            env.clients[speaking_client_name].sendCount += 1
            
    def Close(self):
        print "A network client game pad has been closed."
     
     
class GameServer(Server):
    channelClass = ClientChannel
    
    def __init__(self, *args, **kwargs):
        Server.__init__(self, *args, **kwargs)
        self.client_count = 0
        
    # This runs when each client connects.
    def Connected(self, channel, addr):
        #print 'new connection (channel, addr):', channel, addr
        
        self.client_count += 1
        
        if (self.client_count <= 10):
            channel.Send({"action": "hello", "P_ID":self.client_count})
            client_name = 'C' + str(self.client_count)
            # Make a client and put it in the clients list.
            env.clients[client_name] = Client(env.client_colors[client_name])
            # Add the channel as an attribute of the client. Use this to Send to this client.
            env.clients[client_name].channel = channel
        else:
            channel.Send({"action": "hello", "P_ID":0})

        print "self.client_count =", self.client_count

        
class Client:
    def __init__(self, cursor_color):
        self.cursor_location_px = (0,0)   # x_px, y_px
        self.mouse_button = 1             # 1, 2, or 3
        self.buttonIsStillDown = False
        
        self.channel = 0
        # Jet
        self.key_a = "U"
        self.key_s = "U"
        self.key_s_onoff = "ON"
        self.key_d = "U"
        self.key_w = "U"
        
        # Gun
        self.key_j = "U"
        self.key_k = "U"
        self.key_k_onoff = "ON"
        self.key_l = "U"
        self.key_i = "U"
        self.key_space = "U"
        
        # Freeze it
        self.key_f = "U"
        
        # Zoom
        self.key_b = "U"
        self.key_n = "U"
        self.key_m = "U"
        self.key_h = "U"
        self.key_lctrl = 'U'
        
        self.selected_puck = None
        self.cursor_color = cursor_color
        self.bullet_hit_count = 0
        self.bullet_hit_limit = 50.0
        
        self.previousSendCount = 0
        self.sendCount = 0
        self.active = False
        
        # Define the nature of the cursor strings, one for each mouse button.
        self.mouse_strings = {'string1':{'c_drag':   2.0, 'k_Npm':   60.0},
                              'string2':{'c_drag':   0.2, 'k_Npm':    2.0},
                              'string3':{'c_drag':  20.0, 'k_Npm': 1000.0}}
                              #'string0':{'c_drag':   0.0, 'k_Npm':    0.0}}
                                        
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
            
            stringName = "string" + str(self.mouse_button)
            self.selected_puck.cursorString_spring_force_2d_N   += dx_2d_m * self.mouse_strings[stringName]['k_Npm']
            self.selected_puck.cursorString_puckDrag_force_2d_N += (self.selected_puck.vel_2d_mps * 
                                                                    -1 * self.mouse_strings[stringName]['c_drag'])
            
    def draw_cursor_string(self):
        line_points = [env.ConvertWorldToScreen(self.selected_puck.pos_2d_m), self.cursor_location_px]
        if (self.selected_puck != None):
            pygame.draw.line(game_window.surface, self.cursor_color, line_points[0], line_points[1], 1)
                    
    def draw_fancy_server_cursor(self):
        self.draw_server_cursor( self.cursor_color, 0)
        self.draw_server_cursor( THECOLORS["black"], 1)

    def draw_server_cursor(self, color, edge_px):
        cursor_outline_vertices = []
        cursor_outline_vertices.append(  self.cursor_location_px )
        cursor_outline_vertices.append( (self.cursor_location_px[0] + 10,  self.cursor_location_px[1] + 10) )
        cursor_outline_vertices.append( (self.cursor_location_px[0] +  0,  self.cursor_location_px[1] + 15) )
        
        pygame.draw.polygon(game_window.surface, color, cursor_outline_vertices, edge_px)

        
class runningAvg:
    def __init__(self, n_target):
        self.n_in_avg = 0
        self.n_target = n_target
        self.result = 0.0
        self.values = []
        self.total = 0.0
    
    def update(self, new_value):
        if self.n_in_avg < self.n_target:
            self.total += new_value
            self.n_in_avg += 1
        else:
            # Add the new value and subtract the oldest.
            self.total += new_value - self.values[0]
            # Discard the oldest value.
            self.values.pop(0)
        self.values.append(new_value)
        
        self.result = self.total / float(self.n_in_avg)
        return self.result
        
        
class Puck:
    def __init__(self, pos_2d_m, radius_m, density_kgpm2, puck_color = THECOLORS["grey"], coef_rest=0.85, CR_fixed=False,
                    vel_2d_mps=Vec2D(0.0,0.0)):
        self.radius_m = radius_m
        self.radius_px = int(round(env.px_from_m(self.radius_m * env.viewZoom)))

        self.density_kgpm2 = density_kgpm2    # mass per unit area
        self.mass_kg = self.density_kgpm2 * math.pi * self.radius_m ** 2
        
        self.coef_rest_default = coef_rest
        self.coef_rest = coef_rest
        # This parameter inhibits the changing of the puck's CR when gravity is toggled on and off.
        self.CR_fixed = CR_fixed
        
        self.pos_2d_m = pos_2d_m
        self.vel_2d_mps = vel_2d_mps
        
        self.SprDamp_force_2d_N = Vec2D(0.0,0.0)
        self.jet_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_spring_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_puckDrag_force_2d_N = Vec2D(0.0,0.0)

        self.impulse_2d_Ns = Vec2D(0.0,0.0)
        
        self.selected = False
        
        self.color = puck_color
        
        self.client_name = None
        self.jet = None
        self.gun = None
        
        self.hit = False
        self.hitflash_duration_timer_s = 0.0
        # Make the hit flash persist for this number of seconds:
        if platform.system() == 'Linux':
            self.hitflash_duration_timer_limit_s = 0.15        
        else:
            self.hitflash_duration_timer_limit_s = 0.05        
        
        # Bullet data...
        self.bullet = False
        self.birth_time_s = env.time_s
        self.age_limit_s = 3.0
        
        
    # If you print an object instance...
    def __str__(self):
        return "puck: x is %s, y is %s" % (self.pos_2d_m.x, self.pos_2d_m.y)
        
    def draw(self, tempColor=None):
        # Convert x,y to pixel screen location and then draw.
        
        self.pos_2d_px = env.ConvertWorldToScreen( self.pos_2d_m)
        #print "draw position", self.pos_px[0], self.pos_px[1]
        
        # Update based on zoom factor
        self.radius_px = int(round(env.px_from_m( self.radius_m)))
        if (self.radius_px < 3):
            self.radius_px = 3
            
        # Just after a hit, fill the whole circle with RED (i.e., thickness = 0).
        if self.hit:
            puck_circle_thickness = 0
            puck_color = THECOLORS["red"]
            self.hitflash_duration_timer_s += dt_render_s
            if self.hitflash_duration_timer_s > self.hitflash_duration_timer_limit_s:
                self.hit = False
        else:
            puck_circle_thickness = 3
            if (tempColor != None):
                puck_color = tempColor
            else:    
                puck_color = self.color
        
        # Draw main puck body. First, check these integers. If too large they can crash the
        # script as the python integers convert to c integers.
        if (abs(self.pos_2d_px[0]) < 1000) and (abs(self.pos_2d_px[1]) < 1000):
            pygame.draw.circle(game_window.surface, puck_color, self.pos_2d_px, self.radius_px, puck_circle_thickness)
        
            # Draw life (poor health) indicator circle.
            if (((self.client_name != None) and env.clients[self.client_name].active) or (self.client_name == 'test')) and (not self.bullet):
                spent_fraction = float(env.clients[self.client_name].bullet_hit_count) / float(env.clients[self.client_name].bullet_hit_limit)
                life_radius = spent_fraction * self.radius_px
                if (life_radius > 2.0):
                    life_radius_px = int(round(life_radius))
                else:
                    life_radius_px = 2
                
                pygame.draw.circle(game_window.surface, THECOLORS["red"], self.pos_2d_px, life_radius_px, 1)

            
class RotatingTube:
    def __init__(self, puck):
        # Associate the tube with the puck.
        self.puck = puck
    
        self.color = env.clients[self.puck.client_name].cursor_color
        
        # Degrees of rotation per second.
        #self.rotation_rate_dps = 360.0
        
        # Scaling factors to manage the aspect ratio of the tube.
        self.sf_x = 0.15
        self.sf_y = 0.50
        
        # Notice the counter-clockwise drawing pattern. Four vertices for a rectangle.
        # Each vertex is represented by a vector.
        self.tube_vertices_2d_m = [Vec2D(-0.50 * self.sf_x, 0.00 * self.sf_y), 
                                   Vec2D( 0.50 * self.sf_x, 0.00 * self.sf_y), 
                                   Vec2D( 0.50 * self.sf_x, 1.00 * self.sf_y),
                                   Vec2D(-0.50 * self.sf_x, 1.00 * self.sf_y)]
        
        # Define a normal (1 meter) pointing vector to keep track of the direction of the jet.
        self.direction_2d_m = Vec2D(0.0, 1.0)
        
    def rotate_vertices(self, vertices_2d_m, angle_deg):
        # Put modified vectors in a new list.
        rotated_vertices_2d_m = []
        for vertex_2d_m in vertices_2d_m:
            rotated_vertices_2d_m.append( vertex_2d_m.rotated( angle_deg))
        return rotated_vertices_2d_m
    
    def rotate_everything(self, angle_deg):
        # Rotate the pointer.
        self.direction_2d_m = self.direction_2d_m.rotated( angle_deg)
        
        # Rotate the tube.
        self.tube_vertices_2d_m = self.rotate_vertices( self.tube_vertices_2d_m, angle_deg)
                    
    def convert_from_world_to_screen(self, vertices_2d_m, base_point_2d_m):
        vertices_2d_px = []
        for vertex_2d_m in vertices_2d_m:
            # Calculate absolute position of this vertex.
            vertices_2d_px.append( env.ConvertWorldToScreen( vertex_2d_m + base_point_2d_m))
        return vertices_2d_px
        
    def draw_tube(self, line_thickness=3):
        # Draw the tube on the game-window surface. Establish the base_point as the center of the puck.
        pygame.draw.polygon(game_window.surface, self.color, 
                            self.convert_from_world_to_screen(self.tube_vertices_2d_m, self.puck.pos_2d_m), line_thickness)


class Jet( RotatingTube):
    def __init__(self, puck):
        RotatingTube.__init__(self, puck)
        
        # Degrees of rotation per second.
        self.rotation_rate_dps = 360.0
        
        self.color = THECOLORS["yellow"]
        
        # The jet flame (triangle)
        self.flame_vertices_2d_m =[Vec2D(-0.50 * self.sf_x, 1.02 * self.sf_y), 
                                   Vec2D( 0.50 * self.sf_x, 1.02 * self.sf_y), 
                                   Vec2D(-0.00 * self.sf_x, 1.80 * self.sf_y)]
                                   
        # Scaler magnitude of jet force.
        self.jet_force_N = 1.3 * self.puck.mass_kg * abs(air_table.gON_2d_mps2.y)
        
        # Point everything down for starters.
        self.rotate_everything( 180)
        
    def turn_jet_forces_onoff(self, client_name):
        if (env.clients[client_name].key_w == "D"):
            # Force on puck is in the opposite direction of the jet tube.
            self.puck.jet_force_2d_N = self.direction_2d_m * (-1) * self.jet_force_N
        else:    
            self.puck.jet_force_2d_N = self.direction_2d_m * 0.0
            
    def client_rotation_control(self, client_name):
        if (env.clients[client_name].key_a == "D"):
            self.rotate_everything( +1 * self.rotation_rate_dps * dt_render_s)
        if (env.clients[client_name].key_d == "D"):
            self.rotate_everything( -1 * self.rotation_rate_dps * dt_render_s)
        if (env.clients[client_name].key_s == "D"):
            # Rotate jet tube to be in the same direction as the motion of the puck.
            puck_velocity_angle = self.puck.vel_2d_mps.get_angle()
            current_jet_angle = self.direction_2d_m.get_angle()
            self.rotate_everything(puck_velocity_angle - current_jet_angle)
            
            #self.rotate_everything(180)
            
            # Reset this so it doesn't keep flipping. Just want it to flip the
            # direction once but not keep flipping.
            # This first line is enough to keep the local client from flipping again because
            # the local keyboard doesn't keep sending the "D" event if the key is held down.
            env.clients[client_name].key_s = "U"
            # This second one is also needed for the network clients because they keep
            # sending the "D" until they release the key.
            env.clients[client_name].key_s_onoff = "OFF"

    
    def rotate_everything(self, angle_deg):
        # Rotate the pointer.
        self.direction_2d_m = self.direction_2d_m.rotated( angle_deg)
        
        # Rotate the tube.
        self.tube_vertices_2d_m = self.rotate_vertices( self.tube_vertices_2d_m, angle_deg)
        
        # Rotate the flame.
        self.flame_vertices_2d_m = self.rotate_vertices( self.flame_vertices_2d_m, angle_deg)

    def draw(self):
        # Draw the jet tube.        
        self.draw_tube()
        
        # Draw the red flame.
        if (env.clients[self.puck.client_name].key_w == "D"):
            pygame.draw.polygon(game_window.surface, THECOLORS["red"], 
                                self.convert_from_world_to_screen(self.flame_vertices_2d_m, self.puck.pos_2d_m), 0)
                                
    
class Gun( RotatingTube):
    def __init__(self, puck):
        RotatingTube.__init__(self, puck)
        
        # Degrees of rotation per second.
        self.rotation_rate_dps = 180.0
        
        self.color = env.clients[self.puck.client_name].cursor_color
        
        # Run this method of the RotationTube class to set the initial angle of each new gun.
        self.rotate_everything( 45)
        
        self.bullet_speed_mps = 5.0
        self.fire_time_s = env.time_s
        self.firing_delay_s = 0.1
        self.bullet_count = 0
        self.bullet_count_limit = 10
        self.gun_recharge_wait_s = 2.5
        self.gun_recharge_start_time_s = env.time_s
        self.gun_recharging = False
        
        self.testing_gun = False
    
        self.shield = False
        self.shield_hit = False
        self.shield_hit_duration_s = 0.0
        # Make the hit remove the shield for this number of seconds:
        self.shield_hit_duration_limit_s = 0.05        
        self.shield_hit_count = 0
        self.shield_hit_count_limit = 20
        self.shield_recharging = False
        self.shield_recharge_wait_s = 4.0
        self.shield_recharge_start_time_s = env.time_s
    
    def client_rotation_control(self, client_name):
        if (env.clients[client_name].key_j == "D"):
            self.rotate_everything( +self.rotation_rate_dps * dt_render_s)
        if (env.clients[client_name].key_l == "D"):
            self.rotate_everything( -self.rotation_rate_dps * dt_render_s)
        if (env.clients[client_name].key_k == "D"):
            # Rotate jet tube to be in the same direction as the motion of the puck.
            puck_velocity_angle = self.puck.vel_2d_mps.get_angle()
            current_gun_angle = self.direction_2d_m.get_angle()
            self.rotate_everything(puck_velocity_angle - current_gun_angle)
            
            # Reset this so it doesn't keep flipping. Just want it to flip the
            # direction once but not keep flipping.
            # This first line is enough to keep the local client from flipping again because
            # the local keyboard doesn't keep sending the "D" event if the key is held down.
            env.clients[client_name].key_k = "U"
            # This second one is also needed for the network clients because they keep
            # sending the "D" until they release the key.
            env.clients[client_name].key_k_onoff = "OFF"
    
    def control_firing(self, client_name):
        # Fire only if the shield is off.
        if ((env.clients[client_name].key_i == "D") and (not self.shield)) or self.testing_gun:
            # Fire the gun.
            if ((env.time_s - self.fire_time_s) > self.firing_delay_s) and (not self.gun_recharging):
                self.fire_gun()
                self.bullet_count += 1
                # Timestamp the firing event.
                self.fire_time_s = env.time_s
        
        # Check to see if gun bullet count indicates the need to start recharging.
        if (self.bullet_count > self.bullet_count_limit):
            self.gun_recharge_start_time_s = env.time_s
            self.gun_recharging = True
            self.bullet_count = 0
        
        # If recharged.
        if (self.gun_recharging and (env.time_s - self.gun_recharge_start_time_s) > self.gun_recharge_wait_s):
            self.gun_recharging = False
                
    def fire_gun(self):
        bullet_radius_m = 0.05
        # Set the initial position of the bullet so that it clears (doesn't collide with) the host puck.
        initial_position_2d_m = (self.puck.pos_2d_m +
                                (self.direction_2d_m * (1.1 * self.puck.radius_m + 1.1 * bullet_radius_m)) )
        temp_bullet = Puck(initial_position_2d_m,  bullet_radius_m, 0.3)
        
        # Relative velocity of the bullet: the bullet velocity as seen from the host puck. This is the
        # speed of the bullet relative to the motion of the host puck (host velocity BEFORE the firing of 
        # the bullet).
        bullet_relative_vel_2d_mps = self.direction_2d_m * self.bullet_speed_mps
        
        # Absolute velocity of the bullet.
        temp_bullet.vel_2d_mps = self.puck.vel_2d_mps + bullet_relative_vel_2d_mps
        
        temp_bullet.bullet = True
        temp_bullet.color = env.clients[self.puck.client_name].cursor_color
        temp_bullet.client_name = self.puck.client_name
        
        air_table.pucks.append( temp_bullet)
        
        # Calculate the recoil impulse from firing the gun (opposite the direction of the bullet).
        self.puck.impulse_2d_Ns = bullet_relative_vel_2d_mps * temp_bullet.mass_kg * (-1)
    
    def control_shield(self, client_name):
        if (env.clients[client_name].key_space == "D") and (not self.shield_recharging):
            self.shield = True
        else:
            self.shield = False
        
        # Check to see if the shield hit count indicates the need to start recharging.
        if (self.shield_hit_count > self.shield_hit_count_limit):
            self.shield_recharge_start_time_s = env.time_s
            self.shield = False
            self.shield_recharging = True
            self.shield_hit_count = 0
        
        # If recharged.
        if (self.shield_recharging and (env.time_s - self.shield_recharge_start_time_s) > self.shield_recharge_wait_s):
            self.shield_recharging = False
    
    def draw(self):
        # Draw the gun tube.
        if (self.gun_recharging):
            line_thickness = 3
        else:
            line_thickness = 0
        
        # Draw the jet tube.
        self.draw_tube( line_thickness)
        
        # Draw the shield.
        if (self.shield):
            if self.shield_hit:
                # Don't draw the shield for a moment after the hit. This visualizes the shield hit.
                self.shield_hit_duration_s += dt_render_s
                if (self.shield_hit_duration_s > self.shield_hit_duration_limit_s):
                    self.shield_hit = False
                    
            else:
                pygame.draw.circle(game_window.surface, self.color, self.puck.pos_2d_px, self.puck.radius_px + 6, 4)

                
class Spring:
    def __init__(self, p1, p2, length_m=3.0, strength_Npm=0.5, spring_color=THECOLORS["yellow"], width_m=0.025, drag_c=0.0):
        
        # Optionally this spring can have one end pinned to a vector point. Do this by passing in p2 as a vector.
        if (p2.__class__.__name__ == 'Vec2D'):
            # Create a point puck at the pinning location.
            # The location of this point puck will never change because
            # it is not in the pucks list that is processed by the
            # physics engine.
            p2 = Puck( p2, 1.0, 1.0)
            p2.vel_2d_mps = Vec2D(0.0,0.0)
            length_m = 0.0
        
        self.p1 = p1
        self.p2 = p2
        self.p1p2_separation_2d_m = Vec2D(0,0)
        self.p1p2_separation_m = 0
        self.p1p2_normalized_2d = Vec2D(0,0)
        
        self.length_m = length_m
        self.strength_Npm = strength_Npm
        self.damper_Ns2pm2 = 0.5 #5.0 #0.05 #0.15
        self.unstretched_width_m = width_m #0.05
        
        self.drag_c = drag_c
        
        self.spring_vertices_2d_m = []
        self.spring_vertices_2d_px = []
        
        self.spring_color = spring_color
        self.draw_as_line = False
    
    def calc_spring_forces_on_pucks(self):
        self.p1p2_separation_2d_m = self.p1.pos_2d_m - self.p2.pos_2d_m
        
        self.p1p2_separation_m =  self.p1p2_separation_2d_m.length()
        
        # The pinned case needs to be able to handle the zero length spring. The 
        # separation distance will be zero when the pinned spring is at rest.
        # This will cause a divide by zero error if not handled here.
        if ((self.p1p2_separation_m == 0.0) and (self.length_m == 0.0)):
            spring_force_on_1_2d_N = Vec2D(0.0,0.0)
        else:
            self.p1p2_normalized_2d = self.p1p2_separation_2d_m / self.p1p2_separation_m
            
            # Spring force:  acts along the separation vector and is proportional to the separation distance.
            spring_force_on_1_2d_N = self.p1p2_normalized_2d * (self.length_m - self.p1p2_separation_m) * self.strength_Npm
        
        # Damper force: acts along the separation vector and is proportional to the relative speed.
        v_relative_2d_mps = self.p1.vel_2d_mps - self.p2.vel_2d_mps
        v_relative_alongNormal_2d_mps = v_relative_2d_mps.projection_onto(self.p1p2_separation_2d_m)
        damper_force_on_1_N = v_relative_alongNormal_2d_mps * self.damper_Ns2pm2
        
        # Net force by both spring and damper
        SprDamp_force_2d_N = spring_force_on_1_2d_N - damper_force_on_1_N
        
        # This force acts in opposite directions for each of the two pucks. Notice the "+=" here, this
        # is an aggregate across all the springs. This aggregate MUST be reset (zeroed) after the movements are
        # calculated. So by the time you've looped through all the springs, you get the NET force, one each ball, 
        # applied of all individual springs.
        self.p1.SprDamp_force_2d_N += SprDamp_force_2d_N * (+1)
        self.p2.SprDamp_force_2d_N += SprDamp_force_2d_N * (-1)
        
        # Add in some drag forces if a non-zero drag coef is specified. These are based on the
        # velocity of the pucks (not relative speed as is the case above for damper forces).
        self.p1.SprDamp_force_2d_N += self.p1.vel_2d_mps * (-1) * self.drag_c
        self.p2.SprDamp_force_2d_N += self.p2.vel_2d_mps * (-1) * self.drag_c

    def width_to_draw_m(self):
        width_m = self.unstretched_width_m * (1 + 0.30 * (self.length_m - self.p1p2_separation_m))
        if width_m < (0.05 * self.unstretched_width_m):
            self.draw_as_line = True
            width_m = 0.0
        else:
            self.draw_as_line = False
        return width_m
    
    def draw(self):
        # Change the width to indicate the stretch or compression in the spring. Note, it's good to 
        # do this outside of the main calc loop (using the rendering timer). No need to do all this each
        # time step.
        
        width_m = self.width_to_draw_m()
        
        # Calculate the four corners of the spring rectangle.
        p1p2_perpendicular_2d = self.p1p2_normalized_2d.rotate90()
        self.spring_vertices_2d_m = []
        self.spring_vertices_2d_m.append(self.p1.pos_2d_m + (p1p2_perpendicular_2d * width_m))
        self.spring_vertices_2d_m.append(self.p1.pos_2d_m - (p1p2_perpendicular_2d * width_m))
        self.spring_vertices_2d_m.append(self.p2.pos_2d_m - (p1p2_perpendicular_2d * width_m))
        self.spring_vertices_2d_m.append(self.p2.pos_2d_m + (p1p2_perpendicular_2d * width_m))
        
        # Transform from world to screen.
        self.spring_vertices_2d_px = []
        for vertice_2d_m in self.spring_vertices_2d_m:
            self.spring_vertices_2d_px.append( env.ConvertWorldToScreen( vertice_2d_m))
        
        # Draw the spring
        if self.draw_as_line == True:
            pygame.draw.aaline(game_window.surface, self.spring_color, env.ConvertWorldToScreen(self.p1.pos_2d_m),
                                                                       env.ConvertWorldToScreen(self.p2.pos_2d_m))
        else:
            pygame.draw.polygon(game_window.surface, self.spring_color, self.spring_vertices_2d_px)
        
        
class AirTable:
    def __init__(self, walls_dic):
        self.gON_2d_mps2 = Vec2D(-0.0, -9.0)
        self.gOFF_2d_mps2 = Vec2D(-0.0, -0.0)
        self.g_2d_mps2 = self.gOFF_2d_mps2
        self.g_ON = False
        
        self.pucks = []
        self.controlled_pucks = []
        self.springs = []
        self.walls = walls_dic
        self.collision_count = 0
        
        # Used for wall collisions.
        self.coef_rest = 1.0
        
        self.color_transfer = False
        
        self.stop_physics = False
        self.tangled = False

        self.perfect_kiss = False
        self.FPS_display = True
                             
    def draw(self):
        #{"L_m":0.0, "R_m":10.0, "B_m":0.0, "T_m":10.0}
        topLeft_2d_px =   env.ConvertWorldToScreen( Vec2D( self.walls['L_m'],        self.walls['T_m']))
        topRight_2d_px =  env.ConvertWorldToScreen( Vec2D( self.walls['R_m']-0.01,   self.walls['T_m']))
        botLeft_2d_px =   env.ConvertWorldToScreen( Vec2D( self.walls['L_m'],        self.walls['B_m']+0.01))
        botRight_2d_px =  env.ConvertWorldToScreen( Vec2D( self.walls['R_m']-0.01,   self.walls['B_m']+0.01))
        
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], topLeft_2d_px,  topRight_2d_px, 1)
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], topRight_2d_px, botRight_2d_px, 1)
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], botRight_2d_px, botLeft_2d_px,  1)
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], botLeft_2d_px,  topLeft_2d_px,  1)
    
    def checkForPuckAtThisPosition(self, x_px_or_tuple, y_px = None):
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
            if mag_of_difference_m2 < puck.radius_m**2:
                puck.selected = True
                return puck
        return None

    def update_PuckSpeedAndPosition(self, puck, dt_s):
        # Net resulting force on the puck.
        puck_forces_2d_N = (self.g_2d_mps2 * puck.mass_kg) + (puck.SprDamp_force_2d_N + 
                                                              puck.jet_force_2d_N +
                                                              puck.cursorString_spring_force_2d_N +
                                                              puck.cursorString_puckDrag_force_2d_N +
                                                              puck.impulse_2d_Ns/dt_s)
        
        # Acceleration from Newton's law.
        acc_2d_mps2 = puck_forces_2d_N / puck.mass_kg
        
        # Acceleration changes the velocity:  dv = a * dt
        # Velocity at the end of the timestep.
        puck.vel_2d_mps = puck.vel_2d_mps + (acc_2d_mps2 * dt_s)
        
        # Calculate the new physical puck position using the average velocity.
        # Velocity changes the position:  dx = v * dt
        puck.pos_2d_m = puck.pos_2d_m + (puck.vel_2d_mps * dt_s)
        
        # Now reset the aggregate forces.
        puck.SprDamp_force_2d_N = Vec2D(0.0,0.0)
        puck.cursorString_spring_force_2d_N = Vec2D(0.0,0.0)
        puck.cursorString_puckDrag_force_2d_N = Vec2D(0.0,0.0)
        puck.impulse_2d_Ns = Vec2D(0.0,0.0)
    
    def time_past_kiss(self, dt_s, puckA, puckB):
        # Determine the time between the kiss point and collision detection event (penetration time).
        
        initial_collision_angle = (puckA.pos_2d_m - puckB.pos_2d_m).get_angle_between(Vec2D(1.0,0.0))
        
        # As seen from B.
        puckA_relvel_2d_mps = puckA.vel_2d_mps - puckB.vel_2d_mps
        
        # Previous position vectors (position 1) of the two pucks
        puckA_1_pos_2d_m = puckA.pos_2d_m - puckA.vel_2d_mps * dt_s
        puckB_1_pos_2d_m = puckB.pos_2d_m - puckB.vel_2d_mps * dt_s
        
        # Position vector 2-prime of PuckA
        puckA_2p_pos_2d_m = puckA_1_pos_2d_m + puckA_relvel_2d_mps * dt_s
        
        # A check to see if the collision angle is the same in the new frame of reference (as seen from B).
        #final_collision_angle = (puckA_2p_pos_2d_m - puckB_1_pos_2d_m).get_angle_between(Vec2D(1.0,0.0))
        #print "collision_angle", initial_collision_angle, final_collision_angle
        
        #print "check =", (puckA_2p_pos_2d_m - puckB_1_pos_2d_m).length()/(puckA.radius_m + puckB.radius_m)
        
        # Prime path vectors
        prime_path_puckA_2d_m = puckA_2p_pos_2d_m - puckA_1_pos_2d_m
        prime_normalized_2d_m = prime_path_puckA_2d_m.normal()
        
        # Vector between the original positions of the two pucks.
        A1_B1_path_2d_m = puckB_1_pos_2d_m - puckA_1_pos_2d_m
        
        # Projection of A1_B1_path_2d_m onto the prime vector.
        A1_B1_projection_2d_m = A1_B1_path_2d_m.projection_onto( prime_path_puckA_2d_m)
        
        # B1 to prime path vector (vector to nearest point on prime path). The difference
        # between the B_1 vector and its projection onto the prime vector.
        B1_to_prime_2d_m = A1_B1_path_2d_m - A1_B1_projection_2d_m
        
        # Distance x (scaler). Distance between near point on prime and the A2K (kiss location of A2).
        x_m = ((puckA.radius_m + puckB.radius_m)**2 - B1_to_prime_2d_m.length_squared())**0.5
        x_2d_m = prime_normalized_2d_m * x_m
        
        # Kiss point vector
        puckA_2_kiss_2d_m = puckA_1_pos_2d_m + A1_B1_projection_2d_m - x_2d_m
        #print "A1_B1_projection_2d_m, x_2d_m =", A1_B1_projection_2d_m, x_2d_m
        
        # Vector between detection and kiss.
        d_2d_m = puckA_2p_pos_2d_m - puckA_2_kiss_2d_m
        #print "puckA_2p_pos_2d_m, puckA_2_kiss_2d_m =", puckA_2p_pos_2d_m, puckA_2_kiss_2d_m
        
        # Time between detection and kiss. Avoid zero in the denominator.
        if puckA_relvel_2d_mps.x > 0:
            time_between_kiss_and_detection_s = d_2d_m.x / puckA_relvel_2d_mps.x
            #print "d_2d_m.x, puckA_relvel_2d_mps.x =", d_2d_m.x, puckA_relvel_2d_mps.x
        else:
            time_between_kiss_and_detection_s = d_2d_m.y / puckA_relvel_2d_mps.y
            #print "d_2d_m.y, puckA_relvel_2d_mps.y =", d_2d_m.y, puckA_relvel_2d_mps.y
            
        return time_between_kiss_and_detection_s
    
    def check_for_collisions(self, dt_s):
        
        self.tangled = False
        
        # Wall collisions
        for i, puck in enumerate(self.pucks):
            if not env.inhibit_wall_collisions:
                if (((puck.pos_2d_m.y - puck.radius_m) < self.walls["B_m"]) or ((puck.pos_2d_m.y + puck.radius_m) > self.walls["T_m"])):
                    
                    if env.correct_for_wall_penetration:
                        if (puck.pos_2d_m.y - puck.radius_m) < self.walls["B_m"]:
                            penetration_y_m = self.walls["B_m"] - (puck.pos_2d_m.y - puck.radius_m)
                            puck.pos_2d_m.y += 2 * penetration_y_m
                    
                        if (puck.pos_2d_m.y + puck.radius_m) > self.walls["T_m"]:
                            penetration_y_m = (puck.pos_2d_m.y + puck.radius_m) - self.walls["T_m"]
                            puck.pos_2d_m.y -= 2 * penetration_y_m
                    
                    puck.vel_2d_mps.y *= -1 * min(self.coef_rest, puck.coef_rest)
                
                if (((puck.pos_2d_m.x - puck.radius_m) < self.walls["L_m"]) or ((puck.pos_2d_m.x + puck.radius_m) > self.walls["R_m"])):
                    
                    if env.correct_for_wall_penetration:
                        if (puck.pos_2d_m.x - puck.radius_m) < self.walls["L_m"]:
                            penetration_x_m = self.walls["L_m"] - (puck.pos_2d_m.x - puck.radius_m)
                            puck.pos_2d_m.x += 2 * penetration_x_m
                    
                        if (puck.pos_2d_m.x + puck.radius_m) > self.walls["R_m"]:
                            penetration_x_m = (puck.pos_2d_m.x + puck.radius_m) - self.walls["R_m"]
                            puck.pos_2d_m.x -= 2 * penetration_x_m
                            
                    puck.vel_2d_mps.x *= -1 * min(self.coef_rest, puck.coef_rest)
                
            # Collisions with other pucks. 
            for otherpuck in self.pucks[i+1:]:
                
                # Check if the two puck circles are overlapping.
                
                # Parallel to the normal
                puck_to_puck_2d_m = otherpuck.pos_2d_m - puck.pos_2d_m
                # Parallel to the tangent
                tangent_p_to_p_2d_m = Vec2D.rotate90(puck_to_puck_2d_m)
                
                # Separation between the pucks, squared (not a vector).
                p_to_p_m2 = puck_to_puck_2d_m.length_squared()
                
                # The sum of the radii of the two pucks, squared.
                r_plus_r_m2 = (puck.radius_m + otherpuck.radius_m)**2

                # A check for the Jello-madness game. If it's tangled, balls
                # will be close and this will be set to True.
                if (p_to_p_m2 < 1.1 * r_plus_r_m2):
                    self.tangled = True
                                    
                # Keep this collision check fast by avoiding square roots.
                if (p_to_p_m2 < r_plus_r_m2):
                    self.collision_count += 1
                    #print "collision_count", self.collision_count
                    
                    # If it's a bullet coming from another client, add to the
                    # hit count for non-bullet client.
                    if (puck.client_name != None) and (otherpuck.client_name != None):
                        if (puck.client_name != otherpuck.client_name): 
                            if (otherpuck.bullet and (not puck.bullet)):
                                if not puck.gun.shield:
                                    env.clients[puck.client_name].bullet_hit_count += 1
                                    puck.hit = True
                                    puck.hitflash_duration_timer_s = 0.0
                                else:
                                    puck.gun.shield_hit = True
                                    puck.gun.shield_hit_duration_s = 0.0
                                    puck.gun.shield_hit_count += 1
                    
                    if self.color_transfer == True:
                        #(puck.color, otherpuck.color) = (otherpuck.color, puck.color)
                        pass
                    
                    # Use the p_to_p vector (between the two colliding pucks) as projection target for 
                    # normal calculation.
                    
                    # Draw the overlapping pucks.
                    puck.draw(THECOLORS["red"]); otherpuck.draw(THECOLORS["red"])
                    
                    # The calculate velocity components along and perpendicular to the normal.
                    puck_normal_2d_mps = puck.vel_2d_mps.projection_onto(puck_to_puck_2d_m)
                    puck_tangent_2d_mps = puck.vel_2d_mps.projection_onto(tangent_p_to_p_2d_m)
                    
                    otherpuck_normal_2d_mps = otherpuck.vel_2d_mps.projection_onto(puck_to_puck_2d_m)
                    otherpuck_tangent_2d_mps = otherpuck.vel_2d_mps.projection_onto(tangent_p_to_p_2d_m)
                    
                    relative_normal_vel_2d_mps = otherpuck_normal_2d_mps - puck_normal_2d_mps
                    
                    if env.correct_for_puck_penetration:
                        # Back out a total of 2x of the penetration along the normal. Back-out amounts for each puck is 
                        # based on the velocity of each puck times 2DT where DT is the time of penetration. DT is calculated
                        # from the relative speed and the penetration distance.
                        
                        relative_normal_spd_mps = relative_normal_vel_2d_mps.length()
                        penetration_m = (puck.radius_m + otherpuck.radius_m) - p_to_p_m2**0.5
                        if (relative_normal_spd_mps > 0.00000):
                            if air_table.perfect_kiss:
                                # Use a special perfect-kiss method to determine the time.
                                penetration_time_s = self.time_past_kiss( dt_s, puck, otherpuck)
                            else:    
                                penetration_time_s = penetration_m / relative_normal_spd_mps
                            #print penetration_time_s, self.time_past_kiss( dt_s, puck, otherpuck)
                            
                            penetration_time_scaler_1 = 1.00  # This can be useful for testing to amplify and see the correction.
                            penetration_time_scaler_2 = 1.00
                            
                            # First, reverse the two pucks, to their collision point, along their incoming trajectory paths.
                            if air_table.perfect_kiss:
                                puck.pos_2d_m = puck.pos_2d_m - (puck.vel_2d_mps * (penetration_time_scaler_1 * penetration_time_s))
                                otherpuck.pos_2d_m = otherpuck.pos_2d_m - (otherpuck.vel_2d_mps * (penetration_time_scaler_1 * penetration_time_s))
                                
                                # Draw the perfect-kissing pucks (you'll only be able to see this in the example run that is started by pressing
                                # the 3 key on the number pad. This is one of the pool-shot examples that inhibits screen clears.
                                puck.draw(THECOLORS["cyan"]); otherpuck.draw(THECOLORS["cyan"])
                            
                            else:    
                                puck.pos_2d_m = puck.pos_2d_m - (puck_normal_2d_mps * (penetration_time_scaler_1 * penetration_time_s))
                                otherpuck.pos_2d_m = otherpuck.pos_2d_m - (otherpuck_normal_2d_mps * (penetration_time_scaler_1 * penetration_time_s))
                            
                            # # Test to see how close we got to the just-touching point. Ratio should be close to 1.0000
                            # test_center_to_center_separation = (puck.pos_2d_m - otherpuck.pos_2d_m).length() / (puck.radius_m + otherpuck.radius_m)
                            # print "ratio of c_to_c at kiss point =", '%.30f' % test_center_to_center_separation
                            
                            if air_table.perfect_kiss:
                                # Recalculate the tangent and normals based on the pucks in the just-touching position.
                                puck_to_puck_2d_m = otherpuck.pos_2d_m - puck.pos_2d_m
                                tangent_p_to_p_2d_m = Vec2D.rotate90(puck_to_puck_2d_m)
                                # The calculate velocity components along and perpendicular to the normal.
                                puck_normal_2d_mps = puck.vel_2d_mps.projection_onto(puck_to_puck_2d_m)
                                puck_tangent_2d_mps = puck.vel_2d_mps.projection_onto(tangent_p_to_p_2d_m)
                                otherpuck_normal_2d_mps = otherpuck.vel_2d_mps.projection_onto(puck_to_puck_2d_m)
                                otherpuck_tangent_2d_mps = otherpuck.vel_2d_mps.projection_onto(tangent_p_to_p_2d_m)
                            
                            # Calculate the velocities along the normal AFTER the collision. Use a CR (coefficient of restitution)
                            # of 1 here to better avoid stickiness.
                            CR_puck = 1
                            puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps = self.AandB_normal_AFTER_2d_mps( puck_normal_2d_mps, puck.mass_kg, otherpuck_normal_2d_mps, otherpuck.mass_kg, CR_puck)
                            
                            # Temp values for puck and otherpuck velocities after the collision.
                            puck_vel_2d_mps = puck_normal_AFTER_mps + puck_tangent_2d_mps
                            otherpuck_vel_2d_mps = otherpuck_normal_AFTER_mps + otherpuck_tangent_2d_mps
                            
                            # Finally, travel another penetration time worth of distance using these AFTER-collision velocities.
                            # This will put the pucks where they should have been at the time of collision detection.
                            if air_table.perfect_kiss:
                                puck.pos_2d_m = puck.pos_2d_m + (puck_vel_2d_mps * (penetration_time_scaler_2 * penetration_time_s))
                                otherpuck.pos_2d_m = otherpuck.pos_2d_m + (otherpuck_vel_2d_mps * (penetration_time_scaler_2 * penetration_time_s))
                            else:
                                puck.pos_2d_m = puck.pos_2d_m + (puck_normal_AFTER_mps * (penetration_time_scaler_2 * penetration_time_s))
                                otherpuck.pos_2d_m = otherpuck.pos_2d_m + (otherpuck_normal_AFTER_mps * (penetration_time_scaler_2 * penetration_time_s))
                            
                            # # Just to check, compare the corrected separation with the detected
                            # # overlap. This should be very close to 1.00000... for non-perfect_kiss correction approach.
                            # corrected_sep_m = (puck.pos_2d_m - otherpuck.pos_2d_m).length() - (puck.radius_m + otherpuck.radius_m)
                            # print "ratio of corrected_sep/penetration =", '%.30f' % (corrected_sep_m/penetration_m)
                            
                        else:
                            pass
                            #print "small relative speed"
                            #self.g_2d_mps2 = self.gOFF_2d_mps2
                            # for puck in self.pucks:
                                # puck.vel_2d_mps = Vec2D(0,0)
                           
                    # Assign the AFTER velocities (using the actual CR here) to the puck for use in the next frame calculation.
                    CR_puck = min(puck.coef_rest, otherpuck.coef_rest)
                    puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps = self.AandB_normal_AFTER_2d_mps( puck_normal_2d_mps, puck.mass_kg, otherpuck_normal_2d_mps, otherpuck.mass_kg, CR_puck)
                    
                    # Now that we're done using the current values, set them to the newly calculated AFTERs.
                    puck_normal_2d_mps, otherpuck_normal_2d_mps = puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps
                                        
                    # Add the components back together to get total velocity vectors for each puck.
                    puck.vel_2d_mps = puck_normal_2d_mps + puck_tangent_2d_mps
                    otherpuck.vel_2d_mps = otherpuck_normal_2d_mps + otherpuck_tangent_2d_mps
    
    def normal_AFTER_2d_mps(self, A_normal_BEFORE_2d_mps, A_mass_kg, B_normal_BEFORE_2d_mps, B_mass_kg, CR_puck):
        # For inputs as defined here, this returns the AFTER normal for the first puck in the inputs. So if B
        # is first, it returns the result for the B puck.
        relative_normal_vel_2d_mps = B_normal_BEFORE_2d_mps - A_normal_BEFORE_2d_mps
        return ( ( (relative_normal_vel_2d_mps * (CR_puck * B_mass_kg)) + 
                   (A_normal_BEFORE_2d_mps * A_mass_kg + B_normal_BEFORE_2d_mps * B_mass_kg) ) /
                   (A_mass_kg + B_mass_kg) ) 
    
    def AandB_normal_AFTER_2d_mps(self, A_normal_BEFORE_2d_mps, A_mass_kg, B_normal_BEFORE_2d_mps, B_mass_kg, CR_puck):
        A = self.normal_AFTER_2d_mps(A_normal_BEFORE_2d_mps, A_mass_kg, B_normal_BEFORE_2d_mps, B_mass_kg, CR_puck)
        # Make use of the symmetry in the physics to calculate the B-puck normal (put the B-puck data in the first inputs).
        B = self.normal_AFTER_2d_mps(B_normal_BEFORE_2d_mps, B_mass_kg, A_normal_BEFORE_2d_mps, A_mass_kg, CR_puck)
        return A, B
    

class Environment:
    def __init__(self, screenSize_px, length_x_m):
        self.screenSize_px = Vec2D(screenSize_px)
        self.viewOffset_2d_px = Vec2D(0,0)
        self.viewCenter_px = Vec2D(0,0)
        self.viewZoom = 1
        self.viewZoom_rate = 0.01
    
        self.px_to_m = length_x_m/float(self.screenSize_px.x)
        self.m_to_px = (float(self.screenSize_px.x)/length_x_m)
        
        self.client_colors = {'C1': THECOLORS["orangered1"],'C2': THECOLORS["tan"],'C3': THECOLORS["cyan"],'C4': THECOLORS["blue"],
                              'C5': THECOLORS["pink"], 'C6': THECOLORS["red"],'C7': THECOLORS["coral"],'C8': THECOLORS["green"],
                              'C9': THECOLORS["grey80"],'C10': THECOLORS["rosybrown3"],'test': THECOLORS["purple"]}
                              
        # Add a local (non-network) client to the client dictionary.
        self.clients = {'local':Client(THECOLORS["green"])}
        self.clients['local'].active = True
        
        # General clock time for determining bullet age.
        self.time_s = 0
        # Timer for the Jello Madness game.
        self.game_time_s = 0
        
        self.loopsSinceLastQuietCheck = 0
        
        self.inhibit_screen_clears = False
        self.inhibit_wall_collisions = False
        self.correct_for_wall_penetration = True
        self.correct_for_puck_penetration = True
        
        self.always_render = False
        self.constant_dt_physics = None
        
    def checkForQuietClients(self):
        self.loopsSinceLastQuietCheck += 1
        if self.loopsSinceLastQuietCheck > 20:
            self.loopsSinceLastQuietCheck = 0
            for clientname in self.clients:
                if clientname != 'local':
                    # Check for the no change case (client is quiet).
                    countChange = self.clients[clientname].sendCount - self.clients[clientname].previousSendCount
                    if countChange == 0:
                        self.clients[clientname].active = False
                    else:
                        self.clients[clientname].active = True
                    # Update the previous value for use in the next comparison.
                    self.clients[clientname].previousSendCount = self.clients[clientname].sendCount
                
    def remove_healthless_clients(self):
        # Make a list of terminal clients.
        #print len(air_table.pucks), len(air_table.controlled_pucks)
        
        spent_client_names = []
        for thisclient_name in self.clients:
            if self.clients[thisclient_name].bullet_hit_count > self.clients[thisclient_name].bullet_hit_limit:
                spent_client_names.append( thisclient_name)
                
                # Send the bad news if one of the network clients has died.
                if (thisclient_name not in ['local','test']):
                    self.clients[thisclient_name].channel.Send({"action": "badhealth", "message":"not good"})
                
                print "\"" + thisclient_name + "\"" + " has been popped. "
                
                # Reset the counter for the local client. That will keep this block from running repeatedly
                # when the local puck gets popped. Have to do this because the local client does not get
                # deleted below. That's so it can continue to receive keyboard and mouse input and reset the game
                # if needed. The local client always lives on even if its puck gets popped.
                if thisclient_name == 'local':
                    self.clients[thisclient_name].bullet_hit_count = 0
                
        pucks_list_copy = air_table.pucks[:]
        for puck in pucks_list_copy:
            if puck.client_name in spent_client_names:
                # Had to put this check in to prevent server crash on simultaneous death bullets between two clients.
                # Don't yet understand why this is necessary.
                if (puck in air_table.controlled_pucks):
                    air_table.controlled_pucks.remove( puck)
                    #print "\"" + puck.client_name + "\"" + " has been removed from the controlled puck list."
                    
                air_table.pucks.remove( puck)
        
        for spent_client in spent_client_names:
            # Remove client from client dictionary
            if (spent_client != 'local'):
                del self.clients[ spent_client]
              
        del pucks_list_copy
    
    # Convert from meters to pixels 
    def px_from_m(self, dx_m):
        return dx_m * self.m_to_px * self.viewZoom
    
    # Convert from pixels to meters
    # Note: still floating values here)
    def m_from_px(self, dx_px):
        return float(dx_px) * self.px_to_m / self.viewZoom
    
    def control_zoom_and_view(self):
        if self.clients['local'].key_h == "D":
            self.viewZoom += self.viewZoom_rate * self.viewZoom
        if self.clients['local'].key_n == "D":
            self.viewZoom -= self.viewZoom_rate * self.viewZoom
    
    def ConvertScreenToWorld(self, point_2d_px):
        #self.viewOffset_2d_px = self.viewCenter_px
        x_m = (                       point_2d_px.x + self.viewOffset_2d_px.x) / (self.m_to_px * self.viewZoom)
        y_m = (self.screenSize_px.y - point_2d_px.y + self.viewOffset_2d_px.y) / (self.m_to_px * self.viewZoom)
        return Vec2D( x_m, y_m)

    def ConvertWorldToScreen(self, point_2d_m):
        """
        Convert from world to screen coordinates (pixels).
        In the class instance, we store a zoom factor, an offset indicating where
        the view extents start at, and the screen size (in pixels).
        """

        # self.viewOffset = self.viewCenter - self.screenSize_px/2
        #self.viewOffset = self.viewCenter_px
        x_px = (point_2d_m.x * self.m_to_px * self.viewZoom) - self.viewOffset_2d_px.x
        y_px = (point_2d_m.y * self.m_to_px * self.viewZoom) - self.viewOffset_2d_px.y
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
                elif (event.key==K_KP1):            
                    return "1p"
                elif (event.key==K_KP2):            
                    return "2p"
                elif (event.key==K_KP3):            
                    return "3p"
                elif (event.key==K_1):            
                    return 1           
                elif (event.key==K_2):                          
                    return 2
                elif (event.key==K_3):
                    return 3           
                elif (event.key==K_4):
                    return 4           
                elif (event.key==K_5):
                    return 5
                elif (event.key==K_6):
                    return 6
                elif (event.key==K_7):
                    return 7
                elif (event.key==K_8):
                    return 8
                elif (event.key==K_9):
                    return 9
                elif (event.key==K_0):
                    return 0
                
                elif (event.key==K_c):
                    # Toggle color option.
                    air_table.color_transfer = not air_table.color_transfer
                    #form['ColorTransfer'].value = air_table.color_transfer
                
                elif (event.key==K_f):
                    # Stop all the pucks...
                    for puck in air_table.pucks:
                        puck.vel_2d_mps = Vec2D(0,0)
                
                elif (event.key==K_g):
                    # Toggle the logical flag for g.
                    air_table.g_ON = not air_table.g_ON
                    print "g", air_table.g_ON
                    
                    if air_table.g_ON:
                        air_table.g_2d_mps2 = air_table.gON_2d_mps2
                        for eachpuck in air_table.pucks:
                            eachpuck.coef_rest = eachpuck.coef_rest_default
                    else:
                        air_table.g_2d_mps2 = air_table.gOFF_2d_mps2
                        for eachpuck in air_table.pucks:
                            if not eachpuck.CR_fixed:
                                eachpuck.coef_rest = 1.0
                
                elif (event.key==K_F1):
                    # Toggle FPS display on/off
                    air_table.FPS_display = not air_table.FPS_display
                
                elif (event.key==K_z):
                    air_table.perfect_kiss = not air_table.perfect_kiss
                    
                # Jet keys
                elif (event.key==K_a):
                    local_user.key_a = 'D'
                elif (event.key==K_s):
                    local_user.key_s = 'D'
                elif (event.key==K_d):
                    local_user.key_d = 'D'
                elif (event.key==K_w):
                    local_user.key_w = 'D'
                
                # Gun keys
                elif (event.key==K_j):
                    local_user.key_j = 'D'
                elif (event.key==K_k):
                    local_user.key_k = 'D'
                elif (event.key==K_l):
                    local_user.key_l = 'D'
                elif (event.key==K_i):
                    local_user.key_i = 'D'
                elif (event.key==K_SPACE):
                    local_user.key_space = 'D'
                    
                # Zoom keys
                elif (event.key==K_b):
                    local_user.key_b = 'D'
                elif (event.key==K_n):
                    local_user.key_n = 'D'
                elif (event.key==K_m):
                    local_user.key_m = 'D'
                elif (event.key==K_h):
                    local_user.key_h = 'D'
                elif (event.key==K_LCTRL):
                    #print "lctrl--> D"
                    local_user.key_lctrl = 'D'                    
                
                # Control physics for Jello Madness
                elif (event.key==K_p):
                    air_table.stop_physics = not air_table.stop_physics
                    if (not air_table.stop_physics):
                        env.game_time_s = 0
                
                elif (event.key==K_e):
                    #env.inhibit_screen_clears = not env.inhibit_screen_clears
                    pass
                    
                else:
                    return "nothing set up for this key"
            
            elif (event.type == pygame.KEYUP):
                # Jet keys
                if   (event.key==K_a):
                    local_user.key_a = 'U'
                elif (event.key==K_s):
                    local_user.key_s = 'U'
                elif (event.key==K_d):
                    local_user.key_d = 'U'
                elif (event.key==K_w):
                    local_user.key_w = 'U'
                
                # Gun keys
                elif (event.key==K_j):
                    local_user.key_j = 'U'
                elif (event.key==K_k):
                    local_user.key_k = 'U'
                elif (event.key==K_l):
                    local_user.key_l = 'U'
                elif (event.key==K_i):
                    local_user.key_i = 'U'
                elif (event.key==K_SPACE):
                    local_user.key_space = 'U'
                    
                # Zoom keys
                elif (event.key==K_b):
                    local_user.key_b = 'U'
                elif (event.key==K_n):
                    local_user.key_n = 'U'
                elif (event.key==K_m):
                    local_user.key_m = 'U'
                elif (event.key==K_h):
                    local_user.key_h = 'U'
                elif (event.key==K_LCTRL):
                    local_user.key_lctrl = 'U'
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
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
                
            elif ((event.type == pygame.MOUSEMOTION) and (local_user.key_lctrl == 'D')):
                #print "in mousemotion block", event.pos, event.rel[0], event.rel[1]
                self.viewOffset_2d_px -= Vec2D(event.rel[0], -event.rel[1])
            
            # In all cases, pass the event to the Gui.
            #app.event(event)
        
        if local_user.buttonIsStillDown:
            # This will select a puck when the puck runs into the cursor of the mouse with it's button still down.
            local_user.cursor_location_px = (mouseX, mouseY) = pygame.mouse.get_pos()

        
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
        pygame.display.set_caption( title)
        self.caption = title
    
    def update(self):
        pygame.display.update()
        
    def clear(self):
        # Useful for shifting between the various demos.
        self.surface.fill(THECOLORS["black"])
        pygame.display.update()

        
#===========================================================
# Functions
#===========================================================

def setup_pool_shot():
    env.always_render = True
    env.constant_dt_physics = 1/20.0
    
    air_table.coef_rest_puck =  1.00
    env.inhibit_wall_collisions = True
    env.inhibit_screen_clears = True
    
    # Randomize the starting x position of the incoming puck. 
    air_table.pucks.append( Puck(Vec2D(random.random()-0.3, 4.80), 0.45, 0.3, THECOLORS["orange"], vel_2d_mps=Vec2D(  25.0, 0.0)) )
    air_table.pucks.append( Puck(Vec2D(4.0,                 4.30), 0.45, 0.3,                      vel_2d_mps=Vec2D(   0.0, 0.0)) )
       
def make_some_pucks(resetmode):
    game_window.update_caption("Air Table V.3: Demo #" + str(resetmode)) 
    env.inhibit_wall_collisions = False
    env.inhibit_screen_clears = False
    env.correct_for_wall_penetration = True
    env.correct_for_puck_penetration = True
    
    env.always_render = False
    env.constant_dt_physics = None
    air_table.perfect_kiss = False
    
    if resetmode == '1p':
        env.correct_for_puck_penetration = False
        setup_pool_shot()
        
    elif resetmode == '2p':
        env.correct_for_puck_penetration = True
        air_table.perfect_kiss = False
        setup_pool_shot()
        
    elif resetmode == '3p':
        env.correct_for_puck_penetration = True
        air_table.perfect_kiss = True
        setup_pool_shot()
        
    elif resetmode == 1:
        #                                              ,radius,density
        air_table.pucks.append( Puck(Vec2D(2.5, 7.5), 0.25, 0.3, THECOLORS["orange"]))
        air_table.pucks.append( Puck(Vec2D(6.0, 2.5), 0.45, 0.3)) # maybe not.
        air_table.pucks.append( Puck(Vec2D(7.5, 2.5), 0.65, 0.3)) 
        air_table.pucks.append( Puck(Vec2D(2.5, 5.5), 1.65, 0.3))
        air_table.pucks.append( Puck(Vec2D(7.5, 7.5), 0.95, 0.3))
    
    
    elif resetmode == 2:
        spacing_factor = 2.0
        grid_size = 4,2
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k) == (1,1)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]
                
                air_table.pucks.append( Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.75, 0.3, puck_color=puck_color_value))
    
    
    elif resetmode == 3:
        spacing_factor = 1.5
        grid_size = 5,3
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k) == (2,2)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]

                air_table.pucks.append( Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.55, 0.3, puck_color=puck_color_value))

    
    elif resetmode == 4:
        spacing_factor = 1.0      
        
        if platform.system() == 'Linux':
            grid_size = 5,4
        else:    
            grid_size = 7,7
        
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k) == (2,2)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]
                
                air_table.pucks.append( Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), radius_m=0.25, density_kgpm2=1.0, 
                                             puck_color=puck_color_value,
                                             CR_fixed=False, coef_rest=0.9) )
            
    elif resetmode == 5:
        air_table.pucks.append( Puck(Vec2D(2.00, 3.00),  0.4, 0.3) )
        air_table.pucks.append( Puck(Vec2D(3.50, 4.50),  0.4, 0.3) )
        
        # No springs on this one.
        #air_table.pucks.append( Puck(Vec2D(3.50, 7.00),  0.95, 0.3) )
    
        spring_strength_Npm2 = 20.0 #18.0
        spring_length_m = 1.5
        air_table.springs.append( Spring(air_table.pucks[0], air_table.pucks[1], spring_length_m, spring_strength_Npm2, width_m=0.2))
    
    
    elif resetmode == 6:
        if platform.system() == 'Linux':
            density = 2.0
            radius = 0.7
            
            # Lower the CR for these pucks and fix them, using CR_fixed, so when gravity 
            # toggles on/off they stay at these levels.
            coef_rest_puck =  0.50
            
            spring_strength_Npm2 = 300.0
            spring_length_m = 2.5
            spring_width_m = 0.07
            spring_drag = 0.0
            spring_damper = 10.0
        else:
            density = 1.5
            radius = 0.7
            
            coef_rest_puck =  0.70
            
            spring_strength_Npm2 = 400.0
            spring_length_m = 2.5
            spring_width_m = 0.07
            spring_drag = 0.0
            spring_damper = 5.0

        air_table.pucks.append( Puck(Vec2D(2.00, 3.00),  radius, density, coef_rest=coef_rest_puck, CR_fixed=True) )
        air_table.pucks.append( Puck(Vec2D(3.50, 4.50),  radius, density, coef_rest=coef_rest_puck, CR_fixed=True) )
        air_table.pucks.append( Puck(Vec2D(5.00, 3.00),  radius, density, coef_rest=coef_rest_puck, CR_fixed=True) )
        
        # No springs on this one.
        air_table.pucks.append( Puck(Vec2D(3.50, 7.00),  0.95, density, coef_rest=coef_rest_puck, CR_fixed=True) )
        
        air_table.springs.append( Spring(air_table.pucks[0], air_table.pucks[1],
                                         spring_length_m, spring_strength_Npm2, width_m=spring_width_m, drag_c=spring_drag))
        air_table.springs.append( Spring(air_table.pucks[1], air_table.pucks[2],
                                         spring_length_m, spring_strength_Npm2, width_m=spring_width_m, drag_c=spring_drag))
        air_table.springs.append( Spring(air_table.pucks[2], air_table.pucks[0],
                                         spring_length_m, spring_strength_Npm2, width_m=spring_width_m, drag_c=spring_drag))
        
        # Increase the shock-absorber strength for each spring.
        for spring in air_table.springs:                                 
            spring.damper_Ns2pm2 = spring_damper

            
    elif resetmode == 7:
        air_table.collision_checking_enabled = True
        env.game_time_s = 0    
        offset_xy_m = Vec2D(2.5, 2.1) 
        
        if platform.system() == 'Linux':
            spacing_factor = 1.0
            grid_size = 3
            density = 45.0
            radius = 0.25
            spring_strength_Npm2 = 800.0 #18.0
            spring_length_m = 1.2
            spring_damper_Ns2pm2 = 5.0
        else:
            spacing_factor = 1.0
            grid_size = 4 
            density = 5.0
            radius = 0.25 
            spring_strength_Npm2 = 800.0 #18.0
            spring_length_m = 1.2            
            spring_damper_Ns2pm2 = 5.0
        
        grid = grid_size, grid_size
        
        for j in range(grid[0]):
            for k in range(grid[1]):
                if ((j,k) == (2,2)):
                    air_table.pucks.append( Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)) + offset_xy_m, radius, density, THECOLORS["orange"]))
                else:
                    air_table.pucks.append( Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)) + offset_xy_m, radius, density))

                    
        for m in range(grid_size*(grid_size-1)):
            air_table.springs.append( Spring(air_table.pucks[m], air_table.pucks[m+grid_size], spring_length_m, spring_strength_Npm2, spring_color=THECOLORS["blue"]))
        
        for m in range(grid_size-1):
            for n in range(grid_size):
                o_index = m + (n * grid_size)
                #print "index:", m, n, o_index, o_index+1
                air_table.springs.append( Spring(air_table.pucks[o_index], air_table.pucks[o_index+1], spring_length_m, spring_strength_Npm2, spring_color=THECOLORS["blue"]))
        
        for m in range(0, grid_size-1):
            for n in range(1, grid_size):
                o_index = m + (n * grid_size)
                air_table.springs.append( Spring(air_table.pucks[o_index], air_table.pucks[o_index-(grid_size-1)], spring_length_m, spring_strength_Npm2, spring_color=THECOLORS["yellow"]))
        
        for m in range(0, grid_size-1):
            for n in range(0, grid_size-1):
                o_index = m + (n * grid_size)
                air_table.springs.append( Spring(air_table.pucks[o_index], air_table.pucks[o_index+(grid_size+1)], spring_length_m, spring_strength_Npm2, spring_color=THECOLORS["yellow"]))


        # Increase the shock-absorber strength for each spring.
        for spring in air_table.springs:                                
            spring.damper_Ns2pm2 = spring_damper_Ns2pm2   
            
            
    elif resetmode == 8:
        air_table.collision_checking_enabled = True
        

        if platform.system() == 'Linux':
            # for Raspberry Pi
            density = 1.0
            
            #                                           ,radius,density
            air_table.pucks.append( Puck(Vec2D(5.0, 2.5), 0.30, density))
            air_table.pucks.append( Puck(Vec2D(4.0, 2.5), 0.30, density))
            air_table.pucks.append( Puck(Vec2D(7.5, 2.5), 0.65, density))
            air_table.pucks.append( Puck(Vec2D(7.5, 5.0), 0.85, density))
            air_table.pucks.append( Puck(Vec2D(7.5, 7.5), 1.15, density))

            # Make some pinned-spring pucks.
            for m in range(0, 3): 
                pinPoint_2d = Vec2D(2.0 + float(m) * 1.65, 4.0)
                tempPuck = Puck(pinPoint_2d, 0.7, density*5.0,  THECOLORS["orange"])
                air_table.pucks.append( tempPuck)
                air_table.springs.append( Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, width_m=0.02, drag_c = 1.5 + 10.0))
        else:
            density = 0.7
            
            #                                           ,radius,density
            air_table.pucks.append( Puck(Vec2D(5.0, 2.5), 0.15, density))
            air_table.pucks.append( Puck(Vec2D(4.0, 2.5), 0.15, density))
            air_table.pucks.append( Puck(Vec2D(7.5, 2.5), 0.65, density))
            air_table.pucks.append( Puck(Vec2D(7.5, 5.0), 0.85, density))
            air_table.pucks.append( Puck(Vec2D(7.5, 7.5), 1.15, density))

            # Make some pinned-spring pucks.
            for m in range(0, 6): 
                pinPoint_2d = Vec2D(2.0 + float(m) * 0.65, 4.0)
                tempPuck = Puck(pinPoint_2d, 0.25, density,  THECOLORS["orange"])
                air_table.pucks.append( tempPuck)
                air_table.springs.append( Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, width_m=0.02, drag_c=1.5))
        

        # Make user/client controllable pucks
        # for all the clients.
        y_puck_position_m = 1.0
        for client_name in env.clients:
            if env.clients[client_name].active:
                tempPuck = Puck(Vec2D(6.0, y_puck_position_m), 0.45, density)
                # Let the puck reference the jet and the jet reference the puck.
                tempPuck.client_name = client_name
                tempPuck.jet = Jet( tempPuck)
                tempPuck.gun = Gun( tempPuck)

                air_table.pucks.append( tempPuck)
                air_table.controlled_pucks.append( tempPuck)
                y_puck_position_m += 1.2
                
                # Reset the hit counters.
                env.clients[client_name].bullet_hit_count = 0
        
        # Keep gun on in a testing puck...

        if args.testPuck == 'on':
            tempPuck = Puck(Vec2D(6.0, y_puck_position_m), 0.45, density)
            # Let the puck reference the jet and the jet reference the puck.
            tempPuck.client_name = "test"
            env.clients[tempPuck.client_name] = Client(env.client_colors[tempPuck.client_name])
            tempPuck.jet = Jet( tempPuck)
            tempPuck.gun = Gun( tempPuck)
            tempPuck.gun.testing_gun = True
            # The default position at instantiation is 45 degrees counter-clockwise from vertical.
            # The degree value specified here is relative to that +45. Negative values are clockwise.
            tempPuck.gun.rotate_everything( -110)
            air_table.pucks.append( tempPuck)
            air_table.controlled_pucks.append( tempPuck)
        
    
    elif resetmode == 9:
        air_table.coef_rest_puck =  0.85
        air_table.coef_rest_table = 0.85
        
        # Make user/client controllable pucks
        # for all the clients.
        y_puck_position_m = 1.0
        for client_name in env.clients:
            if env.clients[client_name].active:
                tempPuck = Puck(Vec2D(6.0, y_puck_position_m), 0.45, 0.3)
                # Let the puck reference the jet and the jet reference the puck.
                tempPuck.client_name = client_name
                tempPuck.jet = Jet( tempPuck)
                tempPuck.gun = Gun( tempPuck)

                air_table.pucks.append( tempPuck)
                air_table.controlled_pucks.append( tempPuck)
                y_puck_position_m += 1.2
    
    else:
        print "Nothing set up for this key."

        
def display_number(numeric_value, font_object,  mode='FPS'):
    if mode=='FPS':
        # Small background rectangle for FPS text
        pygame.draw.rect(game_window.surface, THECOLORS["white"], pygame.Rect(10, 10, 35, 20))
        # The text
        fps_string = "%.0f" % numeric_value
        txt_surface = font_object.render(fps_string, True, THECOLORS["black"])
        game_window.surface.blit(txt_surface, [18, 11])
    elif mode=='gameTimer':
        # The text
        fps_string = "%.2f" % numeric_value
        txt_surface = font_object.render(fps_string, True, THECOLORS["white"])
        game_window.surface.blit(txt_surface, [600, 11])
    
        
#============================================================
# Main procedural script.
#============================================================

def main():

    # A few globals.
    global env, game_window, air_table, args, dt_render_s
    
    # Parse parameters provided in the command line.
    # This description string (and parameter help) gets displayed if help is requested (-h added after the filename).
    parser = argparse.ArgumentParser(description='Please add optional client parameters after the file name. For example: \n' + 
                                                 'A16c_2D_B2D_serverN.py off')
    # An optional positional argument.
    parser.add_argument('testPuck', type=str, nargs='?', default='on', help='Please indicate whether the practice puck should be on or off (default is on).')                              
                                    
    args = parser.parse_args()
    print "testPuck:", args.testPuck
    
    pygame.init()

    myclock = pygame.time.Clock()

    if platform.system() == 'Linux':
        window_dimensions_px = (800, 700)   #window_width_px, window_height_px   (600, 500)
    else:
        window_dimensions_px = (800, 700)   #window_width_px, window_height_px   (800, 700)

    # Create the first user/client and the methods for moving between the screen and the world.
    env = Environment(window_dimensions_px, 10.0) # 10m in along the x axis.

    game_window = GameWindow(window_dimensions_px, 'Air Table Server V.2')

    # Define the Left, Right, Bottom, and Top boundaries of the game window.
    air_table = AirTable({"L_m":0.0, "R_m":game_window.UR_2d_m.x, "B_m":0.0, "T_m":game_window.UR_2d_m.y})

    # Add some pucks to the table.
    demo_mode = 1
    make_some_pucks( demo_mode)

    # Setup network server.
    if platform.system() == 'Linux':
        local_ip = commands.getoutput("hostname -I")
    else:
        local_ip = socket.gethostbyname(socket.gethostname())
    print "Server IP address:", local_ip
    game_server = GameServer(localaddr=(local_ip, 4330))

    # Font object for rendering text onto display surface.
    fnt_FPS = pygame.font.SysFont("Arial", 14)
    fnt_gameTimer = pygame.font.SysFont("Arial", 60)
    
    # Limit the framerate, but let it float below this limit.
    framerate_limit = 480.0   # 480  
    dt_render_s = 0.0
    dt_render_limit_s = 1.0/120.0 # = 1.0/render_framerate. Use 1/120 OR, use 1/60 for single collisions with tails (1p, 2p, and e key).

    # An object containing the running average of the framerate of the physics calculations.
    if platform.system() == 'Linux':
        FR_avg = runningAvg(50) #50
    else:
        FR_avg = runningAvg(300) #500
    
    while True:
        if (env.constant_dt_physics != None):
            dt_physics_s = env.constant_dt_physics     # Use this line for (1p, 2p, key demos).
            time.sleep( env.constant_dt_physics)
        else:
            dt_physics_s = float(myclock.tick( framerate_limit) * 1e-3)
        
        #print dt_physics_s, myclock.get_fps()
        
        if air_table.FPS_display:
            FR_avg.update(1/dt_physics_s)
        
        # Get input from local user.
        resetmode = env.get_local_user_input()
        
        # This dt check avoids problem when dragging the game window.
        if ( ((dt_physics_s < 0.10) and (not air_table.stop_physics)) or env.always_render):
            
            ok_to_render = (dt_render_s > dt_render_limit_s) or env.always_render
            
            # Reset the game based on local user control.
            if resetmode in ["1p","2p","3p",1,2,3,4,5,6,7,8,9,0]:
                demo_mode = resetmode
                print resetmode
                # This should remove all references to the pucks and effectively kill them off. If there were other
                # variables referring to this list, this would not stop the pucks.
                
                # Delete all the objects on the table. Cleaning out these list reference to these objects effectively
                # deletes the objects. Notice the controlled list must be cleared also.
                air_table.pucks = []
                air_table.controlled_pucks = []
                air_table.springs = []
                
                # Now just black out the screen.
                game_window.clear()
                
                # Reinitialize the demo.
                make_some_pucks( demo_mode)               
                        
            if ok_to_render:
                # Get input from network clients.
                game_server.Pump()
                env.checkForQuietClients()
                
            for client_name in env.clients:
                # Calculate client related forces.
                env.clients[client_name].calc_string_forces_on_pucks()
                
            if ok_to_render:
                # Control the zoom
                env.control_zoom_and_view()
                
                for controlled_puck in air_table.controlled_pucks:
                    # Rotate based on keyboard of the controlling client.
                    controlled_puck.jet.client_rotation_control( controlled_puck.client_name)
                    controlled_puck.gun.client_rotation_control( controlled_puck.client_name)
                    
                    # Turn gun on/off
                    controlled_puck.gun.control_firing( controlled_puck.client_name)
                    
                    # Turn shield on/off
                    controlled_puck.gun.control_shield( controlled_puck.client_name)
                    
            
            # Calculate jet forces on pucks...
            for controlled_puck in air_table.controlled_pucks:
                controlled_puck.jet.turn_jet_forces_onoff( controlled_puck.client_name)
            
            # Calculate the forces the springs apply on the pucks...
            for eachspring in air_table.springs:
                eachspring.calc_spring_forces_on_pucks()
                
            # Apply forces to the pucks and calculate movements.
            for eachpuck in air_table.pucks:
                air_table.update_PuckSpeedAndPosition( eachpuck, dt_physics_s)
            
            # Check for puck-wall and puck-puck collisions and make penetration corrections.
            air_table.check_for_collisions( dt_physics_s)
            
            if ok_to_render:
                
                # Erase the blackboard.
                if not env.inhibit_screen_clears:
                    if (air_table.perfect_kiss):
                        gray_level = 40
                        game_window.surface.fill((gray_level,gray_level,gray_level))
                    else:
                        if not air_table.g_ON:
                            game_window.surface.fill((0,0,0))  # Black
                        else:
                            #gray_level = 50
                            #game_window.surface.fill((gray_level,gray_level,gray_level))
                            game_window.surface.fill((0,82,110))  # Blue
                
                # Display game timer text.
                if air_table.FPS_display:
                    display_number(FR_avg.result, fnt_FPS, mode='FPS')
                    #display_number(1/dt_physics_s, fnt_FPS, mode='FPS')
                if (demo_mode == 7):
                    display_number(env.game_time_s, fnt_gameTimer, mode='gameTimer')
                
                # Clean out old bullets.
                puck_list_copy = air_table.pucks[:]
                for thisPuck in puck_list_copy:
                    if (thisPuck.bullet) and ((env.time_s - thisPuck.birth_time_s) > thisPuck.age_limit_s):
                        air_table.pucks.remove(thisPuck)
                del puck_list_copy       
                
                # Now draw pucks, springs, mouse tethers, and jets.
                
                # Draw boundaries of table.
                air_table.draw()
                
                for eachpuck in air_table.pucks: 
                    eachpuck.draw()
                    if (eachpuck.jet != None):
                        if env.clients[eachpuck.client_name].active or (eachpuck.client_name == 'test'):
                            eachpuck.jet.draw()
                            eachpuck.gun.draw()
                    
                for eachspring in air_table.springs: 
                    eachspring.draw()
                
                env.remove_healthless_clients()
                
                for client_name in env.clients:
                    if (env.clients[client_name].selected_puck != None):
                        env.clients[client_name].draw_cursor_string()
                    
                    # Draw cursors for network clients.
                    if ((client_name != 'local') and env.clients[client_name].active):
                        env.clients[client_name].draw_fancy_server_cursor()
                    
                pygame.display.flip()
                dt_render_s = 0
            
            # Limit the rendering framerate to be below that of the physics calculations.
            dt_render_s += dt_physics_s
            
            # Keep track of time for deleting old bullets.
            env.time_s += dt_physics_s
            
            # Jello madness game timer
            if air_table.tangled:
                env.game_time_s += dt_physics_s
            

#============================================================
# Run the main program.    
#============================================================
        
main()