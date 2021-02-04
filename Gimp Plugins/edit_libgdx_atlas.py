#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# python Edit Libgdx atlas with selection rect tool
# version-1.0 12/21/2020
# Copyright (c) 2021
# Based on High Pass Sharpen (high-end-sharpend.py) by Paul Sherman 2008
# Used python 2.7.18
#
# Impliments a preview/undo on active image using a layer
# --------------------------------------------------------------------
# for use on Linux - 
# make sure the installed script is set to EXECUTABLE
# usual location is /usr/lib/gimp/2.0/plug-ins
# restart gimp
# --------------------------------------------------------------------
# for Windows
# (User) Copy to %APPDATA%\Roaming\GIMP\2.10\plug-ins 
# Or
# (System) Copy to %PROGRAMFILES%\GIMP 2\lib\gimp\2.0\plug-ins
#
# --------------------------------------------------------------------
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ---------------------------------------------------------------------

from gimpfu import *
import gimp, gimpplugin, math
from gimpenums import *
pdb = gimp.pdb
import gtk, gimpui, gimpcolor
from gimpshelf import shelf
import sys
from threading import Thread
import gobject, glib

INDENTATIONSTR = "  "

DEBUG=True

if DEBUG:
	sys.stderr = open('C:/temp/edit_libgdx_atlas_debug.xt','a')
	sys.stdout=sys.stderr # So that they both go to the same file

def error_box(text):
	currenth = pdb.gimp_message_get_handler()
	pdb.gimp_message_set_handler(2) # box
	gimp.message ("ERROR: "+text)
	print("ERROR: "+text)
	pdb.gimp_message_set_handler(currenth) # current
	
def warning_box(text):
	currenth = pdb.gimp_message_get_handler()
	pdb.gimp_message_set_handler(2) # box
	gimp.message ("Warning: "+text)
	print("Warning: "+text)
	pdb.gimp_message_set_handler(currenth) # current
	
def warning_normal(text):
	currenth = pdb.gimp_message_get_handler()
	pdb.gimp_message_set_handler(0) # box
	gimp.message ("Warning: "+text)
	print("Warning: "+text)
	pdb.gimp_message_set_handler(currenth) # current
	
def testProcess(layer):
	time.sleep(1)
	
class FileDialogManager(object):

	def __init__(self):
		self.fileName=None
		
	def openFile(self):
		localFileName=None
		dialog = gtk.FileChooserDialog(
			title="Please choose a file", parent=self, action=gtk.FileChooserAction.OPEN
		)
		dialog.add_buttons(
			gtk.STOCK_CANCEL,
			gtk.ResponseType.CANCEL,
			gtk.STOCK_OPEN,
			gtk.ResponseType.OK,
		)
		
		if self.fileName is not None:
			dialog.set_filename(self.fileName)

		self.add_filters(dialog)

		response = dialog.run()
		if response == gtk.ResponseType.OK:
			self.fileName = dialog.get_filename()
			localFileName = self.fileName
		elif response == gtk.ResponseType.CANCEL:
			print("Cancel clicked")

		dialog.destroy()
		return localFileName
		
	def saveFile(self):
		localFileName=None
		dialog = gtk.FileChooserDialog(
			title="Please choose a file", parent=self, action=gtk.FileChooserAction.SAVE
		)
		dialog.add_buttons(
			gtk.STOCK_CANCEL,
			gtk.ResponseType.CANCEL,
			gtk.STOCK_OPEN,
			gtk.ResponseType.OK,
		)
		
		if self.fileName is not None:
			dialog.set_filename(self.fileName)

		self.add_filters(dialog)

		response = dialog.run()
		if response == gtk.ResponseType.OK:
			self.fileName = dialog.get_filename()
			localFileName = self.fileName
		elif response == gtk.ResponseType.CANCEL:
			print("Cancel clicked")

		dialog.destroy()
		return localFileName
		
	def add_filters(self, dialog):
		filter_text = gtk.FileFilter()
		filter_text.set_name("Text files")
		filter_any.add_pattern("*.atlas")
		dialog.add_filter(filter_text)
		
		filter_any = Gtk.FileFilter()
		filter_any.set_name("Any files")
		filter_any.add_pattern("*")
		dialog.add_filter(filter_any)
		
	
class WriterLibGDXAtlas(object):
	@staticmethod
	def writeFile(fileName, textureAtlasList):
		outStr=""
		for textureAtlas in textureAtlasList:
			outStr+=str(textureAtlas)
		file = open(fileName, "w")
		file.write(outStr)
		file.close()

