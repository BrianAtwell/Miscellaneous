#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Work In Progress
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

import gimpcolor
from gimpfu import *
import gimp, gimpplugin, math
from gimpenums import *
pdb = gimp.pdb
import gtk, gimpui, gimpcolor
from gimpshelf import shelf
import sys
from threading import Thread
import gobject, glib
import random

INDENTATIONSTR = "  "

DEBUG=True

if DEBUG:
	sys.stderr = open('C:/temp/edit_libgdx_atlas_debug.txt','a')
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
	
class FilePaths:
	
	@staticmethod
	def countOccurances(targetStr, targetChar):
		count=0
		for curChar in targetStr:
			if curChar == targetChar:
				count+=1
		return count

	@staticmethod
	def fileNameOnly(pathStr):
		resultStr=""
		backSlashCnt=FilePaths.countOccurances(pathStr, '\\')
		forwardSlashCnt=FilePaths.countOccurances(pathStr, '\/')
		
		if backSlashCnt > forwardSlashCnt:
			idx=pathStr.rfind('\\')
			resultStr=pathStr[idx+1:]
		else:
			idx=pathStr.rfind('\/')
			resultStr=pathStr[idx+1:]
		return resultStr
	
class FileDialogManager(object):

	def __init__(self, window):
		self.fileName=None
		self.window=window
		
	def openFile(self):
		localFileName=None
		dialog = gtk.FileChooserDialog(
			title="Please choose a file", parent=self.window, action=gtk.FileChooserAction(0)
		)
		dialog.add_buttons(
			gtk.STOCK_CANCEL,
			gtk.ResponseType(-6),
			gtk.STOCK_OPEN,
			gtk.ResponseType(-5),
		)
		
		if self.fileName is not None:
			dialog.set_filename(self.fileName)

		self.add_filters(dialog)

		response = dialog.run()
		## gtk.ResponseType(-5) == GTK_RESPONSE_OK
		if response == gtk.ResponseType(-5):
			self.fileName = dialog.get_filename()
			localFileName = self.fileName
		## gtk.ResponseType(-6) == GTK_RESPONSE_CANCEL
		elif response == gtk.ResponseType(-6):
			print("Cancel clicked")

		dialog.destroy()
		return localFileName
		
	def saveFile(self):
		localFileName=None
		dialog = gtk.FileChooserDialog(
			title="Please choose a file", parent=self.window, action=gtk.FileChooserAction(1)
		)
		dialog.add_buttons(
			gtk.STOCK_CANCEL,
			gtk.ResponseType(-6),
			gtk.STOCK_OPEN,
			gtk.ResponseType(-5),
		)
		
		if self.fileName is not None:
			dialog.set_filename(self.fileName)

		self.add_filters(dialog)

		response = dialog.run()
		## gtk.ResponseType(-5) == GTK_RESPONSE_OK
		if response == gtk.ResponseType(-5):
			self.fileName = dialog.get_filename()
			localFileName = self.fileName
		## gtk.ResponseType(-6) == GTK_RESPONSE_CANCEL
		elif response == gtk.ResponseType(-6):
			print("Cancel clicked")

		dialog.destroy()
		return localFileName
		
	def add_filters(self, dialog):
		filter_text = gtk.FileFilter()
		filter_text.set_name("Atlas files")
		filter_text.add_pattern("*.atlas")
		dialog.add_filter(filter_text)
		
		filter_any = gtk.FileFilter()
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
	def __init__(self, name="", index=0, x=0, y=0, width=0, height=0):
		self.name=name
		self.rotate=False
		self.xy=(x,y)
		self.size=(width,height)
		self.orig=(width,height)
		self.offset=(0,0)
		self.index=index
		
	def __str__(self):
		outStr = self.name + "\n"
		outStr += INDENTATIONSTR + "rotate: " + str(self.rotate).lower() + "\n"
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
		self.filter=("Nearest","Nearest")
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
		
	def clear(self):
		for key in self.subtextures:
			for item in self.subtextures[key]:
				if type(item) is list:
					item.clear()
		self.subtextures.clear()
					


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
		self.fileDialog=None
		self.textureAtlases=[]
		self.textureIdx=0
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
	
	def buttonSaveListData(self, widget, data=None):
		tempSub = SubtextureInfo(self.nameEntry.get_text(), 
			int(self.indexSpinner['adj'].get_value()), 
			int(self.xSpinner['adj'].get_value()),
			int(self.ySpinner['adj'].get_value()),
			int(self.widthSpinner['adj'].get_value()),
			int(self.heightSpinner['adj'].get_value()))
		self.saveRowToListStore(self.textureIdx, tempSub)
		self.updatePreviewLayer(widget)
		
	def clearData(self):
		for item in self.textureAtlases:
			item.clear()
		self.listStore.clear()
		pass
		
	def buttonClearListData(self, widget, data=None):
		self.clearData()
		
	def onTreeViewSelectChange(self, treeSelection):
		(treemodel, treeIter) = treeSelection.get_selected()
		if treeIter is not None:
			modelRow = treemodel[treeIter]
			self.nameEntry.set_text(modelRow[0])
			self.indexSpinner['adj'].set_value(int(modelRow[1]))
			self.xSpinner['adj'].set_value(int(modelRow[2]))
			self.ySpinner['adj'].set_value(int(modelRow[3]))
			self.widthSpinner['adj'].set_value(int(modelRow[4]))
			self.heightSpinner['adj'].set_value(int(modelRow[5]))
			
		
	def buttonRemoveListData(self, widget, data=None):
		treeSelection = self.treeView.get_selection()
		(treemodel, treeIter) = treeSelection.get_selected()
		if treeIter is not None:
			treemodel.remove(treeIter)
	
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
			
	def buttonOnionLayer(self, widget, data=None):
		pass
		
	def saveRowToListStore(self, textureIdx, tempSubtexture):
		subtextureIdx=0
		isFound=False
		
		if not tempSubtexture.name:
			return False
		
		if len(self.textureAtlases) == 0:
			textureAtlas=TextureLibGDXAtlas()
			textureAtlas.fileName=FilePaths.fileNameOnly(pdb.gimp_image_get_filename(self.img))
			textureAtlas.size=(self.img.width,self.img.height)
			self.textureAtlases.append(textureAtlas)
			
		if tempSubtexture.name in self.textureAtlases[textureIdx].subtextures:
			for subtexture in self.textureAtlases[textureIdx].subtextures[tempSubtexture.name]:
				if subtexture.name == tempSubtexture.name and subtexture.index == tempSubtexture.index:
					isFound=True
					break
				subtextureIdx+=1
		
		if isFound:
			isListStoreFound=False
			self.textureAtlases[textureIdx].subtextures[tempSubtexture.name][subtextureIdx]=tempSubtexture
			listStoreIndex=0
			for listItem in self.listStore:
				if listItem[0] == tempSubtexture.name and listItem[1] == tempSubtexture.index:
					isListStoreFound=True
					break
				listStoreIndex+=1
			if isListStoreFound:
				self.listStore[listStoreIndex]=[tempSubtexture.name, tempSubtexture.index, tempSubtexture.xy[0], tempSubtexture.xy[1], tempSubtexture.size[0], tempSubtexture.size[1]]
			return True
		else:
			if tempSubtexture.name not in self.textureAtlases[textureIdx].subtextures:
				self.textureAtlases[textureIdx].subtextures[tempSubtexture.name] = [tempSubtexture]
			else:
				self.textureAtlases[textureIdx].subtextures[tempSubtexture.name].append(tempSubtexture)
			self.listStore.append ([tempSubtexture.name, tempSubtexture.index, tempSubtexture.xy[0], tempSubtexture.xy[1], tempSubtexture.size[0], tempSubtexture.size[1]])
			return True

	def showDialog(self):
		try:
			#self.dialog = gimpui.Dialog("Move Selection for all Sublayers", "highenddialog")
			
			self.dialog = gtk.Window()
			self.fileDialog=FileDialogManager(self.dialog)
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
			self.saveListBtn.connect("clicked", self.buttonSaveListData)
			self.saveListBtn.show()
			self.table.attach(self.saveListBtn, 0, 1, 7, 8)
			
			self.clearListBtn = gtk.Button("Clear List")
			self.clearListBtn.connect("clicked", self.buttonClearListData)
			self.clearListBtn.show()
			self.table.attach(self.clearListBtn, 1, 2, 7, 8)
			
			self.removeListBtn = gtk.Button("Remove Item")
			self.removeListBtn.connect("clicked", self.buttonRemoveListData)
			self.removeListBtn.show()
			self.table.attach(self.removeListBtn, 2, 3, 7, 8)
			
			
			#List view
			self.listStore = gtk.ListStore(str, int, int, int, int, int )
			
			#Test Data to debug with
			#self.listStore.append (["Walk", 0, 2, 2, 30, 30])
			#self.listStore.append (["Walk", 1, 42, 2, 30, 30])
			
			tempSub = SubtextureInfo("Walk", 0, 2, 3, 24, 30)
			self.saveRowToListStore(0,tempSub)
			
			tempSub = SubtextureInfo("Walk", 1, 42, 3, 30, 24)
			self.saveRowToListStore(0,tempSub)
			
			self.treeView = gtk.TreeView()
			self.treeView.set_model(self.listStore)
			self.treeView.get_selection().connect("changed", self.onTreeViewSelectChange);

			self.rendererText = gtk.CellRendererText()
			self.nameColumn = gtk.TreeViewColumn("Name", gtk.CellRendererText(), text=0)
			self.indexColumn = gtk.TreeViewColumn("Index", gtk.CellRendererText(), text=1)
			self.xColumn = gtk.TreeViewColumn("X", gtk.CellRendererText(), text=2)
			self.yColumn = gtk.TreeViewColumn("Y", gtk.CellRendererText(), text=3)
			self.widthColumn = gtk.TreeViewColumn("Width", gtk.CellRendererText(), text=4)
			self.heightColumn = gtk.TreeViewColumn("Height", gtk.CellRendererText(), text=5)
			self.treeView.append_column(self.nameColumn)
			self.treeView.append_column(self.indexColumn)
			self.treeView.append_column(self.xColumn)
			self.treeView.append_column(self.yColumn)
			self.treeView.append_column(self.widthColumn)
			self.treeView.append_column(self.heightColumn)
			self.table.attach(self.treeView, 0, 3, 8, 9)
			
			#Button Row - Load/Save Atlas/Generate Onion Layer
			self.loadAtlasBtn = gtk.Button("Load Atlas")
			self.loadAtlasBtn.connect("clicked", self.buttonLoadAtlas)
			self.loadAtlasBtn.show()
			self.table.attach(self.loadAtlasBtn, 0, 1, 9, 10)
			
			#Button Save Atlas
			self.saveAtlasBtn = gtk.Button("Save Atlas")
			self.saveAtlasBtn.connect("clicked", self.buttonSaveAtlas)
			self.saveAtlasBtn.show()
			self.table.attach(self.saveAtlasBtn, 1, 2, 9, 10)
			
			#Button Generate Onion Layer
			self.onionLayerBtn = gtk.Button("Generate Onion Layer")
			self.onionLayerBtn.connect("clicked", self.buttonOnionLayer)
			self.onionLayerBtn.show()
			self.table.attach(self.onionLayerBtn, 2, 3, 9, 10)
			
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
		#delete old layer
		if self.layer_exists(self.previewLayer):
			pdb.gimp_item_delete(self.previewLayer)
		#generate layer
		#( image,
		#  width, 
		#  height, 
		#  Type { RGB-IMAGE (0), RGBA-IMAGE (1), GRAY-IMAGE (2), GRAYA-IMAGE (3), INDEXED-IMAGE (4), INDEXEDA-IMAGE (5) },
		#  layer Name,
		#  The layer opacity (0 <= opacity <= 100),
		"""  The layer combination mode { LAYER-MODE-NORMAL-LEGACY (0), LAYER-MODE-DISSOLVE (1), LAYER-MODE-BEHIND-LEGACY (2), LAYER-MODE-MULTIPLY-LEGACY (3), LAYER-MODE-SCREEN-LEGACY (4), LAYER-MODE-OVERLAY-LEGACY (5), LAYER-MODE-DIFFERENCE-LEGACY (6), LAYER-MODE-ADDITION-LEGACY (7), LAYER-MODE-SUBTRACT-LEGACY (8), LAYER-MODE-DARKEN-ONLY-LEGACY (9), LAYER-MODE-LIGHTEN-ONLY-LEGACY (10), LAYER-MODE-HSV-HUE-LEGACY (11), LAYER-MODE-HSV-SATURATION-LEGACY (12), LAYER-MODE-HSL-COLOR-LEGACY (13), LAYER-MODE-HSV-VALUE-LEGACY (14), LAYER-MODE-DIVIDE-LEGACY (15), LAYER-MODE-DODGE-LEGACY (16), LAYER-MODE-BURN-LEGACY (17), LAYER-MODE-HARDLIGHT-LEGACY (18), LAYER-MODE-SOFTLIGHT-LEGACY (19), LAYER-MODE-GRAIN-EXTRACT-LEGACY (20), LAYER-MODE-GRAIN-MERGE-LEGACY (21), LAYER-MODE-COLOR-ERASE-LEGACY (22), LAYER-MODE-OVERLAY (23), LAYER-MODE-LCH-HUE (24), LAYER-MODE-LCH-CHROMA (25), LAYER-MODE-LCH-COLOR (26), LAYER-MODE-LCH-LIGHTNESS (27), LAYER-MODE-NORMAL (28), LAYER-MODE-BEHIND (29), LAYER-MODE-MULTIPLY (30), LAYER-MODE-SCREEN (31), LAYER-MODE-DIFFERENCE (32), LAYER-MODE-ADDITION (33), LAYER-MODE-SUBTRACT (34), LAYER-MODE-DARKEN-ONLY (35), LAYER-MODE-LIGHTEN-ONLY (36), LAYER-MODE-HSV-HUE (37), LAYER-MODE-HSV-SATURATION (38), LAYER-MODE-HSL-COLOR (39), LAYER-MODE-HSV-VALUE (40), LAYER-MODE-DIVIDE (41), LAYER-MODE-DODGE (42), LAYER-MODE-BURN (43), LAYER-MODE-HARDLIGHT (44), LAYER-MODE-SOFTLIGHT (45), LAYER-MODE-GRAIN-EXTRACT (46), LAYER-MODE-GRAIN-MERGE (47), LAYER-MODE-VIVID-LIGHT (48), LAYER-MODE-PIN-LIGHT (49), LAYER-MODE-LINEAR-LIGHT (50), LAYER-MODE-HARD-MIX (51), LAYER-MODE-EXCLUSION (52), LAYER-MODE-LINEAR-BURN (53), LAYER-MODE-LUMA-DARKEN-ONLY (54), LAYER-MODE-LUMA-LIGHTEN-ONLY (55), LAYER-MODE-LUMINANCE (56), LAYER-MODE-COLOR-ERASE (57), LAYER-MODE-ERASE (58), LAYER-MODE-MERGE (59), LAYER-MODE-SPLIT (60), LAYER-MODE-PASS-THROUGH (61), LAYER-MODE-REPLACE (62), LAYER-MODE-ANTI-ERASE (63) })
		"""
		#(image, image width, image height, RGB-Image, "Preview Onion Layer", 100% full Opacity, Normal Mode)
		self.previewLayer = pdb.gimp_layer_new(self.img, self.img.width, self.img.height, 1, "Preview Onion Layer", 50.0, 28)
		pdb.gimp_image_insert_layer(self.img, self.previewLayer, None,0)
		##Read Each subtexture and convert to a rectangle
		texture=self.textureAtlases[self.textureIdx]
		bngColor = pdb.gimp_context_get_background()
		for key in texture.subtextures:
			for subtexture in texture.subtextures[key]:
				#Replace Selection
				pdb.gimp_selection_none(self.img)
				selection=pdb.gimp_image_select_rectangle(self.img, 2, int(subtexture.xy[0]), int(subtexture.xy[1]), int(subtexture.size[0]), int(subtexture.size[1]))
				fillColor=gimpcolor.RGB(random.randrange(0, 255),random.randrange(0, 255),random.randrange(0, 255))
				pdb.gimp_context_set_background(fillColor)
				pdb.gimp_drawable_edit_fill(self.previewLayer, 1)
		pdb.gimp_selection_none(self.img)
		pdb.gimp_context_set_background(bngColor)
		gimp.displays_flush()
		
		
		#Old Implementation
		"""
		if self.layer_exists(self.previewLayer):
			self.updateTransformFromGUI()
			pdb.gimp_image_undo_freeze(self.img)
			self.previewLayer.set_offsets(self.previewPos[0]+self.xdelta, self.previewPos[1]+self.ydelta)
			pdb.gimp_image_undo_thaw(self.img)
			gimp.displays_flush()
		"""


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
