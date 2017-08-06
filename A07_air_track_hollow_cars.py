# Filename: A07_air_track_hollow_cars.py
# Author: James D. Miller; Gustavus Adolphus College.

# Python
import sys, os
import pygame
import datetime

# PyGame Constants
from pygame.locals import *
from pygame.color import THECOLORS

# gui from Phil's PyGame Utilities
from pgu import gui

#=====================================================================
# Classes
#=====================================================================

class TrackGuiControls( gui.Table):
    def __init__(self, **params):
        gui.Table.__init__(self, **params)

        text_color = THECOLORS["yellow"]  #(0, 0, 255)
        
        # Make a table row in the gui (like a row in HTML).
        self.tr()
        
        # Color transfer.
        self.td( gui.Label(" Color Transfer (c): ", color=text_color), align=1)
        self.td( gui.Switch(value=False, name='colorTransfer'))
        
        # Stickiness.
        self.td( gui.Label("     Fix stickiness (s): ", color=text_color), align=1)
        self.td( gui.Switch(value=True, name='fix_Stickiness'))
        
        # Gravity.
        self.td( gui.Label("     Gravity (g): ", color=text_color))
        self.td( gui.HSlider(0,-3,3, size=20, width=100, height=16, name='gravity_factor'))
        
        # Freeze the cars.
        self.td( gui.Label("     Freeze (f): ", color=text_color))
        # Form element (freeze_button).
        freeze_button = gui.Button("v=0")
        # Note: must invoke the method to be called WITHOUT parentheses.
        freeze_button.connect( gui.CLICK, self.stop_cars)
        self.td( freeze_button)
        
        # Just a help tip for starting a new demo.
        self.td( gui.Label("       New demo (0-9)", color=THECOLORS["green"]))
    
    # The method that's called by the button must be defined here in this class.
    def stop_cars(self):
        air_track.stop_the_cars()
    
    # Set air_track attributes based on the values returned from the gui.
    def queryIt(self):
        # Color transfer.
        air_track.color_transfer = gui_form['colorTransfer'].value
        
        # Stickiness
        air_track.fix_wall_stickiness = gui_form['fix_Stickiness'].value
        air_track.fix_car_stickiness = air_track.fix_wall_stickiness            
        
        # Gravity: modify the base value by the form scaling factor.
        air_track.g_mps2 = air_track.gbase_mps2 * (gui_form['gravity_factor'].value/2.0)
        
        
class Client:
    def __init__(self, cursorString_color):
        self.cursor_location_px = (0,0)   # x_px, y_px
        self.mouse_button = 1             # 1, 2, or 3
        self.buttonIsStillDown = False        
        
        self.cursorString_color = cursorString_color
        
        self.selected_car = None
        
        # Define the nature of the cursor strings, one for each mouse button.
        self.mouse_strings = {'string1':{'c_drag':   2.0, 'k_Npm':   60.0},
                              'string2':{'c_drag':   0.2, 'k_Npm':    2.0},
                              'string3':{'c_drag':  20.0, 'k_Npm': 1000.0}}
                                        
    def calc_tether_forces_on_cars(self):
        # Calculated the string forces on the selected car and add to the aggregate
        # that is stored in the car object.
        
        # Only check for a selected car if one isn't already selected. This keeps
        # the car from unselecting if cursor is dragged off the car!
        if (self.selected_car == None):
            if self.buttonIsStillDown:
                self.selected_car = air_track.checkForCarAtThisPosition(self.cursor_location_px)        
        
        # If a car is selected
        else:
            if not self.buttonIsStillDown:
                # Unselect the car and bomb out of here.
                self.selected_car.selected = False
                self.selected_car = None
                return None
            
            # If button is down, calculate the forces on the car.
            else:
                # Use dx difference to calculate the hooks law force being applied by the tether line. 
                # If you release the mouse button after a drag it will fling the car.
                # This tether force will diminish as the car gets closer to the mouse point.
                dx_m = env.m_from_px( self.cursor_location_px[0]) - self.selected_car.center_m
                
                stringName = "string" + str(self.mouse_button)
                self.selected_car.cursorString_spring_force_N  += dx_m * self.mouse_strings[stringName]['k_Npm']
                self.selected_car.cursorString_carDrag_force_N += (self.selected_car.v_mps * 
                                                                   (-1) * self.mouse_strings[stringName]['c_drag'])
            
    def draw_cursor_string(self):
        car_center_xy_px = (env.px_from_m(self.selected_car.center_m), self.selected_car.center_y_px)        
        pygame.draw.line(game_window.surface, self.cursorString_color, car_center_xy_px, self.cursor_location_px, 1)

            
