#!/usr/bin/env python

# GIMP Python plug-in template.

from gimpfu import *
import sys

DEBUG=True

if DEBUG:
	sys.stderr = open('C:/temp/python-fu-output.txt','a')
	sys.stdout=sys.stderr # So that they both go to the same file

def dump(elem):
	for method_name in dir(elem):
		if callable(getattr(elem, method_name)):
			print(method_name)
		else:
			print(method_name+": "+str(getattr(elem, method_name)))
			
def perform_on_sublayers(image, xpos, ypos, width, height, xdelta, ydelta, selectedLayer):
	for curLayer in selectedLayer.children:
		if isinstance(curLayer, gimp.GroupLayer) :
			perform_every_layer(image, xpos, ypos, width, height, curLayer)
		else:
			#Apply to each layer
			origVis=pdb.gimp_layer_get_visible(curLayer)
			
			#Set each layer as active
			pdb.gimp_image_set_active_layer(image, curLayer)
			# Show preview Selection
			# CHANNEL_OP_ADD = 0
			# CHANNEL_OP_SUBTRACT = 1
			# CHANNEL_OP_REPLACE = 2
			# CHANNEL_OP_INTERSECT = 3 
			pdb.gimp_image_select_rectangle(image, 2, xpos, ypos, width, height)
			
			#Preform Cut
			pdb.gimp_edit_cut(curLayer)
			floatLayer=pdb.gimp_edit_paste(curLayer, True)
			
			#Preform Move
			#transform_2d(source_x, source_y, scale_x, scale_y, angle, dest_x, dest_y, transform_direction, interpolation)
			floatLayer=floatLayer.transform_2d(xpos, ypos, 1, 1, 0, xpos+xdelta, ypos+ydelta, 0, 0)
			
			#Preform Anchor
			pdb.gimp_floating_sel_anchor(floatLayer)
			
			#Restore Visibility
			pdb.gimp_layer_set_visible(curLayer,origVis)

def move_selection_over_layers(image, xpos, ypos, width, height, xdelta, ydelta, selectedLayer) :
	#print("Doing stuff to " + str(selectedLayer) + "...")
	#dump(selectedLayer)
	
	#Copy current active layer
	origActiveLayer=pdb.gimp_image_get_active_layer(image)
	
	selectionChan = pdb.gimp_selection_save(image)
	
	#dump(selectionChan)
	
	pdb.gimp_selection_none(image)
	
	pdb.gimp_image_select_item(image, 2, selectionChan)
	
	#perform_on_sublayers(image, xpos, ypos, width, height, xdelta, ydelta, origActiveLayer)
	
	
	#Restor active layer
	pdb.gimp_image_set_active_layer(image, origActiveLayer)

register(
    "python_fu_select_move_layers",
    "Move Selection over all sub Layers",
    "Move Selection over all sub Layers",
    "Brian Atwell",
    "Brian Atwell",
    "2020",
    "Move selection layers",
    "",      # Alternately use RGB, RGB*, GRAY*, INDEXED etc.
    [
		(PF_IMAGE, 'image', 'Input image', None),
        (PF_INT, "xpos", "X Position", 0),
		(PF_INT, "ypos", "Y Position", 0),
		(PF_INT, "width", "Width", 100),
		(PF_INT, "height", "Height", 100),
		(PF_INT, "xdelta", "X Delta", 100),
		(PF_INT, "ydelta", "y Delta", 100),
		(PF_LAYER, "selectedLayer", "Input layer", None),
    ],
    [],
    move_selection_over_layers, menu="<Image>/Filters/Languages/Python-Fu")

main()