class ReaderLibGDXAtlas(object):
	def __init__(self):
		self.curSubtexture=None
		self.curTextureAtlas=None
		
	def getIndentation(self, lineStr):
		count=0
		for curChar in lineStr:
			if curChar.isspace():
				count+=1
			else:
				break
		return count
		
	def getListFromLine(self, lineStr):
		result=None
		idxKey=lineStr.find(":")
		if idxKey != -1:
			result=[]
			key = lineStr[0:idxKey].strip()
			result.append(key)
			valueList = lineStr[idxKey+1:].split(",")
			for vlIdx in range(0,len(valueList)):
				valueList[vlIdx] = valueList[vlIdx].strip()
			result.extend(valueList)
		return result
		
	def textureAtlasParamToObj(self, list):
		if list[0] == "size" and len(list) == 3:
			self.curTextureAtlas.size=(list[1], list[2])
		elif list[0] == "format" and len(list) == 2:
			self.curTextureAtlas.format=list[1]
		elif list[0] == "filter" and len(list) == 3:
			self.curTextureAtlas.filter=(list[1], list[2])
		elif list[0] == "repeat" and len(list) == 2:
			self.curTextureAtlas.repeat=list[1]
	
	def subtextureParamToObj(self, list):
		if list[0] == "rotate" and len(list) == 2:
			self.curSubtexture.rotate=list[1]
		elif list[0] == "xy" and len(list) == 3:
			self.curSubtexture.xy=(list[1], list[2])
		elif list[0] == "size" and len(list) == 3:
			self.curSubtexture.size=(list[1], list[2])
		elif list[0] == "orig" and len(list) == 3:
			self.curSubtexture.orig=(list[1], list[2])
		elif list[0] == "offset" and len(list) == 3:
			self.curSubtexture.offset=(list[1], list[2])
		elif list[0] == "index" and len(list) == 2:
			self.curSubtexture.index=list[1]
	
	def readFile(self, fileName):
		textureAtlases=[]
		self.curSubtexture=None
		self.curTextureAtlas=None
		sectionName=None
		curIndentation=0
		file = open(fileName, "r")
		for line in file:
			if line and line.strip():
				indentation=self.getIndentation(line)
				locResult=self.getListFromLine(line)
				if locResult is not None:
					if indentation == 0:
						if indentation != curIndentation:
							if self.curSubtexture is not None and self.curTextureAtlas is not None:
								if self.curSubtexture.name in self.curTextureAtlas.subtextures:
									self.curTextureAtlas.subtextures[self.curSubtexture.name].append(self.curSubtexture)
								else:
									self.curTextureAtlas.subtextures[self.curSubtexture.name] = [self.curSubtexture]
								self.curSubtexture=None
							if self.curTextureAtlas is not None:
								textureAtlases.append(self.curTextureAtlas)
								self.curTextureAtlas=None
						if self.curTextureAtlas is None and sectionName:
							self.curTextureAtlas = TextureLibGDXAtlas()
							self.curTextureAtlas.fileName = sectionName
						if self.curTextureAtlas:
							self.textureAtlasParamToObj(locResult)
						curIndentation=0
							
					elif indentation > 0:
						if indentation != curIndentation:
							if self.curSubtexture is not None and self.curTextureAtlas is not None:
								if self.curSubtexture.name in self.curTextureAtlas.subtextures:
									self.curTextureAtlas.subtextures[self.curSubtexture.name].append(self.curSubtexture)
								else:
									self.curTextureAtlas.subtextures[self.curSubtexture.name] = [self.curSubtexture]
								self.curSubtexture=None
						if self.curSubtexture is None and sectionName:
							self.curSubtexture = SubtextureInfo()
							self.curSubtexture.name = sectionName
						if self.curSubtexture:
							self.subtextureParamToObj(locResult)
						curIndentation=indentation
				else:
					sectionName = line.strip()
					curIndentation=0
		if self.curSubtexture is not None and self.curTextureAtlas is not None:
			if self.curSubtexture.name in self.curTextureAtlas.subtextures:
				self.curTextureAtlas.subtextures[self.curSubtexture.name].append(self.curSubtexture)
			else:
				self.curTextureAtlas.subtextures[self.curSubtexture.name] = [self.curSubtexture]
			self.curSubtexture=None
		if self.curTextureAtlas is not None:
			textureAtlases.append(self.curTextureAtlas)
			self.curTextureAtlas=None
		file.close()
		return textureAtlases
							
								
						
	
class SubtextureInfo(object):
	def __init__(self):
		self.name=""
		self.rotate=False
		self.xy=(0,0)
		self.size=(0,0)
		self.orig=(0,0)
		self.offset=(0,0)
		self.index=0
		
	def __str__(self):
		outStr = self.name + "\n"
		outStr += INDENTATIONSTR + "rotate: " + str(self.rotate) + "\n"
		outStr += INDENTATIONSTR + "xy: " + str(self.xy[0]) + ", " + str(self.xy[1]) + "\n"
		outStr += INDENTATIONSTR + "size: " + str(self.size[0]) + ", " + str(self.size[1]) + "\n"
		outStr += INDENTATIONSTR + "orig: " + str(self.orig[0]) + ", " + str(self.orig[1]) + "\n"
		outStr += INDENTATIONSTR + "offset: " + str(self.offset[0]) + ", " + str(self.offset[1]) + "\n"
		outStr += INDENTATIONSTR + "index: " + str(self.index) + "\n"
		return outStr
	