class GameWindow:
    def __init__(self, screen_tuple_px):
        self.width_px = screen_tuple_px[0]
        self.height_px = screen_tuple_px[1]

        # Create a reference to display's surface object. This object is a pygame "surface".
        # Screen dimensions in pixels (tuple)
        self.surface = pygame.display.set_mode(screen_tuple_px)
        
        # Define the physics-world boundaries of the window.
        self.left_m = 0.0
        self.right_m = env.m_from_px(self.width_px)
        
        # Paint screen black.
        self.erase_and_update()
        
    def update_caption(self, title):
        pygame.display.set_caption(title)
        self.caption = title
        
    def erase_and_update(self):
        # Useful for shifting between the various demos.
        self.surface.fill(THECOLORS["black"])
        pygame.display.flip()
        

class Detroit:
    def __init__(self, color=THECOLORS["white"], left_px=10, width_px=26, height_px=98, hollow=True, m_kg=None, v_mps=1):
        
        self.color = color
        self.hollow = hollow
        
        self.height_px = height_px        
        self.top_px    = game_window.height_px - self.height_px
        self.width_px  = width_px
        
        # Use y midpoint for drawing the cursor line.
        self.center_y_px = int(round( float(game_window.height_px - self.height_px) + float(self.height_px)/2.0) )
        # For use with cursor-tethers selection.
        self.selected = False
        
        self.width_m = env.m_from_px(width_px)
        self.halfwidth_m = self.width_m/2.0
        
        self.height_m = env.m_from_px(width_px)
        
        # Initialize the position and velocity of the car. These are affected by the
        # physics calcs in the Track.
        self.center_m = env.m_from_px(left_px) + self.halfwidth_m
        self.v_mps = v_mps
        
        # Aggregate type forces acting on car.
        self.cursorString_spring_force_N = 0
        self.cursorString_carDrag_force_N = 0

        # Calculate the mass of the car.
        if self.hollow:
            self.m_kg = m_kg
        else:
            self.density_kgpm2 = 600.0
            self.m_kg = self.height_m * self.width_m * self.density_kgpm2
        
        # Increment the car count. The air_track object has global scope.
        air_track.carCount += 1
        # Name this car based on this air_track attribute.
        self.name = air_track.carCount
        
        # Update the list of masses and recalculate the maximum.
        air_track.mass_list.append(self.m_kg)
        air_track.max_m_kg = max(air_track.mass_list)
        
        # Create a rectangle object based on these dimensions
        # Left: distance from the left edge of the screen in px.
        # Top:  distance from the top  edge of the screen in px.
        self.rect = pygame.Rect(left_px, self.top_px, self.width_px, self.height_px)
        
        # Calculate the hole characteristics (shrink values).
        if self.hollow:
            if (self.m_kg == air_track.max_m_kg):
                # If you're the top dog (heaviest), everyone else will have to re-calculate their shrink
                # values accordingly.
                    for eachcar in air_track.cars:
                        eachcar.calc_hole_shrink()
            else:
                # Oh well, not the top dog. Then I'm the only one that needs to calculate
                # shrink values.
                self.calc_hole_shrink()
    
    def calc_hole_shrink(self):
        # Calculate a special density in kg per pixel area. Use this only for the 
        # hole calculation. Notice the reference to the air_track's max_m_kg which is
        # the mass of the heaviest car.
        
        self.density_kgppx2 = float(air_track.max_m_kg)/float(self.width_px * self.height_px)
        
        # Keep the hole width consistent for all the cars.
        hole_width_pxi = self.width_px - 2
        
        # Calculate the hole height based on the difference in mass it represents.
        hole_height_pxf = (air_track.max_m_kg - self.m_kg)/(self.density_kgppx2 * hole_width_pxi)
        hole_height_pxi = int(round(hole_height_pxf))
        
        # These shrink values will be used (relative to the main car rectangle) when time comes 
        # to draw the rectangle that represents the hole.
        self.shrink_x_px = self.width_px - hole_width_pxi
        self.shrink_y_px = self.height_px - hole_height_pxi
    
    def draw_car(self):
        # Update the pixel position of the car's rectangle object to match the value
        # controlled by the physics calculations.
        self.rect.centerx = env.px_from_m( self.center_m)
        
        # Draw the main rectangle.
        pygame.draw.rect(game_window.surface, self.color, self.rect)
        
        if self.hollow and (self.m_kg <> air_track.max_m_kg):
        
            # Draw a subrectangle (a hole) to illustrate the mass of this car relative
            # to the mass of the most massive car. The closer we are to the most massive car
            # the more shrinking of the hole. So heavier cars look more
            # solid.
            
            # Make a hole by shrinking the main rectangle.
            hole_rect = self.rect.inflate(-self.shrink_x_px, -self.shrink_y_px)  # x,y
            
            # Draw the hole.
            pygame.draw.rect(game_window.surface, THECOLORS["black"], hole_rect)        

        