class TextureLibGDXAtlas(object):
	def __init__(self):
		self.subtextures={}
		self.fileName=""
		self.size=(0,0)
		self.format="RGBA8888"
		self.filter="Nearest,Nearest"
		self.repeat="none"
		
	def __str__(self):
		outStr = self.fileName + "\n"
		outStr += "size: " + str(self.size[0]) + ", " + str(self.size[1]) + "\n"
		outStr += "format: " + self.format + "\n"
		outStr += "filter: " + str(self.filter[0]) + ", " + str(self.filter[1]) + "\n"
		outStr += "repeat: " + self.repeat + "\n"
		
		for key in self.subtextures:
			for subtexture in self.subtextures[key]:
				outStr += str(subtexture)
		
		return outStr

class ProgressThread(Thread):
	def __init__(self, stopFunc, processFunc, layerList, progressDialog): 
		Thread.__init__(self) 
		self.layerList=layerList
		self.stopFunc=stopFunc
		self.processFunc=processFunc
		self.progressDialog=progressDialog
		self.threadNotifyType=1
		
	def updateStartProcess(self):
		if self.threadNotifyType == 1:
			gtk.threads_enter()
			self.progressDialog.progressStarted()
			gtk.threads_leave()
		else:
			glib.idle_add(self.progressDialog.progressStarted)
		
	def updateProgressDialog(self, count, totalLen, progress, layerName):
		if self.threadNotifyType == 1:
			gtk.threads_enter()
			self.progressDialog.updateProgess(count, totalLen, progress, layerName)
			gtk.threads_leave()
		else:
			glib.idle_add(self.progressDialog.updateProgess, count, totalLen, progress, layerName)
		
	def updateFinishProgress(self):
		if self.threadNotifyType == 1:
			gtk.threads_enter()
			self.progressDialog.progressDone()
			gtk.threads_leave()
		else:
			glib.idle_add(self.progressDialog.progressDone)
	
	def run(self):
		if DEBUG:
			sys.stderr = open('C:/temp/progresstest-thread1.txt','a')
			sys.stdout=sys.stderr # So that they both go to the same file
		self.updateStartProcess()
		try:
			count=0
			totalLen=len(self.layerList)
			for curLayer in self.layerList:
				if self.stopFunc():
					break
				progress=float(count)/float(totalLen)
				print("Progress: "+str(count)+"/"+str(totalLen)+" "+str(progress))
				self.processFunc(curLayer)
				self.updateProgressDialog(count, totalLen, progress, curLayer.name)
				count+=1
			if not self.stopFunc():
				print("Progress: "+str(count)+"/"+str(totalLen)+" "+str(progress))
				self.updateProgressDialog(count, totalLen, progress, curLayer.name)
		except Exception as err:
			print("ProgressThread Exception: "+str(err))
			self.err = err
			pass # or raise err
		else:
			self.err = None
		self.updateFinishProgress()
		print("ProgressThread: End of run")
	
class edit_libgdx_atlas(object):
	
	def __init__(self, runmode, img, drawable):
		self.runmode=runmode
		self.img = img
		self.drawable = drawable
		self.shelfkey = 'layerfx-drop-shadow'
		self.fileDialog=FileDialogManager()
		self.textureAtlases=[]
		self.thread=None
		self.origActiveLayer=None
		self.userSelectionChan=None
		self.userGroupLayer=None
		self.userPreviewLayer=None
		self.previewLayer = None
		self.previewActiveLayer=None
		self.previewPos=None
		self.stop_signal=False
		self.isRunning=True
		self.selectionData={}
		self.processSelection()
		self.showDialog()
		
	def do_thread_finished(self, args):
		self.window.destroy()
		
	def findFirstVisibleLayer(self, groupLayer):
		for layer in groupLayer.children:
			if layer.visible:
				return layer
		return None
		
	def processSelection(self):
		"""
		pdb.gimp_image_undo_freeze(self.img)
		self.origActiveLayer=pdb.gimp_image_get_active_layer(self.img)
		
		if type(self.origActiveLayer) == gimp.GroupLayer:
			self.userGroupLayer=self.origActiveLayer
				
		
		if not pdb.gimp_selection_is_empty(self.img):
			curSelection=pdb.gimp_image_get_selection(self.img)
			self.selectionData["width"]=curSelection.width
			self.selectionData["height"]=curSelection.height
			self.userSelectionChan = pdb.gimp_selection_save(self.img)
		pdb.gimp_image_undo_thaw(self.img)
		"""
		
	def postDialogProcessing(self):
		"""
		if type(self.userGroupLayer) == gimp.GroupLayer:
			firstVisible=self.findFirstVisibleLayer(self.userGroupLayer)
			#Finish setting up 
			if firstVisible is not None and type(firstVisible) == gimp.Layer:
				self.setPreviewLayer(firstVisible, self.previewLayerButton)
		"""
		"""
		if type(self.userGroupLayer) == gimp.GroupLayer:
			self.setPreviewLayer(self.userGroupLayer, self.previewLayerButton)
		"""
		
	def setPreviewLayer(self, userLayer, widget):
		try:
			if not self.layer_exists(self.previewLayer):
				oldPreviewLayer = self.userPreviewLayer
				self.userPreviewLayer=userLayer
			
				if type(self.userPreviewLayer) == gimp.Layer:
					self.previewLayerViewer.set_text(self.userPreviewLayer.name)
					self.previewButton(widget)
				else:
					warning_normal("Please select a layer!")
					if type(oldPreviewLayer) == gimp.Layer:
						self.userPreviewLayer = oldPreviewLayer
		except Exception as exp:
			error_box("Exception: "+str(exp))
	
	def buttonSelectionSelected(self, widget, data=None):
		try:
			if not pdb.gimp_selection_is_empty(self.img):
				curSelection=pdb.gimp_image_get_selection(self.img)
				self.selectionData["width"]=curSelection.width
				self.selectionData["height"]=curSelection.height
				self.selectionChan = pdb.gimp_selection_save(self.img)
				self.selectionChanViewer.set_text("Selected")
			else:
				self.selectionChanViewer.set_text("")
		except Exception as exp:
			error_box("Exception: "+str(exp))
	
	def buttonSelectLayerSelected(self, widget, data=None):
		try:
			oldGroupLayer = self.userGroupLayer
			self.userGroupLayer=pdb.gimp_image_get_active_layer(self.img)
		
			if type(self.userGroupLayer) == gimp.GroupLayer:
				self.selectedLayerViewer.set_text(self.userGroupLayer.name)
			else:
				warning_normal("Please select a Group Layer!")
				if type(oldGroupLayer) == gimp.GroupLayer:
					self.userGroupLayer = oldGroupLayer
		except Exception as exp:
			error_box("Exception: "+str(exp))
		
	def buttonPreviewLayerSelected(self, widget, data=None):
		try:
			self.setPreviewLayer(pdb.gimp_image_get_active_layer(self.img), widget)
		except Exception as exp:
			error_box("Exception: "+str(exp))
			
	def buttonLoadSelection(self, widget, data=None):
		try:
				isSel, x1, y1, x2, y2  = pdb.gimp_selection_bounds(self.img)
				if isSel:
					self.xSpinner['adj'].set_value(x1)
					self.ySpinner['adj'].set_value(y1)
					self.widthSpinner['adj'].set_value(abs(x2-x1))
					self.heightSpinner['adj'].set_value(abs(y2-y1))
		except Exception as exp:
			error_box("Exception: "+str(exp))
			
	def buttonLoadAtlas(self, widget, data=None):
		localFileName = self.fileDialog.openFile()
		if localFileName is not None:
			reader = ReaderLibGDXAtlas()
			self.textureAtlases = reader.readFile(localFileName)
		
	def buttonSaveAtlas(self, widget, data=None):
		localFileName = self.fileDialog.saveFile()
		if localFileName is not None:
			WriterLibGDXAtlas.writeFile(localFileName, self.textureAtlases)

	def showDialog(self):
		try:
			#self.dialog = gimpui.Dialog("Move Selection for all Sublayers", "highenddialog")
			
			self.dialog = gtk.Window()
			self.dialog.connect("destroy", self.main_quit)

			self.table = gtk.Table(10, 3, True)
			self.table.set_homogeneous(False)
			self.table.set_row_spacings(4)
			self.table.set_col_spacings(4)
			self.table.show()
			
			#Load Selection Button
			self.loadSelectBtn = gtk.Button("Load Selection")
			self.loadSelectBtn.connect("clicked", self.buttonLoadSelection)
			self.loadSelectBtn.show()
			self.table.attach(self.loadSelectBtn, 1, 2, 0, 1)
			
			#Image Name Row
			self.nameLabel = self.make_label("Name:")
			self.table.attach(self.nameLabel, 0, 1, 1, 2)
			
			self.nameEntry=gtk.Entry()
			self.nameEntry.show()
			self.table.attach(self.nameEntry, 1, 2, 1, 2)
			
			#Index Row
			self.indexLabel = self.make_label("Index:")
			self.table.attach(self.indexLabel, 0, 1, 2, 3)
			
			self.indexSpinner = self.make_slider_and_spinner(0, 0.0, 1000, 1.0, 10.0, 0)
			self.indexSpinner['adj'].set_value(1)
			self.indexSpinner['spinner'].set_value(0)
			#self.indexSpinner['adj'].connect("value_changed", self.updatePreviewLayer)

			self.indexLabel.set_mnemonic_widget(self.indexSpinner['spinner'])
			self.table.attach(self.indexSpinner['slider'], 1, 2, 2, 3)
			self.table.attach(self.indexSpinner['spinner'], 2, 3, 2, 3)
			
			#X Row
			self.xLabel = self.make_label("X:")
			self.table.attach(self.xLabel, 0, 1, 3, 4)
			self.xSpinner = self.make_slider_and_spinner(0.0, 0.0, self.img.width, 1.0, 10.0, 0)
			self.xSpinner['adj'].set_value(0)
			self.xSpinner['spinner'].set_value(0)
			#self.xSpinner['adj'].connect("value_changed", self.updatePreviewLayer)

			self.xLabel.set_mnemonic_widget(self.xSpinner['spinner'])
			self.table.attach(self.xSpinner['slider'], 1, 2, 3, 4)
			self.table.attach(self.xSpinner['spinner'], 2, 3, 3, 4)
			
			#Y Row
			self.yLabel = self.make_label("Y:")
			self.table.attach(self.yLabel, 0, 1, 4, 5)
			self.ySpinner = self.make_slider_and_spinner(0.0, 0.0, self.img.height, 1.0, 10.0, 0)
			self.ySpinner['adj'].set_value(0)
			self.ySpinner['spinner'].set_value(0)
			#self.ySpinner['adj'].connect("value_changed", self.updatePreviewLayer)

			self.yLabel.set_mnemonic_widget(self.ySpinner['spinner'])
			self.table.attach(self.ySpinner['slider'], 1, 2, 4, 5)
			self.table.attach(self.ySpinner['spinner'], 2, 3, 4, 5)
			
			#Size Width Row
			self.widthLabel = self.make_label("Size Width:")
			self.table.attach(self.widthLabel, 0, 1, 5, 6)
			
			self.widthSpinner = self.make_slider_and_spinner(0.0, 0.0, self.img.height, 1.0, 10.0, 0)
			self.widthSpinner['adj'].set_value(0)
			self.widthSpinner['spinner'].set_value(0)
			#self.widthSpinner['adj'].connect("value_changed", self.updatePreviewLayer)
			
			self.widthLabel.set_mnemonic_widget(self.widthSpinner['spinner'])
			self.table.attach(self.widthSpinner['slider'], 1, 2, 5, 6)
			self.table.attach(self.widthSpinner['spinner'], 2, 3, 5, 6)
			
			#Size Height
			self.heightLabel = self.make_label("Height:")
			self.table.attach(self.heightLabel, 0, 1, 6, 7)
			
			self.heightSpinner = self.make_slider_and_spinner(0.0, 0.0, self.img.height, 1.0, 10.0, 0)
			self.heightSpinner['adj'].set_value(0)
			self.heightSpinner['spinner'].set_value(0)
			#self.heightSpinner['adj'].connect("value_changed", self.updatePreviewLayer)
			
			self.heightLabel.set_mnemonic_widget(self.heightSpinner['spinner'])
			self.table.attach(self.heightSpinner['slider'], 1, 2, 6, 7)
			self.table.attach(self.heightSpinner['spinner'], 2, 3, 6, 7)
			
			#Button Row - List Button Control - Save/Load/Remove from list
			self.saveListBtn = gtk.Button("Save")
			#self.saveListBtn.connect("clicked", self.methodname)
			self.saveListBtn.show()
			self.table.attach(self.saveListBtn, 0, 1, 7, 8)
			
			self.loadListBtn = gtk.Button("Load")
			#self.loadListBtn.connect("clicked", self.methodname)
			self.loadListBtn.show()
			self.table.attach(self.loadListBtn, 1, 2, 7, 8)
			
			self.removeListBtn = gtk.Button("Remove")
			#self.removeListBtn.connect("clicked", self.methodname)
			self.removeListBtn.show()
			self.table.attach(self.removeListBtn, 2, 3, 7, 8)
			
			
			#List view
			self.listStore = gtk.ListStore(str)
			self.listStore.append (["PyQt"])
			self.listStore.append (["Tkinter"])
			self.listStore.append (["WxPython"])
			self.listStore.append (["PyGTK"])
			self.listStore.append (["PySide"])
			
			self.treeView = gtk.TreeView()
			self.treeView.set_model(self.listStore)

			self.rendererText = gtk.CellRendererText()
			self.column = gtk.TreeViewColumn("Python GUI Libraries", self.rendererText, text=0)
			self.treeView.append_column(self.column)
			self.table.attach(self.treeView, 1, 2, 8, 9)
			
			#Button Row - Load/Save Atlas
			self.loadAtlasBtn = gtk.Button("Load Atlas")
			self.loadAtlasBtn.connect("clicked", self.buttonLoadAtlas)
			self.loadAtlasBtn.show()
			self.table.attach(self.loadAtlasBtn, 0, 1, 9, 10)
			
			self.saveAtlasBtn = gtk.Button("Save Atlas")
			self.saveAtlasBtn.connect("clicked", self.buttonSaveAtlas)
			self.saveAtlasBtn.show()
			self.table.attach(self.saveAtlasBtn, 1, 2, 9, 10)
			
			#Window only
			self.dialog.vbox = gtk.VBox(False, 9)
			self.dialog.vbox.show()
			self.dialog.add(self.dialog.vbox)
			
			self.dialog.vbox.hbox1 = gtk.HBox(False, 9)
			self.dialog.vbox.hbox1.show()
			self.dialog.vbox.pack_start(self.dialog.vbox.hbox1, True, True, 9)
			self.dialog.vbox.hbox1.pack_start(self.table, True, True, 9)
			
			"""
			self.dialog.progressbar = gtk.ProgressBar()
			self.dialog.progressbar.show()
			self.dialog.vbox.pack_start(self.dialog.progressbar, True, True, 9)

			self.reset_button = gtk.Button("_Reset")
			self.reset_button.connect("clicked", self.resetbutton)
			self.reset_button.show()

			self.preview_button = gtk.Button("Preview")
			self.preview_button.connect("clicked", self.previewButton)
			self.preview_button.set_size_request(110, -1)
			self.preview_button.show()
			
			self.ok_button = gtk.Button("Ok")
			self.ok_button.show()
			"""
			
			#Window only
			self.dialog.vbox.hboxButtons = gtk.HBox(False, 3)
			self.dialog.vbox.hboxButtons.show()
			
			"""
			self.ok_button.connect("clicked", self.okbutton)
			
			self.cancel_button = gtk.Button("Cancel")
			self.cancel_button.connect("clicked", self.main_quit)
			self.cancel_button.show()
			
			self.dialog.vbox.hboxButtons.pack_start(self.ok_button, True, True, 3)
			self.dialog.vbox.hboxButtons.pack_start(self.cancel_button, True, True, 3)
			self.dialog.vbox.hboxButtons.pack_start(self.reset_button, True, True, 3)
			self.dialog.vbox.hboxButtons.pack_start(self.preview_button, True, True, 3)
			"""
			
			self.dialog.vbox.pack_start(self.dialog.vbox.hboxButtons, True, True, 3)
			
			#Dialog only
			"""
			if gtk.alternative_dialog_button_order():
				#self.ok_button = self.dialog.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
				self.dialog.action_area.add(self.ok_button)
				self.cancel_button = self.dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
				self.dialog.action_area.add(self.reset_button)
				self.dialog.action_area.add(self.preview_button)
			else:
				self.dialog.action_area.add(self.preview_button)
				self.dialog.action_area.add(self.reset_button)
				self.cancel_button = self.dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
				#self.ok_button = self.dialog.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
				self.dialog.action_area.add(self.ok_button)
			
			self.dialog.show()
			"""
			self.dialog.show_all()
			self.dialog.set_keep_above(True)
			self.postDialogProcessing()
			while self.isRunning:
				gtk.main_iteration_do(False)
			if self.thread is not None:
				self.thread.join()
			if self.runmode != -1:
				#self.dialog.run()
				#gtk.main()
				self.destroy()
		except Exception as err:
			print("select_move_layers_preview.dialog Exception: "+str(err))
			
	def destroy(self):
		self.cleanUp()
		self.dialog.destroy()

	def okbutton(self, widget):
		# remove old preview layer if it exists
		self.removePreviews()
		"""
		if self.layer_exists(self.previewLayer):
			self.img.remove_layer(self.previewLayer)
			self.previewLayer = None
		"""
			
		self.updateTransformFromGUI()
		
		self.perform_on_sublayers(self.userGroupLayer)
		
	def updateProgess(self, count, total, progress, layerName):
		#self.dialog.progressbar.pulse()
		self.dialog.progressbar.set_fraction(progress)
		self.dialog.progressbar.set_text(str(count)+"/"+str(total)+" "+layerName)
		return False
	
	def progressStarted(self):
		pdb.gimp_image_undo_group_start(self.img)
		
	def progressDone(self):
		pdb.gimp_image_undo_group_end(self.img)
		self.isRunning=False
		#self.window.destroy()
		
	def main_quit(self, gtkobject, data=None):
		self.stop_signal=True
		self.isRunning=False
		#self.thread.join()
		#gtk.main_quit()


	def resetbutton(self, widget):
		self.strength_spinner['adj'].set_value(10.0)
		self.flatten_check.set_active(True)

	def updateTransformFromGUI(self):
		self.xdelta = int(self.x_transform_spinner['adj'].get_value())
		self.ydelta = int(self.y_transform_spinner['adj'].get_value())

	def previewButton(self, widget):
		ptxt = self.preview_button.get_label()

		if self.layer_exists(self.previewLayer):
			#Remove Preview
			self.img.remove_layer(self.previewLayer)
			gimp.displays_flush()
			self.previewLayerButton.set_sensitive(True)
	
		else:
			self.updateTransformFromGUI()
			#Add/Update Preview
			lPreviewLayer=None
			if self.userPreviewLayer is not None:
				self.previewLayer = self.makePreviewLayer(self.img, self.userPreviewLayer)
				self.previewLayerButton.set_sensitive(False)


		if ptxt == "Preview":
			ptxt = "Undo Preview"
		else:
			ptxt = "Preview"
		self.preview_button.set_label(ptxt)
		
	def make_list_of_sublayers(self, applyLayer):
		curList=[]
		for curLayer in applyLayer.children:
			try:
				if isinstance(curLayer, gimp.GroupLayer):
					curList.extend(self.make_list_of_sublayers(curLayer))
				else:
					curList.append(curLayer)
			except Exception as exp:
					error_box("Exception: "+str(exp))
		return curList
		
	def perform_on_single_layer(self, curLayer):
		try:
			#Apply to each layer
			#origVis=pdb.gimp_layer_get_visible(curLayer)
			
			#Set each layer as active
			pdb.gimp_image_set_active_layer(self.img, curLayer)
			
			#Apply selection
			pdb.gimp_image_select_item(self.img, 2, self.userSelectionChan)
			
			#Preform Cut
			pdb.gimp_edit_cut(curLayer)
			floatLayer=pdb.gimp_edit_paste(curLayer, True)
			
			#Preform Move
			#transform_2d(source_x, source_y, scale_x, scale_y, angle, dest_x, dest_y, transform_direction, interpolation)
			#floatLayer.set_offsets(self.xdelta, self.ydelta)
			floatLayer = floatLayer.transform_2d(0, 0, 1, 1, 0, self.xdelta, self.ydelta, 0, 0)
			
			#Preform Anchor
			pdb.gimp_floating_sel_anchor(floatLayer)
			
			#Restore Visibility
			#pdb.gimp_layer_set_visible(curLayer,origVis)
		except Exception as exp:
			error_box("Exception: "+str(exp))
		
	def perform_on_sublayers(self, applyLayer):
		layerList = self.make_list_of_sublayers(applyLayer)
		#pdb.gimp_image_undo_group_start(self.img)
		#progressDialog = ProgressDialog()
		#progressDialog.showDialog(layerList, self.perform_on_single_layer)
		#progressDialog.showDialog(layerList, testProcess)
		
		#gtk.threads_init()		
		self.thread = ProgressThread(lambda : self.stop_signal, self.perform_on_single_layer, layerList, self)
		self.thread.daemon = True
		self.thread.start()
		
		#pdb.gimp_image_undo_group_end(self.img)
					
	def perform_on_alllayers(self, applyLayer):
		pdb.gimp_image_undo_group_start(self.img)
		for curLayer in applyLayer.children:
			if isinstance(curLayer, gimp.GroupLayer):
				try:
					self.perform_on_alllayers(curLayer)
				except Exception as exp:
					error_box("Exception: "+str(exp))
			else:
				try:
					#Apply to each layer
					#origVis=pdb.gimp_layer_get_visible(curLayer)
					
					#Set each layer as active
					pdb.gimp_image_set_active_layer(self.img, curLayer)
					
					#Apply selection
					pdb.gimp_image_select_item(self.img, 2, self.userSelectionChan)
					
					#Preform Cut
					pdb.gimp_edit_cut(curLayer)
					floatLayer=pdb.gimp_edit_paste(curLayer, True)
					
					#Preform Move
					#transform_2d(source_x, source_y, scale_x, scale_y, angle, dest_x, dest_y, transform_direction, interpolation)
					#floatLayer.set_offsets(self.xdelta, self.ydelta)
					floatLayer = floatLayer.transform_2d(0, 0, 1, 1, 0, self.xdelta, self.ydelta, 0, 0)
					
					#Preform Anchor
					pdb.gimp_floating_sel_anchor(floatLayer)
					
					#Restore Visibility
					#pdb.gimp_layer_set_visible(curLayer,origVis)
				except Exception as exp:
					error_box("Exception: "+str(exp))
		pdb.gimp_image_undo_group_end(self.img)
				
	def updatePreviewLayer(self, widget, data=None):
		if self.layer_exists(self.previewLayer):
			self.updateTransformFromGUI()
			pdb.gimp_image_undo_freeze(self.img)
			self.previewLayer.set_offsets(self.previewPos[0]+self.xdelta, self.previewPos[1]+self.ydelta)
			pdb.gimp_image_undo_thaw(self.img)
			gimp.displays_flush()


	def makePreviewLayer(self, img, layer):
		lNewPreviewLayer=None
		pdb.gimp_image_undo_freeze(self.img)
		
		#Apply selection
		pdb.gimp_image_select_item(self.img, 2, self.userSelectionChan)
		
		#Preform Copy
		pdb.gimp_edit_copy(layer)
		floatLayer=pdb.gimp_edit_paste(layer, True)
		
		pdb.gimp_floating_sel_to_layer(floatLayer)
		lNewPreviewLayer = pdb.gimp_image_get_active_layer(img)
		
		lNewPreviewLayer.name="(Do Not Edit) Select Move Layers"
		
		#Preform Move
		#transform_2d(source_x, source_y, scale_x, scale_y, angle, dest_x, dest_y, transform_direction, interpolation)
		#floatLayer=lNewPreviewLayer.transform_2d(curLayer.offsets[0], curLayer.offsets[1], 1, 1, 0, curLayer.offsets[0]+xdelta, curLayer.offsets[1]+ydelta, 0, 0)
		self.previewPos=floatLayer.offsets
		lNewPreviewLayer.set_offsets(self.previewPos[0]+self.xdelta, self.previewPos[1]+self.ydelta)
		
		#Preform Anchor
		#pdb.gimp_floating_sel_anchor(floatLayer)
		pdb.gimp_image_undo_thaw(self.img)
		gimp.displays_flush()
		return lNewPreviewLayer
		
	def get_layer_pos(self, layer):
		i = 0
		while i < len(self.img.layers):
			if layer == self.img.layers[i]:
				return i
		else:
			i += 1
		return -1


	def layer_exists(self, layer):
		return layer and pdb.gimp_item_is_valid(layer)
		
	def cleanUp(self):
		print("cleanUp Called")
		self.removePreviews()
		pdb.gimp_image_undo_freeze(self.img)
		if self.userSelectionChan:
			pdb.gimp_image_remove_channel(self.img, self.userSelectionChan)
			self.userSelectionChan=None
		
		#Restor Original Active Layer
		if self.origActiveLayer:
			pdb.gimp_image_set_active_layer(self.img, self.origActiveLayer)
			self.origActiveLayer=None
		pdb.gimp_image_undo_thaw(self.img)

	def removePreviews(self):
		if self.layer_exists(self.previewLayer):
			pdb.gimp_image_undo_freeze(self.img)
			self.img.remove_layer(self.previewLayer)
			pdb.gimp_image_undo_thaw(self.img)
			self.previewLayer = None
		gimp.displays_flush()

	def make_label(self, text):
		label = gtk.Label(text)
		#label.set_use_underline(True)
		#label.set_alignment(1.0, 0.5)
		label.show()
		return label

	def make_slider_and_spinner(self, init, min, max, step, page, digits):
		controls = {'adj':gtk.Adjustment(init, min, max, step, page), 'slider':gtk.HScale(), 'spinner':gtk.SpinButton()}
		controls['slider'].set_adjustment(controls['adj'])
		controls['slider'].set_draw_value(False)
		controls['spinner'].set_adjustment(controls['adj'])
		controls['spinner'].set_digits(digits)
		controls['slider'].show()
		controls['spinner'].show()
		return controls
		
	def make_spinner(self, init, min, max, step, page, digits):
		controls = {'adj':gtk.Adjustment(init, min, max, step, page), 'spinner':gtk.SpinButton()}
		controls['spinner'].set_adjustment(controls['adj'])
		controls['spinner'].set_digits(digits)
		controls['spinner'].show()
		return controls

	def show_error_msg(self, msg):
		origMsgHandler = pdb.gimp_message_get_handler()
		pdb.gimp_message_set_handler(ERROR_CONSOLE)
		pdb.gimp_message(msg)
		pdb.gimp_message_set_handler(origMsgHandler)

	def stringToColor(self, string):
		colorlist = string[5:-1].split(", ")
		return gimpcolor.RGB(float(colorlist[0]), float(colorlist[1]), float(colorlist[2]), float(colorlist[3]))