class AirTrack:
    def __init__(self):
        self.clean()    
        self.gui_menu = True
        
    def clean(self):
        # Initialize the list of cars.
        self.cars = []
        self.carCount = 0
        self.mass_list = []
        self.max_m_kg = 0
        
        # Coefficients of restitution.
        self.coef_rest_base = 0.90  # Useful for reseting things.
        self.coef_rest_car = self.coef_rest_base
        self.coef_rest_wall = self.coef_rest_base
        
        # Component of gravity along the length of the track.
        self.g_toggle = False
        self.gbase_mps2 = 9.8/40.0 # one 40th of g.
        
        self.color_transfer = False
        
        self.collision_count = 0
        
        self.fix_wall_stickiness = True
        self.fix_car_stickiness = True
    
    def checkForCarAtThisPosition(self, cursor_location_xy):
        x_px = cursor_location_xy[0]
        y_px = cursor_location_xy[1]
        x_m = env.m_from_px(x_px)
        for car in self.cars:
            if (((x_m > car.center_m - car.halfwidth_m) and (x_m < car.center_m + car.halfwidth_m)) and
                    (y_px > game_window.height_px - car.height_px)):
                car.selected = True
                return car
        return None
    
    def update_SpeedandPosition(self, car, dt_s):
        # Add up all the forces on the car.
        car_forces_N = (car.m_kg * self.g_mps2) + (car.cursorString_spring_force_N + 
                                                   car.cursorString_carDrag_force_N )
        
        # Calculate the acceleration based on the forces and Newton's law.
        car_acc_mps2 = car_forces_N / car.m_kg
        
        # Calculate the velocity at the end of this time step.
        v_end_mps = car.v_mps + (car_acc_mps2 * dt_s)
        
        # Calculate the average velocity during this timestep.
        v_avg_mps = (car.v_mps + v_end_mps)/2.0
        
        # Use the average velocity to calculate the new position of the car.
        # Physics note: v_avg*t is equivalent to (v*t + (1/2)*acc*t^2)
        car.center_m = car.center_m + (v_avg_mps * dt_s)
        
        # Assign the final velocity to the car.
        car.v_mps = v_end_mps
        
        # Reset the aggregate forces.
        car.cursorString_spring_force_N = 0
        car.cursorString_carDrag_force_N = 0
        
    def check_for_collisions(self):
        # Collisions with walls.
        # Enumerate so can efficiently check car-car collisions below.
        
        for i, car in enumerate(self.cars):
            
            # Collisions with Left and Right wall.
            #   If left-edge of the car is less than...                OR  If right-edge of car is greater than...
            if ((car.center_m - car.width_m/2.0) < game_window.left_m) or ((car.center_m + car.width_m/2.0) > game_window.right_m):
                self.collision_count += 1
                
                if self.fix_wall_stickiness:
                    self.correct_wall_penetrations(car)
            
                car.v_mps = -car.v_mps * self.coef_rest_wall                
            
            # This makes use of the "enumerate"d for loop above. 
            # In doing so, it avoids checking the self-self case and avoids checking pairs twice
            # like (2 with 3) and (3 with 2).
            # Example checks: (1 with 2,3,4,5), (2 with 3,4,5), (3 with 4,5), (4 with 5) etc...
            for ocar in self.cars[i+1:]:
                # Check for overlap with other rectangle.
                if (abs(car.center_m - ocar.center_m) < (car.halfwidth_m + ocar.halfwidth_m)):
                    self.collision_count += 1

                    if self.color_transfer:
                        (car.color, ocar.color) = (ocar.color, car.color)
                    
                    # Prevent sticking to other cars.
                    if self.fix_car_stickiness:
                        self.correct_car_penetrations(car, ocar)
                    
                    # Calculate the new post-collision velocities.
                    (car.v_mps, ocar.v_mps) = self.car_and_ocar_vel_AFTER_collision( car, ocar)

    def car_and_ocar_vel_AFTER_collision(self, car, ocar, CR=None):
        # If no override CR is provided, use the car's value.
        if (CR == None):
            CR = self.coef_rest_car
            
        # Calculate the AFTER velocities.
        car_vel_AFTER_mps =  ( (CR * ocar.m_kg * (ocar.v_mps - car.v_mps) + car.m_kg*car.v_mps + ocar.m_kg*ocar.v_mps)/
                               (car.m_kg + ocar.m_kg) )
        ocar_vel_AFTER_mps = ( (CR * car.m_kg *  (car.v_mps - ocar.v_mps) + car.m_kg*car.v_mps + ocar.m_kg*ocar.v_mps)/
                               (car.m_kg + ocar.m_kg) )

        return (car_vel_AFTER_mps, ocar_vel_AFTER_mps)
        
    def correct_wall_penetrations(self, car):
        penetration_left_x_m = game_window.left_m - (car.center_m - car.halfwidth_m)
        if penetration_left_x_m > 0:
            car.center_m += 2 * penetration_left_x_m
        
        penetration_right_x_m = (car.center_m + car.halfwidth_m) - game_window.right_m
        if penetration_right_x_m > 0:
            car.center_m -= 2 * penetration_right_x_m
    
    def correct_car_penetrations(self, car, ocar):
        relative_spd_mps = abs(car.v_mps - ocar.v_mps)
        penetration_m = (car.halfwidth_m + ocar.halfwidth_m) - abs(car.center_m - ocar.center_m)
        
        if (relative_spd_mps > 0.0):
            penetration_time_s = penetration_m / relative_spd_mps
            
            # First, back up the two cars, to their collision point, along their incoming trajectory paths.
            # Use BEFORE collision velocities here!
            car.center_m  -= car.v_mps  * penetration_time_s
            ocar.center_m -= ocar.v_mps * penetration_time_s
            
            # Calculate the velocities along the normal AFTER the collision. Use a CR (coefficient of restituion)
            # of 1 here to better avoid stickiness.
            (car_vel_AFTER_mps, ocar_vel_AFTER_mps) = self.car_and_ocar_vel_AFTER_collision( car, ocar, CR=1.0)

            # Finally, travel another penetration time worth of distance using these AFTER-collision velocities.
            # This will put the cars where they should have been at the time of collision detection.
            car.center_m  += car_vel_AFTER_mps  * penetration_time_s
            ocar.center_m += ocar_vel_AFTER_mps * penetration_time_s
        else:
            pass
    
    def stop_the_cars(self):
        for car in self.cars:
            car.v_mps = 0
    
    def make_some_cars(self, nmode):
        # Update the caption at the top of the pygame window frame.
        game_window.update_caption("Air Track (hollow cars): Demo #" + str(nmode)) 
        
        # Scrub off the old cars and reset some stuff.
        air_track.clean()
        
        if nmode == '1p':
            gui_form['gravity_factor'].value = 0.0
            gui_form['colorTransfer'].value = False
            
            self.cars.append( Detroit(color=THECOLORS["yellow" ], left_px = 240, width_px=20, hollow=False, v_mps=  0.0))
            self.cars.append( Detroit(color=THECOLORS["orange"],  left_px = 340, width_px=30, hollow=False, v_mps= -0.0))
        
        elif nmode == '2p':
            gui_form['gravity_factor'].value = 2.0
            gui_form['colorTransfer'].value = False
            
            self.cars.append( Detroit(color=THECOLORS["yellow" ], left_px = 240, width_px=20, hollow=False, v_mps= -0.1))
            self.cars.append( Detroit(color=THECOLORS["orange"],  left_px = 440, width_px=60, hollow=False, v_mps= -0.2))
        
        elif nmode == '3p':
            gui_form['gravity_factor'].value = -1.0
            gui_form['colorTransfer'].value = True
            
            self.cars.append( Detroit(color=THECOLORS["yellow" ], left_px = 240, width_px=20, hollow=False, v_mps= -0.1))
            self.cars.append( Detroit(color=THECOLORS["orange"],  left_px = 440, width_px=80, hollow=False, v_mps= -0.2))
            
        elif nmode == 0:
            gui_form['gravity_factor'].value = 0
            gui_form['colorTransfer'].value = False
            
            self.coef_rest_car  = 1.00
            self.coef_rest_wall = 1.00    
            x_steps = Next_x( 100, 29)
            cars_v_mps = 0.0 #.15 #m/s
            cars_m_kg =  0.3 #kg
            color_list = ["yellow","red","green","blue","pink"]
            k_color = 0
            for j in range(9):
                if (k_color > (len(color_list) - 1)):
                    k_color = 0
                else:
                    k_color += 0
                self.cars.append( Detroit(color=THECOLORS[color_list[k_color]], left_px=x_steps.step(), 
                                  v_mps=cars_v_mps, m_kg=cars_m_kg))
                    
            cars_v_mps = -0.3 #.15 #m/s
            x_steps = Next_x( 750, 45)
            k_color = 0
            for j in range(3):
                if (k_color > (len(color_list) - 1)):
                    k_color = 2
                else:
                    k_color += 1
                self.cars.append( Detroit(color=THECOLORS[color_list[k_color]], left_px=x_steps.step(), 
                                  v_mps=cars_v_mps, m_kg=cars_m_kg))        
        
        elif nmode == 1:
            gui_form['gravity_factor'].value = 2
            gui_form['colorTransfer'].value = True
            
            self.coef_rest_car  = 0.95
            self.coef_rest_wall = 0.95    
            
            color_list = ["yellow","red","green","blue","pink"]
            x_steps = Next_x( 050, 30)
            cars_v_mps = 0.0 #.15 #m/s
            cars_m_kg =  0.3 #kg
            k_color = 0
            for j in range(4):
                if (k_color > (len(color_list) - 1)):
                    k_color = 0
                self.cars.append( Detroit(color=THECOLORS[color_list[k_color]], left_px=x_steps.step(), 
                                  v_mps=cars_v_mps, m_kg=cars_m_kg))
                k_color += 0
            k_color += 1
            self.cars.append( Detroit(color=THECOLORS[color_list[k_color]], left_px=x_steps.step(), 
                              v_mps=cars_v_mps, m_kg=cars_m_kg))
            
        elif nmode == 2:
            gui_form['gravity_factor'].value = 3
            gui_form['colorTransfer'].value = False
            
            x_steps = Next_x( 450, 30)
            cars_v_mps = 0.0 #.15 #m/s
            cars_m_kg =  0.3 #kg
            
            self.cars.append( Detroit(color=THECOLORS["white"], left_px=x_steps.step(), v_mps=cars_v_mps, m_kg=cars_m_kg*6))
            self.cars.append( Detroit(color=THECOLORS["white"], left_px=x_steps.step(), v_mps=cars_v_mps, m_kg=cars_m_kg*8))    
        
        elif nmode == 3:
            gui_form['gravity_factor'].value = 3
            gui_form['colorTransfer'].value = False
            
            x_steps = Next_x( 450, 30)
            cars_v_mps = 0.0 #.15 #m/s
            cars_m_kg =  0.3 #kg
            
            self.cars.append( Detroit(color=THECOLORS["white"], left_px=x_steps.step(), v_mps=cars_v_mps, m_kg=cars_m_kg*1))
            self.cars.append( Detroit(color=THECOLORS["white"], left_px=x_steps.step(), v_mps=cars_v_mps, m_kg=cars_m_kg*8))    
        
        elif nmode == 4:
            gui_form['colorTransfer'].value = False
            
            self.coef_rest_car  = 0.0
            self.coef_rest_wall = 1.0
            
            gui_form['gravity_factor'].value = 0
            
            cars_v_mps = 0.1 #.15 #m/s
            cars_m_kg =  0.3 #kg
            
            self.cars.append( Detroit(color=THECOLORS["white"], left_px= 30, v_mps=+7.0*cars_v_mps, m_kg=2*cars_m_kg))
            self.cars.append( Detroit(color=THECOLORS["white"], left_px=500, v_mps=+2.0*cars_v_mps, m_kg=1*cars_m_kg))  
            self.cars.append( Detroit(color=THECOLORS["white"], left_px=600, v_mps=-2.0*cars_v_mps, m_kg=2*cars_m_kg))  
            self.cars.append( Detroit(color=THECOLORS["white"], left_px=700, v_mps=-1.0*cars_v_mps, m_kg=1*cars_m_kg))  
            self.cars.append( Detroit(color=THECOLORS["white"], left_px=900, v_mps=-5.5*cars_v_mps, m_kg=2*cars_m_kg))  
            
        elif nmode == 5:
            self.coef_rest_car  = 1
            self.coef_rest_wall = 1          
            
            gui_form['gravity_factor'].value = 0
            gui_form['colorTransfer'].value = True
            
            x_steps = Next_x(450, 35)
            cars_v_mps = 0.0 #.15 #m/s
            cars_m_kg =  0.3 #kg
            
            for j in range(10):
                self.cars.append( Detroit(color=THECOLORS["yellow"], 
                                             left_px=x_steps.step(),  
                                             v_mps=cars_v_mps, 
                                             m_kg=cars_m_kg))
            self.cars.append( Detroit(color=THECOLORS["red"], left_px=x_steps.step(), v_mps=0.5, m_kg=cars_m_kg)) 
        
        elif nmode == 6:
            self.coef_rest_car  = 1
            self.coef_rest_wall = 1          
            
            gui_form['gravity_factor'].value = -1
            gui_form['colorTransfer'].value = True
            
            x_steps = Next_x(450, 35)
            cars_v_mps = 0.1
            cars_m_kg =  0.3 #kg
            
            for j in range(10):
                self.cars.append( Detroit(color=THECOLORS["yellow"], 
                                             left_px=x_steps.step(),  
                                             v_mps=cars_v_mps, 
                                             m_kg=cars_m_kg))
            self.cars.append( Detroit(color=THECOLORS["red"], left_px=x_steps.step(), v_mps=0.5, m_kg=cars_m_kg)) 
        
        elif nmode == 7:
            self.coef_rest_car  = 1 #0.99
            self.coef_rest_wall = 1 #0.99          
            
            gui_form['gravity_factor'].value = 0
            
            gui_form['colorTransfer'].value = True
            
            x_steps = Next_x(450, 35)
            cars_v_mps = 0.0 #.15 #m/s
            cars_m_kg =  0.3 #kg
            
            for j in range(10):
                cars_m_kg += .1
                self.cars.append( Detroit(color=THECOLORS["yellow"], 
                                             left_px=x_steps.step(),  
                                             v_mps=cars_v_mps, 
                                             m_kg=cars_m_kg))
            cars_m_kg += .1
            self.cars.append( Detroit(color=THECOLORS["red"], left_px=x_steps.step(), v_mps=0.5, m_kg=cars_m_kg)) 
            
        elif nmode == 8:
            gui_form['colorTransfer'].value = False
            
            self.coef_rest_car  = 1.000
            self.coef_rest_wall = 1.000 
            
            gui_form['gravity_factor'].value = 0

            cars_v_mps = 0.0 #.15 #m/s
            cars_m_kg =  0.3 #kg
            
            # This does interesting COMPLETE energy transfers between the cars when the first car is
            # 3,4,5,6... times the mass of the other car, and the lighter car is initially stationary.
            # If the heavy car is initially stationary, then only 3x works.
            self.cars.append( Detroit(color=THECOLORS["yellow"], left_px=200, v_mps=0, m_kg=3*cars_m_kg))
            self.cars.append( Detroit(color=THECOLORS["red"],    left_px=500, v_mps=1, m_kg=1*cars_m_kg))  
            
        elif nmode == 9:
            #self.gui_menu = True #False
            gui_form['gravity_factor'].value = 0
            gui_form['colorTransfer'].value = True
            
            self.coef_rest_car  = 1.00
            self.coef_rest_wall = 1.00    
            
            cars_v_mps = 0.0 #.15 #m/s
            cars_m_kg =  0.3 #kg
            color_list = ["yellow","red","green","blue","pink","grey"]

            self.cars.append( Detroit(color=THECOLORS[color_list[1]], left_px= 20, v_mps= 0.05, m_kg=cars_m_kg))        
            x_steps = Next_x( 50, 29)
            for j in range(12):
                self.cars.append( Detroit(color=THECOLORS[color_list[0]], left_px=x_steps.step(), v_mps=cars_v_mps, m_kg=cars_m_kg))
            self.cars.append( Detroit(color=THECOLORS[color_list[2]], left_px= 430, v_mps=-0.05, m_kg=cars_m_kg))        
                
            self.cars.append( Detroit(color=THECOLORS[color_list[3]], left_px= 460, v_mps= 0.20, m_kg=cars_m_kg))        
            x_steps = Next_x( 500, 29)
            for j in range(12):
                self.cars.append( Detroit(color=THECOLORS[color_list[0]], left_px=x_steps.step(), v_mps=cars_v_mps, m_kg=cars_m_kg))
            self.cars.append( Detroit(color=THECOLORS[color_list[5]], left_px=890, v_mps=-0.05, m_kg=cars_m_kg))        
            
        else:
            print "nothing set up for this key"
            
            
class Next_x:
    # Initialize the positions of the cars.
    def __init__(self, x_start, x_increment):
        self.x = x_start
        self.dx = x_increment
    def step(self):
        self.x += self.dx
        return self.x
        

class Environment:
    def __init__(self, length_px, length_m):
        self.px_to_m = length_m/float(length_px)
        self.m_to_px = (float(length_px)/length_m)
        
        # Add a local (non-network) client to the client dictionary.
        self.clients = {'local':Client(THECOLORS["green"])}
        self.gui_controls = None
    
    # Convert from meters to pixels
    def px_from_m(self, dx_m):
        return int(round(dx_m * self.m_to_px))
    
    # Convert from pixels to meters
    def m_from_px(self, dx_px):
        return float(dx_px) * self.px_to_m
        
    def get_local_user_input(self):
        # Get all the events since the last call to get().
        for event in pygame.event.get():
            if (event.type == pygame.QUIT): 
                return 'quit'
            elif (event.type == pygame.KEYDOWN):
                if (event.key == K_ESCAPE):
                    return 'quit'
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
                
                elif (event.key==K_s):
                    gui_form['fix_Stickiness'].value = not gui_form['fix_Stickiness'].value
                
                elif (event.key==K_c):
                    gui_form['colorTransfer'].value = not gui_form['colorTransfer'].value
                
                elif (event.key==K_f):
                    air_track.stop_the_cars()
                    
                elif (event.key==K_g):
                    air_track.g_toggle = not air_track.g_toggle
                    if air_track.g_toggle:
                        gui_form['gravity_factor'].value = -2
                    else:
                        gui_form['gravity_factor'].value = 0
                
                elif (event.key==K_F2):
                    # Turn the gui menu on/off
                    air_track.gui_menu = not air_track.gui_menu
                
                else:
                    return "Nothing set up for this key."
            
            elif (event.type == pygame.KEYUP):
                pass
            
            elif (event.type == pygame.MOUSEBUTTONDOWN):
                self.clients['local'].buttonIsStillDown = True
            
                (button1, button2, button3) = pygame.mouse.get_pressed()
                if button1:
                    self.clients['local'].mouse_button = 1
                elif button2:
                    self.clients['local'].mouse_button = 2
                elif button3:
                    self.clients['local'].mouse_button = 3
                else:
                    self.clients['local'].mouse_button = 0
            
            elif event.type == pygame.MOUSEBUTTONUP:
                self.clients['local'].buttonIsStillDown = False
                self.clients['local'].mouse_button = 0
            
            # In all cases, pass the "event" to the Gui application.
            gui_application.event( event)
            
        if self.clients['local'].buttonIsStillDown:
            # If it is down, get the cursor position.
            self.clients['local'].cursor_location_px = (mouseX, mouseY) = pygame.mouse.get_pos()
                
        