class pyEditLibGDXAtlas(gimpplugin.plugin):
	def start(self):
		gimp.main(self.init, self.quit, self.query, self._run)

	def init(self):
		pass

	def quit(self):
		pass

	def query(self):
		authorname = "Brian Atwell"
		copyrightname = "Brian Atwell"
		menu_location = "<Image>/Filters/Languages/Python-Fu/Edit Atlas"
		date = "Jan. 2021"
		plug_description = "Edit Atlas files using rect selections"
		plug_help = "Load an Atlas file, edit Atlas and save Atlas"
		plug_params = [
			(PDB_INT32, "run_mode", "Run mode"),
			(PDB_IMAGE, "image", "Input image"),
			(PDB_DRAWABLE, "drawable", "Input drawable")]
			####### 3 params above needed by all scripts using gimpplugin.plugin ######################
		
		gimp.install_procedure("py_edit_libgdx_atlas",
			plug_description,
			plug_help,
			authorname,
			copyrightname,
			date,
			menu_location,
			"RGB*, GRAY*",
			PLUGIN,
			plug_params,
			[])
			
	def py_edit_libgdx_atlas(self, runmode, img, drawable):
		edit_libgdx_atlas(runmode, img, drawable)
	
	def py_edit_libgdx_debug(self):
		return edit_libgdx_atlas(-1, gimp.image_list()[0], None)

if __name__ == '__main__':
	pyEditLibGDXAtlas().start()