#============================================================
# Main procedural functions.
#============================================================

def main():

    # A few globals.
    global env, game_window, air_track, gui_form, gui_application
    
    # Initiate pygame
    pygame.init()

    # Tuple to define window dimensions
    window_size_px = window_width_px, window_height_px = 950, 120

    # Instantiate an Environment object for converting back and forth from pixels and meters.
    # The also creates the local client.
    env = Environment(window_width_px, 1.5)

    # Instantiate the window.
    game_window = GameWindow(window_size_px)
    
    # Initialize gui...
    gui_form = gui.Form()
    env.gui_controls = TrackGuiControls()
    
    gui_container = gui.Container(align=-1, valign=-1)
    gui_container.add(env.gui_controls, 0, 0)
    
    gui_application = gui.App()
    gui_application.init( gui_container)

    # Instantiate an air track (this adds an empty car list to the track).
    air_track = AirTrack()

    # Make some cars (run demo #1).
    air_track.make_some_cars(1)

    # Instantiate clock to help control the framerate.
    myclock = pygame.time.Clock()
        
    # Control the framerate.
    framerate_limit = 400

    time_s = 0.0
    user_done = False
    
    while not user_done:
    
        # Erase everything.
        game_window.surface.fill(THECOLORS["black"])

        # Get the delta t for one frame (this changes depending on system load).
        dt_s = float(myclock.tick(framerate_limit) * 1e-3)

        # This check avoids problem when dragging the game window.
        if (dt_s < 0.10):
        
            # Check for user initiated stop or demo change.
            resetmode = env.get_local_user_input()
            
            if (resetmode in ["1p","2p","3p",1,2,3,4,5,6,7,8,9,0]):
                print "demo mode =", resetmode
                
                # This should remove all references to the cars and effectively deletes them.
                #air_track.cars = []
                
                # Now just black everything out and update the screen.
                game_window.erase_and_update()
                
                # Build new set of cars based on the reset mode.
                air_track.make_some_cars( resetmode)
            
            elif (resetmode == 'quit'):
                user_done = True
                
            elif (resetmode != None):
                print resetmode
            
            # Set object attributes based on the values returned from a query of the Gui.
            # Important to do this AFTER all initialization and car building is over, AFTER
            # any user input from the pygame event queue, and BEFORE the updates to the speed
            # and position.
            env.gui_controls.queryIt()
            
            # Calculate client related forces.
            for client_name in env.clients:
                env.clients[client_name].calc_tether_forces_on_cars()
            
            # Update velocity and x position of each car based on the dt_s for this frame.
            for car in air_track.cars:
                air_track.update_SpeedandPosition(car, dt_s)
            
            # Check for collisions and apply collision physics to determine resulting
            # velocities.
            air_track.check_for_collisions()
            
            # Draw the car at the new position.
            for car in air_track.cars:
                car.draw_car()
                
            # Draw cursor strings.
            for client_name in env.clients:
                if (env.clients[client_name].selected_car != None):
                    env.clients[client_name].draw_cursor_string()
                        
            # Update the total time since starting.
            time_s += dt_s
            
            # Paint the gui. (F2 toggles gui on/off)
            if air_track.gui_menu:
                gui_application.paint()
                    
            # Make this update visible on the screen.
            pygame.display.flip()
            
#============================================================
# Run the main program.    
#============================================================

main()